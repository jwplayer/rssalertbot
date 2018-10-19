
import mock
import pendulum
import unittest
from box import Box

from rssalertbot.config  import Config
from rssalertbot.feed    import Feed
from rssalertbot.storage import BaseStorage
import rssalertbot.alerts

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


class TestFeeds(unittest.TestCase):

    def test_setup(self):
        """
        In which we test that a feed was created properly.
        """

        config = Config()

        feed = Feed(mock.MagicMock(), config, MockStorage(),
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


    def test_alerts_enabled(self):
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
                    'enabled': True,
                },
            },
        })

        feed = Feed(mock.MagicMock(), config, MockStorage(),
                    group, testdata['name'], testdata['url'])

        self.assertTrue(feed.outputs.get('email.enabled'))
        self.assertTrue(feed.outputs.get('log.enabled'))
        self.assertTrue(feed.outputs.get('slack.enabled'))

        rssalertbot.alerts.alert_email = mock.MagicMock()
        rssalertbot.alerts.alert_log = mock.MagicMock()
        rssalertbot.alerts.alert_slack = mock.MagicMock()
        feed.alert(self.make_entry())
        rssalertbot.alerts.alert_email.assert_called()
        rssalertbot.alerts.alert_log.assert_called()
        rssalertbot.alerts.alert_slack.assert_called()


    def test_alerts_disabled(self):
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

        feed = Feed(mock.MagicMock(), config, MockStorage(),
                    group, testdata['name'], testdata['url'])

        self.assertFalse(feed.outputs.get('email.enabled'))
        self.assertFalse(feed.outputs.get('slack.enabled'))

        # the group overrides this one!
        self.assertTrue(feed.outputs.get('log.enabled'))

        rssalertbot.alerts.alert_email = mock.MagicMock()
        rssalertbot.alerts.alert_log = mock.MagicMock()
        rssalertbot.alerts.alert_slack = mock.MagicMock()
        feed.alert(self.make_entry())
        rssalertbot.alerts.alert_email.assert_not_called()
        rssalertbot.alerts.alert_slack.assert_not_called()

        # again, the group overrides this!
        rssalertbot.alerts.alert_log.assert_called()


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
