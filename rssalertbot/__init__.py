#!/usr/bin/env python
"""
RSS feed monitoring robot.
"""

from pkg_resources  import get_distribution, DistributionNotFound


__author__    = 'Michael Stella <michael@jwplayer.com>'

# get the version from the installed package
try:
    __version__ = get_distribution('rssalertbot').version
except DistributionNotFound:
    # package is not installed
    __version__ = '0.1.0-alpha'

BOT_USERNAME = 'RSS Alert Bot'

KEYS_GREEN  = (
    'complete', 'completed',
    'recovered', 'recovery',
    'resolved',
    'scheduled',
)
KEYS_YELLOW = (
    'identified',
    'investigating',
    'in progress',
    'mitigated',
    'monitoring',
    'testing',
    'update',
    'verifying',
)

FEED_TIMEOUT = 10

RE_ALERT_DEFAULT = '24h'

BOGUS_TIMEZONES = {
    'PST': -800,
    'PDT': -700,
    'MST': -700,
    'MDT': -600,
    'CST': -600,
    'CDT': -500,
    'EST': -500,
    'EDT': -400,
}

LOG_FORMAT = '%(asctime)s %(levelname)-7s [%(module)s.%(funcName)s:%(lineno)d] %(message)s'
