#########
Changelog
#########

2.4.0 (mgundel)
---------------

* Add better handling for future events, with global re-alerting configuration
  - resolves `<https://github.com/jwplayer/rssalertbot/issues/9>`_

2.3.3 (alertedsnake)
--------------------

* Modernize async stuff, fix issues handling awaits
* Set up timezone in Docker - this is needed for timing

2.3.1 (alertedsnake)
--------------------

* Minor bugfixes
* Do async tests properly

2.3.0 (alertedsnake)
--------------------

* Additional/better logging
* Removed anything which messes with the log format or root logger,
  you should do this yourself.
* Reworked the ``cli.py`` file so it only does the cli stuff and nothing else
* Update slackclient to 2.0.0, do many more things async as a result
* Add config sanity checks
* **BREAKING**: ``color`` in configs is now ``level``, so you can set the
  mapping from message to warning level, not the color directly in
  configuration.  This was done to be accurate at setting a color *and* an icon
  with Slack.  Leaving ``color`` in your config will not break anything, it will
  just be ignored.

2.2.2 (alertedsnake)
--------------------

* Allow output to multiple slack channels
* Pass log level into feed processor

2.1.2 (alertedsnake)
--------------------

* Okay, passing in one more option to clean up some bogus timezone warnings.

2.1.1 (alertedsnake)
--------------------

* Dateparser breaks with weird TZ offsets, like `-0000` - I submitted a bug:
  https://github.com/scrapinghub/dateparser/issues/458 .
  In the meantime, why did I use that instead of `dateutil.parser` anyway?
  Updated.

2.1.0 (alertedsnake)
--------------------

* Added config option ``load_dir()`` to merge a ``conf.d`` style directory
  of config files.  We use these at JWPlayer_.
* ``Config.load()`` now will call either ``load_dir()`` or ``load_file()`` as
  appropriate.
* ``--config`` argument now accepts multiple files
* Bugfix: user should be able to write to its homedir

2.0.0 (alertedsnake)
--------------------

Breaking changes:
^^^^^^^^^^^^^^^^^

* Hipchat is no longer supported - it's dead, Jim.
* Removed command-line arguments ``--lock`` and ``--state_path``

New features:
^^^^^^^^^^^^^

* Switched to using AsyncIO for fetching feed data
* Config files can now be YAML or JSON, split handling of such into
  its own python file, and now using :py:mod:`Box` to make working with
  config data easy
* A new locking framework was built, supporting both file locking (as previous),
  and using DynamoDB (for running in containers).
  This framework is extensible for other locking methods.
* A new storage framework was built, supporting both local files and DynamoDB.
  This stores the date of the most recently processed messages, so as to not
  alert on messages already seen.
  This framework is extensible for other storage methods.
* Added a flag for feed groups to alert if fetching a feed fails
* Created a ``Dockerfile`` so you can containerize the thing, and a
  ``docker-compose.yaml`` for example purposes.  It makes some assumptions.
* Created a ``Makefile`` so we can publish this container for real.

Enhancements:
^^^^^^^^^^^^^

* All dates in events will be formated RFC1123 style, in localtime (or
  another TZ if set in the config file)
* Now doing case-insensitive parsing messages for keywords
* Logging now always adds the feed name to messages
* Config file option ``loglevel`` can be used to set the default, command-line
  will always override though.
* Split alerts into their own file, so it's easy to add more
* Most functions and classes documented
* Cleanly handling timeouts and fetch exceptions
* Actual executable is now a entrypoint (as defined in ``setup.py``)
* Added additional message keywords for determining the message color
* Slack and DynamoDB support are now optional, use the extras with pip to
  install those dependencies

1.3.0 (alertedsnake)
--------------------

* Added a `force-colors` argument for Slack, to force a color to always be used
  for a given feed.

1.2.0 (kzapolski)
-----------------

* Add `X-Mailer` header
* Fix notification defaults - wasn't setting them to False if not in the outputs
  block for a feed

1.1.1 (kzapolski)
-----------------

* added slack support
* added lock file support


1.1.0 (alertedsnake)
--------------------

* Full upgrade to Python 3
* Added command-line argument --no-notify to disable notification for testing
* Added command-line argument --version
* Logfile format updated
* Cleanup requirements

.. _JWPlayer: https://jwplayer.com/
