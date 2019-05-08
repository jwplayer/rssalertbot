
import pendulum
import mock
import testfixtures
import unittest

from box import Box

import rssalertbot.alerts


class Feed:
    name = "test"
    group = {
        'name': 'testgroup'
    }


class MockMailer:
    send = mock.MagicMock()

    def __init__(self, *args, **kwargs):
        pass


class AlertsTest(unittest.TestCase):

    alertmsg = Box({
        'title':        'test alert',
        'description':  'this is a test alert',
        'published':    pendulum.now('UTC'),
        'datestring':   pendulum.now().to_rfc1123_string(),
    })


    def test_alert_log(self):
        feed = Feed()

        with testfixtures.LogCapture() as capture:
            rssalertbot.alerts.alert_log(feed, mock.MagicMock(), self.alertmsg)

            capture.check_present(
                (
                    'rssalertbot.alerts',
                    'WARNING',
                    f"[{feed.name}] {self.alertmsg.published}: {self.alertmsg.title}",
                )
            )


    def test_alert_email(self):
        config = {
            'server': 'localhost',
            'from':   'test@nothing.test',
            'to':     'test@nothing.test',
        }
        feed = Feed()

        # mock :allthethings:
        rssalertbot.alerts.Mailer = MockMailer
        rssalertbot.alerts.Mailer.send = mock.MagicMock()
        rssalertbot.alerts.alert_email(feed, config, self.alertmsg)

        # just make sure we've called this
        rssalertbot.alerts.Mailer.send.assert_called()


    def test_alert_slack(self):

        config = {
            'outputs': {
                'slack': {
                    'enabled': True,
                    'channel': '#foo',
                    'token':   'monkeys',
                }
            }
        }

        feed = Feed()

        # mock the import
        import sys
        mock_client = mock.MagicMock()
        mock_client.api_call = mock.MagicMock()
        slackclient = mock.MagicMock()
        slackclient.SlackClient = mock.MagicMock(return_value = mock_client)

        sys.modules['slackclient'] = slackclient

        rssalertbot.alerts.alert_slack(feed, config, self.alertmsg)

        mock_client.api_call.assert_called()
