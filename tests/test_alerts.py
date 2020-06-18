
import pendulum
import testfixtures
import unittest

from box import Box
from unittest.mock import AsyncMock, MagicMock, patch

import rssalertbot.alerts


class Feed:
    name = "test"
    group = {
        'name': 'testgroup'
    }


class MockMailer:
    send = MagicMock()

    def __init__(self, *args, **kwargs):
        pass


class AlertsTest(unittest.IsolatedAsyncioTestCase):

    alertmsg = Box({
        'title':        'test alert',
        'description':  'this is a test alert',
        'published':    pendulum.now('UTC'),
        'datestring':   pendulum.now().to_rfc1123_string(),
    })


    def test_alert_log(self):
        feed = Feed()

        with testfixtures.LogCapture() as capture:
            rssalertbot.alerts.alert_log(feed, MagicMock(), self.alertmsg)

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
        rssalertbot.alerts.Mailer.send = MagicMock()
        rssalertbot.alerts.alert_email(feed, config, self.alertmsg)

        # just make sure we've called this
        rssalertbot.alerts.Mailer.send.assert_called()


    async def test_alert_slack(self):

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

        with patch('slack.WebClient', new=AsyncMock) as slackclient:
            # we want this to have been called
            slackclient.chat_postMessage = AsyncMock()

            await rssalertbot.alerts.alert_slack(feed, config, self.alertmsg)

            slackclient.chat_postMessage.assert_awaited()
