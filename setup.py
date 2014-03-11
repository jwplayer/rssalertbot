#!/usr/bin/env python

from setuptools import setup

setup(
    name            = 'rssalertbot',
    version         = '1.0',
    description     = 'RSS fetch and alert bot',
    author          = 'Michael Stella',
    author_email    = 'michael@jwplayer.com',
    url             = 'https://github.com/JWPlayer/rssalertbot',
    scripts         = ['rssalertbot'],
    install_requires = ['feedparser', 'mailer', 'python-dateutil', 'pytz', 'python-simple-hipchat'],
    dependency_links = ['git://github.com/kurttheviking/python-simple-hipchat.git#egg=python-simple-hipchat'],
    classifiers     = [
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ]
)
