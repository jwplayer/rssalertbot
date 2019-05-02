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
    logger = logging.LoggerAdapter(log, extra = {
        'feed':  feed.name,
        'group': feed.group['name'],
    })
    logger.setLevel(logging.DEBUG)

    logger.debug(f"[{feed.name}] Alerting email: {entry.title}")

    description = strip_html(entry.description)

    try:
        smtp = Mailer(host=cfg['server'])
        message = Message(charset="utf-8", From=cfg['from'], To=cfg['to'],
                          Subject = f"{feed.group['name']} Alert: ({feed.name}) {entry.title}")
        message.Body = f"Feed: {feed.name}\nDate: {entry.datestring}\n\n{description}"
        message.header('X-Mailer', 'rssalertbot')
        smtp.send(message)

    except Exception:
        logger.exception(f"[{feed.name}] Error sending mail")


def alert_log(feed, cfg, entry):
    """
    Sends alert to the logfile.

    Args:
        feed (:py:class:`Feed`): the feed
        cfg (dict):              output config
        entry (dict):            the feed entry
    """
    logger = logging.LoggerAdapter(log, extra = {
        'feed':  feed.name,
        'group': feed.group['name'],
    })
    logger.setLevel(logging.DEBUG)

    logger.warning(f"[{feed.name}] {entry.published}: {entry.title}")
    if entry.description:
        logger.debug(f"[{feed.name}] {entry.description}")


def alert_slack(feed, cfg, entry, color=None):
    """
    Sends alert to slack if enabled.

    Args:
        feed (:py:class:`Feed`): the feed
        cfg (dict):              output config
        entry (dict):            the feed entry
    """
    logger = logging.LoggerAdapter(log, extra = {
        'feed':  feed.name,
        'group': feed.group['name'],
    })
    logger.setLevel(logging.DEBUG)
    logger.debug(f"[{feed.name}] Alerting slack: {entry.title}")

    # load this here to nicely deal with pip extras
    try:
        import slack
    except ImportError:
        logger.error("Python package 'slackclient' not installed!")
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

    # NOTE - this isn't actually used as color here, since it's slack
    # and now it doesn't do color, but it does do emojis, so...

    # cleanup description to get it supported by slack - might figure out
    # something more elegant later

    desc = html2text.html2text(entry.description)
    desc = desc.replace('**', '*')
    desc = desc.replace('\\', '')
    desc = desc.replace('<', '&lt;')
    desc = desc.replace('>', '&gt;')
    desc = desc.replace('&', '&amp;')

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":{color}: *{feed.name}: {entry.title}*",
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": desc,
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Date:*\n{entry.datestring}"
                }
            ]
        }
    ]

    try:
        sc = slack.WebClient(cfg.get('token'))
        channels = cfg.get('channel')
        if not isinstance(channels, list):
            channels = [channels]
        for channel in channels:
            response = sc.chat_postMessage(
                user        = rssalertbot.BOT_USERNAME,
                channel     = channel,
                mrkdwn      = True,
                as_user     = True,
                text        = f"*{feed.name}: {entry.title}*",
                blocks      = blocks,
            )
            if response.get('ok'):
                logger.debug("Sent message to slack channel {channel}")
            else:
                logger.warning(f"Slack error: {response['response_metadata']}")

    except Exception:
        logger.exception(f"[{feed.name}] Error contacting Slack")
