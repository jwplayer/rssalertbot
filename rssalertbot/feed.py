import aiohttp
import async_timeout
import base64
import concurrent.futures
import dateparser
import feedparser
import logging
import pendulum
import re
from box import Box

import rssalertbot
import rssalertbot.alerts as alerts
from .util import deepmerge


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

    def __init__(self, loop, cfg, group, name, url, storage):
        self.log = logging.getLogger('.'.join((self.__class__.__module__,
                                               self.__class__.__name__)))

        self.group = group
        self.loop = loop
        self.cfg  = cfg
        self.name = name
        self.url  = url
        self.storage = storage

        # first get the default outputs from the group
        self.outputs = group.get('outputs', {})

        # next merge the feed-specific outputs
        self.outputs = deepmerge(self.outputs, cfg.get('outputs', {}))

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


    @property
    def previous_date(self):
        """Get the previous date from storage"""
        return self.storage.last_update(self.name)


    def save_date(self, new_date: pendulum.DateTime):
        """
        Sets the 'last run' date in storage.

        Args:
            date: obviously, the date
        """
        self.storage.save_date(self.name, new_date)


    async def _fetch(self, session, timeout=10):
        """
        Async'ly fetch the feed

        Args:
            session: active aiohttp.ClientSession()
            timeout (int): fetch timeout

        Returns:
            str: response text
        """

        self.log.debug(f"[{self.name}] Fetching url: {self.url}")
        with async_timeout.timeout(timeout, loop=self.loop):
            try:
                async with session.get(self.url) as response:
                    if response.status != 200:
                        self._handle_fetch_failure('no data', f"HTTP error {response.status}")
                        return
                    return await response.text()

            except concurrent.futures.CancelledError:
                self._handle_fetch_failure('timeout', f"Timeout while fetching feed")

            except Exception as e:
                self._handle_fetch_failure('unkown', f"Exception fetching feed: {e}")


    def _handle_fetch_failure(self, title, description):
        """
        Handles a fetch failure, at least by logging, possibly by
        alerting too.

        Args:
            title (str): alert title
            description (str): alert description
        """

        self.log.error(f"[{self.name}] {title}: {description}")

        if not self.group.get('alert_on_failure'):
            return

        # if we've been asked to alert on failure, we create
        # a fake event (as a Box) and alert with it
        self.alert(Box({
            'title':        title,
            'description':  description,
            'published':    pendulum.now('UTC'),
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
                self.log.error(f"[{self.name}] Error: no data recieved")
                return []
            return data.entries


    async def process(self, timeout=60):
        """
        Fetch and process this feed.

        Args:
            timeout (int): HTTP timeout
        """

        self.log.info(f"[{self.name}] Begining processing, previous date {self.previous_date}")

        new_date = pendulum.datetime(1970, 1, 1, tz='UTC')
        now = pendulum.now('UTC')

        for entry in await self.fetch_and_parse(timeout):

            # fix some bogus timezones
            m = re.search(' ([PMCE][DS]T)$', entry.published)
            if m:
                entry.published = entry.published.replace(
                    m.group(1),
                    rssalertbot.BOGUS_TIMEZONES[m.group(1)])

            date = pendulum.from_timestamp(dateparser.parse(entry.published).timestamp())

            # store the date from the first entry
            if date > new_date:
                new_date = date

            # skip anything that's stale
            if date <= now.subtract(days=1):
                continue

            # and anything before the previous date
            if date <= self.previous_date:
                continue

            self.log.debug(f"[{self.name}] Found new entry {date}")

            # alert on it
            self.alert(entry)

            if not new_date:
                new_date = now

        self.save_date(new_date)
        self.log.info(f"[{self.name}] End processing, previous date {new_date}")


    def alert(self, entry):
        """
        Alert with this entry.
        """

        if self.outputs.get('log.enabled'):
            alerts.alert_log(self, self.outputs.get('log'), entry)

        if self.outputs.get('email.enabled'):
            alerts.lert_email(self, self.outputs.get('email'), entry)

        if self.outputs.get('slack.enabled'):
            alerts.alert_slack(self, self.outputs.get('slack'), entry)


