#!/usr/bin/env python

import os
import re
from setuptools import setup

VERSION = "0.1.0a1"
# this is overwritten by the makefile.
try:
    with open(os.path.join(os.path.dirname(__file__), 'CHANGELOG.rst'), 'r') as f:
        for line in f.readlines():
            m = re.match('(\d+\.\d+\.\d+\S*)', line)
            if m:
                VERSION = m.group(1)
                break
except:
    import warnings
    warnings.warn("version not found, defaulting to {}".format(VERSION))


setup(
    name            = 'rssalertbot',
    version         = VERSION,
    description     = 'RSS fetch and alert bot',
    author          = 'Michael Stella',
    author_email    = 'michael@jwplayer.com',
    url             = 'https://github.com/JWPlayer/rssalertbot',
    scripts         = ['rssalertbot'],
    install_requires = [
        'requests',
        'feedparser',
        'mailer',
        'python-dateutil',
        'pytz',
        'python-simple-hipchat==0.4.0',
    ],
    python_requires = ">=3.6",
    classifiers     = [
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ]
)
