"""
Alerts
"""
import logging
import re
import html2text
from mailer import Mailer, Message

import rssalertbot
from .util import guess_color, strip_html

log = logging.getLogger(__name__)


def alert_email(feed, cfg, entry):
    """Sends alert via email.

    Args:
        feed (:py:class:`Feed`): the feed
        cfg (dict):              output config
        entry (dict):            the feed entry
    """
    log.debug(f"Alerting email: {entry.title}")

    description = strip_html(entry.description)

    smtp = Mailer(host=cfg['server'])
    message = Message(charset="utf-8", From=cfg['from'], To=cfg['to'],
                      Subject = f"{feed.group['name']} Alert: ({feed.name}) {entry.title}")
    message.Body = f"Feed: {feed.name}\nDate: {entry.datestring}\n\n{description}"
    message.header('X-Mailer', 'rssalertbot')
    smtp.send(message)


def alert_log(feed, cfg, entry):
    """
    Sends alert to the logfile.

    Args:
        feed (:py:class:`Feed`): the feed
        cfg (dict):              output config
        entry (dict):            the feed entry
    """

    log.warning(f"[{feed.name}] {entry.published}: {entry.title}")
    if entry.description:
        log.debug(f"[{feed.name}] {entry.description}")


def alert_slack(feed, cfg, entry, color=None):
    """
    Sends alert to slack if enabled.

    Args:
        feed (:py:class:`Feed`): the feed
        cfg (dict):              output config
        entry (dict):            the feed entry
    """

    # load this here to nicely deal with pip extras
    try:
        import slackclient
    except ImportError:
        log.error("Python package 'slackclient' not installed!")
        return

    # attempt to match keywords in the title
    matchstring = entry.title

    # also attempt to match keywords in the body, if requested
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
        color = guess_color(matchstring)['slack']

    log.debug(f"[{feed.name}] Alerting slack: {entry.title} color {color}")

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
            "title": f"{feed.name} {entry.datestring}\n{entry.title}",
            "text": desc,
            "mrkdwn_in": [
                "title",
                "text"
            ],
            "color": color
        }
    ]

    try:
        sc = slackclient.SlackClient(cfg.get('token'))
        sc.api_call(
            "chat.postMessage",
            channel=cfg.get('channel'),
            attachments=attachments,
            icon_emoji=':information_source:',
            as_user=False,
            username=rssalertbot.BOT_USERNAME
        )

    except Exception as e:
        log.exception(f"Error contacting Slack for feed {feed.name}")
