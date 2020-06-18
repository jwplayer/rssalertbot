
import copy
import pendulum
import testfixtures
import unittest
from box import Box
from unittest.mock import AsyncMock, MagicMock, patch

from rssalertbot.config  import Config
from rssalertbot.feed    import Feed
from rssalertbot.storage import BaseStorage

group = Box({
    "name": "Test Group",
    "outputs": {
        "log": {
            "enabled": True,
        }
    }
})

testdata = {
    "name": "test feed",
    "url": "http://localhost:8930",
}


class MockStorage(BaseStorage):

    def __init__(self, *args, **kwargs):
        self.data = {}


    def last_update(self, feed) -> pendulum.DateTime:
        return self.data.get(feed, pendulum.now('UTC'))


    def save_date(self, feed, date: pendulum.DateTime):
        self.data[feed] = date


class TestFeeds(unittest.IsolatedAsyncioTestCase):

    def test_setup(self):
        """
        In which we test that a feed was created properly.
        """

        config = Config()

        feed = Feed(MagicMock(), config, MockStorage(),
                    group, testdata['name'], testdata['url'])

        # test the basics
        self.assertEqual(feed.name, testdata['name'])
        self.assertEqual(feed.url, testdata['url'])

        # test this stuff got merged from the group
        self.assertIn('log', feed.outputs)
        self.assertIn('enabled', feed.outputs['log'])
        self.assertTrue(feed.outputs['log']['enabled'])

        # test we can get save a date and get it back
        date = pendulum.now('UTC')
        feed.save_date(date)
        self.assertEqual(date, feed.previous_date)


    async def test_alerts_enabled(self):
        """
        In which we make sure enabled alerts are called.
        """

        config = Config({
            'outputs': {
                'email': {
                    'enabled': True,
                    'from':    'monkey@jwplayer.test',
                    'to':      'monkey@jwplayer.test',
                },
                'log': {
                    'enabled': True,
                },
                'slack': {
                    'enabled':  True,
                    'token':    'monkeys',
                    'channel':  '#foo',
                },
            },
        })

        feed = Feed(MagicMock(), config, MockStorage(),
                    group, testdata['name'], testdata['url'])

        self.assertTrue(feed.outputs.get('email.enabled'))
        self.assertTrue(feed.outputs.get('log.enabled'))
        self.assertTrue(feed.outputs.get('slack.enabled'))

        with patch('rssalertbot.alerts', new=AsyncMock) as alerts:
            alerts.alert_email = MagicMock()
            alerts.alert_log = MagicMock()
            alerts.alert_slack = AsyncMock()

            await feed.alert(self.make_entry())
            alerts.alert_email.assert_called()
            alerts.alert_log.assert_called()
            alerts.alert_slack.assert_awaited()


    def test_alert_slack_missing_values(self):

        config = Config({
            'outputs': {
                'slack': {
                    'enabled': True,
                }
            }
        })

        mygroup = copy.deepcopy(group)
        with testfixtures.LogCapture() as capture:
            Feed(
                loop     = MagicMock(),
                cfg      = config,
                storage  = MockStorage(),
                group    = mygroup,
                name     = testdata['name'],
                url      = testdata['url'],
            )

            capture.check_present(
                ('rssalertbot.feed', 'ERROR', 'Slack enabled but slack.channel not set!'),
                ('rssalertbot.feed', 'ERROR', 'Slack enabled but slack.token not set!'),
                order_matters=False,
            )


    async def test_alerts_disabled(self):
        """
        In which we make sure disabled alerts are NOT called.
        """
        config = Config({
            'outputs': {
                'email': {
                    'enabled': False,
                    'from':    'monkey@jwplayer.test',
                    'to':      'monkey@jwplayer.test',
                },
                'log': {
                    'enabled': False,
                },
                'slack': {
                    'enabled': False,
                },
            },
        })

        feed = Feed(MagicMock(), config, MockStorage(),
                    group, testdata['name'], testdata['url'])

        self.assertFalse(feed.outputs.get('email.enabled'))
        self.assertFalse(feed.outputs.get('slack.enabled'))

        # the group overrides this one!
        self.assertTrue(feed.outputs.get('log.enabled'))

        with patch('rssalertbot.alerts') as alerts:
            alerts.alert_email = MagicMock()
            alerts.alert_log = MagicMock()
            alerts.alert_slack = AsyncMock()

            await feed.alert(self.make_entry())
            alerts.alert_email.assert_not_called()
            alerts.alert_slack.assert_not_awaited()

            # again, the group overrides this!
            alerts.alert_log.assert_called()


    def make_entry(self, title="test entry", description="test description", date=None):
        """
        Make a test entry
        """
        date = date or pendulum.now('UTC')
        return Box({
            'title':        title,
            'description':  description,
            'published':    date,
            'datestring':   date.to_rfc1123_string(),
        })
