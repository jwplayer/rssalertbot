import aiohttp
import async_timeout
import base64
import dateparser
import feedparser
import html2text
import logging
import os
import pendulum
import re

from mailer         import Mailer, Message
from slackclient    import SlackClient

import rssalertbot
from .util import guess_color, strip_html


class Feed:
    """Base class for feeds"""

    group = "FeedBot"

    enable_slack    = False
    enable_email    = False
    enable_log      = False

    slack_colors = {}
    slack_match_body = False
    slack_force_color = None

    username = None
    password = None

    def __init__(self, loop, cfg, group, name, url, loglevel=logging.WARN):
        self.log = logging.getLogger('.'.join((self.__class__.__module__,
                                               self.__class__.__name__)))
        self.log.setLevel(loglevel)

        self.loop = loop
        self.cfg  = cfg
        self.name = name
        self.url  = url

        # get the outputs, and configure them
        outputs = cfg.get('outputs', [])
        self.state_path = cfg.get('state_path', '/tmp')
        self.datafile = os.path.join(self.state_path, f'last.{self.name}.dat')

        if 'email' in outputs:
            self.enable_email   = outputs['email']['enabled']
            self.email_target   = outputs['email']['to']
            self.email_from     = f"{group['name']} Feeds <{outputs['email']['from']}>"
            self.email_server   = outputs['email']['server']

        if 'log' in outputs:
            self.enable_log     = outputs['log']['enabled']

        if 'slack' in outputs:
            self.enable_slack   = outputs['slack']['enabled']
            self.slack_channel  = outputs['slack']['channel']
            self.slack_token    = outputs['slack']['token']

        # do the global notification disable
        if cfg.get('no_notify', False):
            self.log.debug("Note: notifications disabled")
            self.enable_email = False

        self.group = group['name']

        # configure fetch user/password
        if 'username' in group:
            self.username = group['username']
        if 'password' in group:
            self.password = group['password']

        if 'outputs' in group:
            # configure email output
            if self.enable_email and 'email' in group['outputs']:
                # enable/disable email here, default = false
                self.enable_email = group['outputs']['email'].get('enabled', False)

                if 'to' in group['outputs']['email']:
                    self.email_target = group['outputs']['email']['to']
                if 'from' in group['outputs']['email']:
                    self.email_from = group['outputs']['email']['from']
            else:
                self.enable_email = False

            # configure slack output
            if self.enable_slack and 'slack' in group['outputs']:
                if 'channel' in group['outputs']['slack']:
                    self.slack_channel = group['outputs']['slack']['channel']
                if 'colors' in group['outputs']['slack']:
                    self.slack_colors = group['outputs']['slack']['colors']
                if 'force_color' in group['outputs']['slack']:
                    self.slack_force_color = group['outputs']['slack']['force_color']
                if 'match_body' in group['outputs']['slack']:
                    self.slack_match_body = group['outputs']['slack']['match_body']
            else:
                self.enable_slack = False

        self._previous_date = None


    @property
    def previous_date(self):
        if not self._previous_date:
            # read the previous date from our data file
            try:
                with open(self.datafile, 'rb') as f:
                    self._previous_date = pendulum.parse(f.read().strip())
            except:
                self._previous_date = pendulum.yesterday('UTC')
                self

        return self._previous_date


    def save_date(self, new_date):
        """save the date, as UTC always"""
        with open(self.datafile, 'w') as f:
            f.write(str(new_date))


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


    async def process(self, timeout=60, dry_run=False):
        """Fetch and process this feed"""

        self.log.info(f"[{self.name}] Begining processing, previous date {self.previous_date}")

        if dry_run:
            self.log.warn(f"[{self.name}] Simulation mode active")
            return

        async with aiohttp.ClientSession() as session:
            for entry in await self.fetch_entries(session, timeout):
                self.process_entry(entry)


        # TODO: save the date


    def process_entry(self, entry):
        """
        Process the entry
        """

        now = pendulum.now('UTC')
        new_date = None

        # fix some bogus timezones
        m = re.search(' ([PMCE][DS]T)$', entry.published)
        if m:
            entry.published = entry.published.replace(m.group(1),
                                                      rssalertbot.BOGUS_TIMEZONES[m.group(1)])

        now = pendulum.now('UTC')
        date = pendulum.from_timestamp(dateparser.parse(entry.published).timestamp())


        # store the date from the first entry
        if not new_date or date > new_date:
            new_date = date

        # skip anything that's stale
        if date <= now.subtract(days=1):
            return

        # and anything before the previous date
        if date <= self.previous_date:
            return

        self.log.debug(f"[{self.name}] Found new entry {date}")

        # alert on it
        self.alert(entry)

        if not new_date:
            new_date = now

        self.save_date(new_date)


    def alert(self, entry):
        self.alert_log(entry)
        self.alert_email(entry)
        self.alert_slack(entry)


    def alert_email(self, entry):
        """Sends alert via email if enabed"""

        if not self.enable_email:
            return

        description = strip_html(entry.description)

        smtp = Mailer(host=self.email_server)
        message = Message(charset="utf-8", From=self.email_from, To=self.email_target,
                          Subject = f"{self.group} Alert: ({self.name}) {entry.title}")
        message.Body = f"Feed: {self.name}\nDate: {entry.published}\n\n{description}"
        message.header('X-Mailer', 'rssalertbot')
        smtp.send(message)


    def alert_log(self, entry):
        """Sends alert to logfile if enabled"""

        if not self.enable_log:
            return

        self.log.warning(f"[{self.name}] {entry.published}: {entry.title}")
        self.log.debug(f"[{self.name}] {entry.description}")


    def alert_slack(self, entry, color=None):
        """Sends alert to slack if enabled"""

        if not self.enable_slack:
            return

        matchstring = entry.title
        if self.slack_match_body:
            matchstring += entry.description

        # use the provided color
        if self.slack_force_color:
            color = self.slack_force_color

        # guess color
        elif self.slack_colors:
            matches = '(' + '|'.join(self.slack_colors.keys()) + ')'
            m = re.search(matches, matchstring)
            if m:
                for (s, c) in self.slack_colors.items():
                    if s in m.groups(1):
                        color = c
                        break

        # if color isn't set already, try some defaults
        if not color:
            color = guess_color(matchstring)['slack_color']

        # cleanup description to get it supported by slack - might figure out something more elegant later
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
            sc = SlackClient(self.slack_token)
            sc.api_call(
                "chat.postMessage",
                channel=self.slack_channel,
                attachments=attachments,
                icon_emoji=':information_source:',
                as_user=False,
                username=rssalertbot.BOT_USERNAME
            )

        except Exception as e:
            self.log.exception(f"Error contacting Slack for feed {self.name}")

