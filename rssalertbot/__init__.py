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
    'scheduled',
    'testing',
    'update',
    'verifying',
)

FEED_TIMEOUT = 10

BOGUS_TIMEZONES = {
    'PST': '-0800',
    'PDT': '-0700',
    'MST': '-0700',
    'MDT': '-0600',
    'CST': '-0600',
    'CDT': '-0500',
    'EST': '-0500',
    'EDT': '-0400',
}

LOG_FORMAT = '%(levelname)-7s [%(module)s.%(funcName)s:%(lineno)d] %(message)s'
LOG_FORMAT_FEED = '%(levelname)-7s [%(module)s.%(funcName)s:%(lineno)d] [%(feed)s] %(message)s'
