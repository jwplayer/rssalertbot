"""
Alerts
"""
import logging
import re
import html2text
import pendulum
from mailer import Mailer, Message

import rssalertbot
from .util import guess_level, strip_html

log = logging.getLogger(__name__)

SLACK_COLORS = {
    'warning':  '#ffc300',
    'good':     '#00cc00',
    'alert':    '#cc0000',
}
SLACK_ICONS = {
    'warning':  'warning',
    'good':     'heavy_check_mark',
    'alert':    'fire',
}


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

    logger.debug("[%s]] Alerting email: %s", feed.name, entry.title)

    description = strip_html(entry.description)

    try:
        smtp = Mailer(host=cfg['server'])
        message = Message(charset="utf-8", From=cfg['from'], To=cfg['to'],
                          Subject = f"{feed.group['name']} Alert: ({feed.name}) {entry.title}")
        message.Body = f"Feed: {feed.name}\nDate: {entry.datestring}\n\n{description}"
        message.header('X-Mailer', 'rssalertbot')
        smtp.send(message)

    except Exception:
        logger.exception("[%s] Error sending mail", feed.name)


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

    logger.warning("[%s] %s: %s", feed.name, entry.published, entry.title)
    if entry.description:
        logger.debug("[%s] %s", feed.name, entry.description)


async def alert_slack(feed, cfg, entry, level=None):
    """
    Sends alert to slack if enabled.

    Args:
        feed (:py:class:`Feed`): the feed
        cfg (dict):              output config
        entry (dict):            the feed entry
        level (str):             forced level for this alert
    """
    logger = logging.LoggerAdapter(log, extra = {
        'feed':  feed.name,
        'group': feed.group['name'],
    })
    logger.setLevel(logging.DEBUG)
    logger.debug("[%s] Alerting slack: %s", feed.name, entry.title)

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

    # use the provided level if we've got a force
    if cfg.get('force_level'):
        level = cfg.get('force_level')

    # try to guess the level
    elif cfg.get('levels'):
        levels = cfg.get('levels')
        matches = '(' + '|'.join(levels.keys()) + ')'
        m = re.search(matches, matchstring)
        if m:
            for (s, c) in levels.items():
                if s in m.groups(1):
                    level = c
                    break

    # if the level isn't set already, try some defaults
    if not level:
        level = guess_level(matchstring)

    # cleanup description to get it supported by slack - might figure out
    # something more elegant later

    desc = html2text.html2text(entry.description)
    desc = desc.replace('**', '*')
    desc = desc.replace('\\', '')
    desc = desc.replace('<', '&lt;')
    desc = desc.replace('>', '&gt;')
    desc = desc.replace('&', '&amp;')

    blocks = _make_blocks(
        feed        = feed.name,
        title       = entry.title,
        message     = desc,
        alert_class = level,
        date        = entry.datestring)


    def on_result(channel, future):
        response = future.result()
        if response['ok']:
            logger.debug("Sent message to slack channel %s", channel)
        else:
            logger.warning("Slack error: %s", response['response_metadata'])


    try:
        sc = slack.WebClient(cfg.get('token'), run_async = True)
        channels = cfg.get('channel')
        if not isinstance(channels, list):
            channels = [channels]
        for channel in channels:
            await sc.chat_postMessage(
                user        = rssalertbot.BOT_USERNAME,
                channel     = channel,
                mrkdwn      = True,
                as_user     = True,
                text        = f"*{feed.name}*",
                attachments = blocks,
            )

    except Exception:
        logger.exception("[%s] Error contacting Slack", feed.name)


def _make_blocks(feed, title, message, alert_class = 'warning', date=None):
    """Makes the attachments for the slack message"""

    if not date:
        date = pendulum.now('utc').to_rfc1123_string()

    return [
        {
            "color":        SLACK_COLORS[alert_class],
            "blocks":       [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":{SLACK_ICONS[alert_class]}: *{title}*",
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message,
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Date:*\n{date}",
                        }
                    ]
                }
            ]
        }
    ]
