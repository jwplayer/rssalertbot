#!/usr/bin/env python
"""
RSS feed monitoring robot.

"""

from pkg_resources  import get_distribution, DistributionNotFound


__author__    = 'Michael Stella <michael@jwplayer.com>'

try:
    __version__ = get_distribution('rssalertbot').version
except DistributionNotFound:
    # package is not installed
    __version__ = '0.1.0-alpha'

BOT_USERNAME = 'RSS Alert Bot'

KEYS_GREEN  = ('Completed', 'Resolved', 'RESOLVED')
KEYS_YELLOW = ('Identified', 'Monitoring', 'Update', 'Mitigated', 'Update', 'Scheduled')

LOCK_FILE = '/var/lock/rssalertbot.lock'

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

