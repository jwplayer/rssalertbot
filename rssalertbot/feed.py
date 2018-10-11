import aiohttp
import async_timeout
import base64
import dateparser
import feedparser
import html2text
import logging
import pendulum
import re

from mailer         import Mailer, Message

import rssalertbot
from .util import deepmerge, guess_color, strip_html


class Feed:
    """Base class for feeds"""

    def __init__(self, loop, cfg, group, name, url, storage):
        self.log = logging.getLogger('.'.join((self.__class__.__module__,
                                               self.__class__.__name__)))

        self.group = group['name']
        self.loop = loop
        self.cfg  = cfg
        self.name = name
        self.url  = url
        self.storage = storage

        # first get the default outputs from the group
        self.outputs = group.get('outputs', {})

        # next merge the feed-specific outputs
        self.outputs = deepmerge(self.outputs, cfg.get('outputs', {}))

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


    def save_date(self, new_date):
        """Sets the 'last run' date in storage"""
        self.storage.save_date(self.name, new_date)


    async def _fetch(self, session, url, timeout=10):
        """
        Async'ly fetch a feed
        """

        self.log.debug(f"[{self.name}] Fetching url: {self.url}")
        with async_timeout.timeout(timeout, loop=self.loop):
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.log.error(f"[{self.name}] HTTP {response.status}: {response}")
                        return
                    return await response.text()
            except aiohttp.client_exceptions.ClientError as e:
                self.log.error(f"[{self.name}] {e}")


    async def fetch_entries(self, session, timeout=10):
        """Fetch and return a list of entries"""


        headers = {}
        if self.username and self.password:
            creds = f'{self.username}:{self.password}'.encode('utf-8')
            headers['Authorization'] = f'Basic {base64.urlsafe_b64encode(creds)}'

        try:
            rsp = await self._fetch(session, self.url, timeout)

            data = feedparser.parse(rsp)
            if not data:
                self.log.error(f"[{self.name}] Error: no data recieved")
                return
            return data.entries
        except Exception as e:
            self.log.exception(f"[{self.name}] Error or timeout while fetching feed")
            return


    async def process(self, timeout=60):
        """Fetch and process this feed"""

        self.log.info(f"[{self.name}] Begining processing, previous date {self.previous_date}")

        new_date = pendulum.datetime(1970, 1, 1, tz='UTC')
        now = pendulum.now('UTC')
        async with aiohttp.ClientSession() as session:

            for entry in await self.fetch_entries(session, timeout):

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
        self.alert_log(entry)
        self.alert_email(entry)
        self.alert_slack(entry)


    def alert_email(self, entry):
        """Sends alert via email if enabed"""

        if not self.outputs.get('email.enabled'):
            self.log.debug("Email not enabled")
            return

        cfg = self.outputs.get('email')

        description = strip_html(entry.description)

        smtp = Mailer(host=self.email_server)
        message = Message(charset="utf-8", From=cfg['from'], To=cfg['to'],
                          Subject = f"{self.group} Alert: ({self.name}) {entry.title}")
        message.Body = f"Feed: {self.name}\nDate: {entry.published}\n\n{description}"
        message.header('X-Mailer', 'rssalertbot')
        smtp.send(message)


    def alert_log(self, entry):
        """Sends alert to logfile if enabled."""

        if not self.outputs.get('log.enabled'):
            self.log.debug("Logging not enabled")
            return

        self.log.warning(f"[{self.name}] {entry.published}: {entry.title}")
        self.log.debug(f"[{self.name}] {entry.description}")


    def alert_slack(self, entry, color=None):
        """Sends alert to slack if enabled"""

        # load this here to nicely deal with pip extras
        try:
            from slackclient import SlackClient
        except ImportError:
            self.log.error("Python package 'slackclient' not installed!")
            return

        if not self.outputs('slack.enabled'):
            self.log.debug("Slack not enabled")
            return
        cfg = self.outputs.get('slack')

        matchstring = entry.title
        if cfg.get('match_body'):
            matchstring += entry.description

        # use the provided color
        if cfg.get('force_color'):
            color = cfg.get('force_color')

        # guess color
        elif cfg.get('colors'):
            colors = cfg.get('colors')
            matches = '(' + '|'.join(colors.keys()) + ')'
            m = re.search(matches, matchstring)
            if m:
                for (s, c) in colors.items():
                    if s in m.groups(1):
                        color = c
                        break

        # if color isn't set already, try some defaults
        if not color:
            color = guess_color(matchstring)['slack_color']

        # cleanup description to get it supported by slack - might figure out
        # something more elegant later

        desc = html2text.html2text(entry.description)
        desc = desc.replace('**', '*')
        desc = desc.replace('\\', '')
        desc = desc.replace('<', '&lt;')
        desc = desc.replace('>', '&gt;')
        desc = desc.replace('&', '&amp;')

        attachments = [
            {
                "title": "{} {}\n{}".format(self.name, entry.published, entry.title),
                "text": desc,
                "mrkdwn_in": [
                    "title",
                    "text"
                ],
                "color": color
            }
        ]

        try:
            sc = SlackClient(cfg.get('token'))
            sc.api_call(
                "chat.postMessage",
                channel=cfg.get('channel'),
                attachments=attachments,
                icon_emoji=':information_source:',
                as_user=False,
                username=rssalertbot.BOT_USERNAME
            )

        except Exception as e:
            self.log.exception(f"Error contacting Slack for feed {self.name}")
