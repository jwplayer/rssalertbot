#########
Changelog
#########

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
