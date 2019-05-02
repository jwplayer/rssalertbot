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

import rssalertbot
import rssalertbot.alerts
from .config import Config

log = logging.getLogger(__name__)


class Feed:
    """
    A feed.

    Args:
        loop:           active asyncio event loop
        cfg (Box):      full configuration
        group (Box):    the group config
        name (str):     Feed name
        url (str):      URL to fetch
        storage:        Instantiated :py:class:`rssalertbot.storage.BaseStorage` subclass
    """

    def __init__(self, loop, cfg, storage, group, name, url):

        self.group = group
        self.loop = loop
        self.cfg  = cfg
        self.name = name
        self.url  = url
        self.storage = storage

        self.log = logging.LoggerAdapter(
            log,
            extra = {
                "feed": self.name,
                "group": self.group.name,
            })

        self.log.debug(f"Setting up feed {self.name}")

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
                    self.log.error(f"Slack enabled but {field} not set!")
                    self.outputs.set('slack.enabled', False)

        if self.outputs.get('email.enabled'):
            for field in ('email.to', 'email.from'):
                if not self.outputs.get(field):
                    self.log.error(f"Email enabled but {field} not set!")
                    self.outputs.set('email.enabled', False)


    @property
    def previous_date(self):
        """Get the previous date from storage"""
        key = f'{self.group.name}-{self.name}'
        return self.storage.last_update(key)


    def save_date(self, new_date: pendulum.DateTime):
        """
        Sets the 'last run' date in storage.

        Args:
            date: obviously, the date
        """
        key = f'{self.group.name}-{self.name}'
        self.storage.save_date(key, new_date)


    async def _fetch(self, session, timeout=10):
        """
        Async'ly fetch the feed

        Args:
            session: active aiohttp.ClientSession()
            timeout (int): fetch timeout

        Returns:
            str: response text
        """

        self.log.debug(f"Fetching url: {self.url}")
        with async_timeout.timeout(timeout, loop=self.loop):
            try:
                async with session.get(self.url) as response:
                    if response.status != 200:
                        self._handle_fetch_failure('no data', f"HTTP error {response.status}")
                        return
                    return await response.text()

            except concurrent.futures.CancelledError:
                self._handle_fetch_failure('Timeout', f"Timeout while fetching feed")

            except Exception as e:
                etype = '.'.join((type(e).__module__, type(e).__name__))
                self._handle_fetch_failure('Exception', f"{etype} fetching feed: {e}")


    def _handle_fetch_failure(self, title, description):
        """
        Handles a fetch failure, at least by logging, possibly by
        alerting too.

        Args:
            title (str): alert title
            description (str): alert description
        """

        self.log.error(f"{title}: {description}")

        if not self.group.get('alert_on_failure', False):
            return

        # if we've been asked to alert on failure, we create
        # a fake event (as a Box) and alert with it
        now = pendulum.now('UTC')
        self.alert(Box({
            'title':        title,
            'description':  description,
            'published':    pendulum.now('UTC'),
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
                self.log.error(f"Error: no data recieved")
                return []
            return data.entries


    async def process(self, timeout=60):
        """
        Fetch and process this feed.

        Args:
            timeout (int): HTTP timeout
        """

        self.log.info(f"Begining processing feed {self.name}, previous date {self.previous_date}")

        new_date = pendulum.datetime(1970, 1, 1, tz='UTC')
        now = pendulum.now('UTC')

        for entry in await self.fetch_and_parse(timeout):

            pubdate = dateutil.parser.parse(entry.published, tzinfos=rssalertbot.BOGUS_TIMEZONES)
            entry.published = pendulum.from_timestamp(pubdate.timestamp())
            # also save a prettified string format
            entry.datestring = self.format_timestamp_local(entry.published)

            # store the date from the first entry
            if entry.published > new_date:
                new_date = entry.published

            # skip anything that's stale
            if entry.published <= now.subtract(days=1):
                continue

            # and anything before the previous date
            if entry.published <= self.previous_date:
                continue

            self.log.debug(f"Found new entry {entry.published}")

            # alert on it
            self.alert(entry)

            if not new_date:
                new_date = now

        self.save_date(new_date)
        self.log.info(f"End processing feed {self.name}, previous date {new_date}")


    def alert(self, entry):
        """
        Alert with this entry.
        """

        if self.outputs.get('log.enabled'):
            rssalertbot.alerts.alert_log(self, self.outputs.get('log'), entry)

        if self.outputs.get('email.enabled'):
            rssalertbot.alerts.alert_email(self, self.outputs.get('email'), entry)

        if self.outputs.get('slack.enabled'):
            rssalertbot.alerts.alert_slack(self, self.outputs.get('slack'), entry)


    def format_timestamp_local(self, timestamp):
        """
        Format the given timestamp for printing, in the local time.
        This is good when printing messages for users who don't think in UTC.

        The format is RFC 1123.

        Args:
            timestamp (:py:class:`pendulum.DateTime`): the timestamp
        """
        return timestamp.in_tz(self.cfg.get('tz', pendulum.now().tz)).to_rfc1123_string()
