"""
Feed processing
"""

import aiohttp
import async_timeout
import base64
import concurrent.futures
import copy
import dateutil.parser
import feedparser
import logging
import pendulum
from box import Box
from hashlib import md5

import rssalertbot
import rssalertbot.alerts
from .config import Config

log = logging.getLogger(__name__)


class Feed:
    """
    A feed.

    Args:
        cfg (Box):      full configuration
        storage:        Instantiated :py:class:`rssalertbot.storage.BaseStorage` subclass
        group (Box):    the group config
        name (str):     Feed name
        url (str):      URL to fetch
    """

    def __init__(self, cfg, storage, group, name, url):

        self.cfg  = cfg
        self.storage = storage
        self.group = group
        self.name = name
        self.url  = url

        self.feed = f'{self.group.name}-{self.name}'

        self.log = logging.LoggerAdapter(
            log,
            extra = {
                "feed": self.name,
                "group": self.group.name,
            })

        self.log.debug("Setting up feed %s", self.name)

        # start with the global outputs - note the copy so we don't mess
        # with the main config dictionary
        self.outputs = Config(copy.deepcopy(cfg.get('outputs', {})))

        # then merge the group outputs
        self.outputs.merge_dict(group.get('outputs', {}))

        # update the email 'from' to show the feed group name
        if 'email' in self.outputs:
            self.outputs['email']['from'] = f"{group['name']} Feeds <{self.outputs['email']['from']}>"

        # do the global notification disable
        if cfg.get('no_notify', False):
            self.log.debug("Note: notifications disabled")
            if 'email' in self.outputs:
                self.outputs['email']['disabled'] = True
            if 'slack' in self.outputs:
                self.outputs['slack']['disabled'] = True

        # configure fetch user/password
        self.username = group.get('username')
        self.password = group.get('password')

        # sanity tests
        if self.outputs.get('slack.enabled'):
            for field in ('slack.channel', 'slack.token'):
                if not self.outputs.get(field):
                    self.log.error("Slack enabled but %s not set!", field)
                    self.outputs.set('slack.enabled', False)

        if self.outputs.get('email.enabled'):
            for field in ('email.to', 'email.from'):
                if not self.outputs.get(field):
                    self.log.error("Email enabled but %s not set!", field)
                    self.outputs.set('email.enabled', False)


    @property
    def previous_date(self):
        """Get the previous date from storage"""
        yesterday = pendulum.yesterday('UTC')
        last_update = self.storage.last_update(self.feed)
        if not last_update or last_update < yesterday:
            last_update = yesterday
        return last_update


    async def _fetch(self, session, timeout=10):
        """
        Async'ly fetch the feed

        Args:
            session: active aiohttp.ClientSession()
            timeout (int): fetch timeout

        Returns:
            str: response text
        """

        self.log.debug("Fetching url: %s", self.url)
        with async_timeout.timeout(timeout):
            try:
                async with session.get(self.url) as response:
                    if response.status != 200:
                        self.log.error("HTTP Error %s fetching feed %s", response.status, self.url)
                        return await self._handle_fetch_failure('no data', f"HTTP error {response.status}")
                    return await response.text()

            except concurrent.futures.CancelledError:
                self.log.error("Timeout fetching feed %s", self.url)
                await self._handle_fetch_failure('Timeout', "Timeout while fetching feed")

            except Exception as e:
                self.log.exception("Error fetching feed %s", self.url)
                etype = '.'.join((type(e).__module__, type(e).__name__))
                await self._handle_fetch_failure('Exception', f"{etype} fetching feed: {e}")


    async def _handle_fetch_failure(self, title, description):
        """
        Handles a fetch failure, possibly by alerting.

        Args:
            title (str): alert title
            description (str): alert description
        """

        if not self.group.get('alert_on_failure', False):
            return

        # if we've been asked to alert on failure, we create
        # a fake event (as a Box) and alert with it
        now = pendulum.now('UTC')
        await self.alert(Box({
            'title':        title,
            'description':  description,
            'published':    now,
            'datestring':   self.format_timestamp_local(now),
        }))


    async def fetch_and_parse(self, timeout=10):
        """
        Fetch and parse the data to return a list of entries.

        Args:
            timeout (int): fetch timeout

        Returns:
            list: entries as objects from feedparser
        """

        headers = {}
        if self.username and self.password:
            creds = f'{self.username}:{self.password}'.encode('utf-8')
            headers['Authorization'] = f'Basic {base64.urlsafe_b64encode(creds)}'

        async with aiohttp.ClientSession() as session:
            rsp = await self._fetch(session, timeout)

            data = feedparser.parse(rsp)
            if not data:
                self.log.error("Error: no data recieved")
                return []
            return data.entries


    async def process(self, timeout=60):
        """
        Fetch and process this feed.

        Args:
            timeout (int): HTTP timeout
        """

        self.log.info("Begining processing feed %s, previous date %s",
                      self.name, self.previous_date)

        new_date = self.previous_date
        now = pendulum.now('UTC')

        for entry in await self.fetch_and_parse(timeout):

            pubdate = dateutil.parser.parse(entry.published, tzinfos=rssalertbot.BOGUS_TIMEZONES)
            entry.published = pendulum.from_timestamp(pubdate.timestamp())
            # also save a prettified string format
            entry.datestring = self.format_timestamp_local(entry.published)

            # skip anything that's stale
            if entry.published <= self.previous_date:
                continue

            event_id = md5((entry.title + entry.description).encode()).hexdigest()
            last_sent = self.storage.load_event(self.feed, event_id)
            re_alert = self.cfg.get('re_alert', rssalertbot.RE_ALERT_DEFAULT)
            should_delete_message = False

            if entry.published > now:
                if last_sent and now < last_sent.add(hours=re_alert):
                    continue
                self.storage.save_event(self.feed, event_id, now)
            else:
                if entry.published > new_date:
                    new_date = entry.published
                should_delete_message = last_sent

            self.log.debug("Found new entry %s", entry.published)

            # alert on it
            await self.alert(entry)

            if should_delete_message:
                self.log.debug(f"Deleting stored date for message {event_id}")
                self.storage.delete_event(self.feed, event_id)

        if new_date != self.previous_date:
            self.storage.save_date(self.feed, new_date)
        self.log.info("End processing feed %s, previous date %s", self.name, new_date)


    async def alert(self, entry):
        """
        Alert with this entry.
        """

        if self.outputs.get('log.enabled'):
            rssalertbot.alerts.alert_log(self, self.outputs.get('log'), entry)

        if self.outputs.get('email.enabled'):
            rssalertbot.alerts.alert_email(self, self.outputs.get('email'), entry)

        if self.outputs.get('slack.enabled'):
            await rssalertbot.alerts.alert_slack(self, self.outputs.get('slack'), entry)


    def format_timestamp_local(self, timestamp):
        """
        Format the given timestamp for printing, in the local time.
        This is good when printing messages for users who don't think in UTC.

        The format is RFC 1123.

        Args:
            timestamp (:py:class:`pendulum.DateTime`): the timestamp
        """
        return timestamp.in_tz(self.cfg.get('tz', pendulum.now().tz)).to_rfc1123_string()
