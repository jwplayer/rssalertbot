
import copy
import feedparser
import pendulum
import testfixtures
import unittest
from box import Box
from hashlib import md5
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

    def _read(self, name):
        return self.data.get(name)

    def _write(self, name, date):
        self.data[name] = date

    def _delete(self, name):
        del self.data[name]


class TestFeeds(unittest.IsolatedAsyncioTestCase):

    def test_setup(self):
        """
        In which we test that a feed was created properly.
        """

        config = Config()

        feed = Feed(config, MockStorage(), group, testdata['name'], testdata['url'])

        # test the basics
        self.assertEqual(feed.name, testdata['name'])
        self.assertEqual(feed.url, testdata['url'])

        # test this stuff got merged from the group
        self.assertIn('log', feed.outputs)
        self.assertIn('enabled', feed.outputs['log'])
        self.assertTrue(feed.outputs['log']['enabled'])

        # test we can get save a date and get it back
        date = pendulum.now('UTC')
        feed.storage.save_date(feed.feed, date)
        self.assertEqual(date, feed.previous_date())


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

        feed = Feed(config, MockStorage(), group, testdata['name'], testdata['url'])

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

        feed = Feed(config, MockStorage(), group, testdata['name'], testdata['url'])

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


    def test_previous_date_recent(self):
        stored_date = pendulum.now('UTC').subtract(minutes=10)
        storage = MockStorage()
        storage.data = {f"{group.name}-{testdata['name']}": stored_date}
        feed = Feed(Config(), storage, group, testdata['name'], testdata['url'])
        self.assertEqual(stored_date, feed.previous_date())


    def test_previous_date_old(self):
        stored_date = pendulum.now('UTC').subtract(days=10)
        storage = MockStorage()
        storage.data = {f"{group.name}-{testdata['name']}": stored_date}
        feed = Feed(Config(), storage, group, testdata['name'], testdata['url'])
        self.assertEqual(pendulum.yesterday('UTC'), feed.previous_date())


    def test_previous_date_not_found(self):
        storage = MockStorage()
        storage.data = {f"{group.name}-{testdata['name']}": None}
        feed = Feed(Config(), storage, group, testdata['name'], testdata['url'])
        self.assertEqual(pendulum.yesterday('UTC'), feed.previous_date())


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


class TestFeedProcessing(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.now = pendulum.now('UTC')
        self.publish_date = self.now
        self.event_title = "Incident: Things are not going well!"
        self.event_description = "Issue summary: OH NO"
        self.storage = MockStorage()
        self.storage.save_event = MagicMock(wraps=self.storage.save_event)
        self.storage.delete_event = MagicMock(wraps=self.storage.delete_event)
        self.feed = Feed(Config(), self.storage, group, testdata['name'], testdata['url'])
        self.feed.alert = AsyncMock()


    def storage_name(self):
        event_id = md5((self.event_title + self.event_description).encode()).hexdigest()
        return f"{self.feed.feed}-{event_id}"


    async def process_feed(self, rss=None):
        if not rss:
            rss = f"""
            <rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
                <channel>
                    <title>Fake System Status</title>
                    <link>https://status.fake.system/</link>
                    <description>Fake System Status Notices</description>
                    <lastBuildDate>{self.publish_date.to_rss_string()}</lastBuildDate>
                    <item>
                        <title>{self.event_title}</title>
                        <description>{self.event_description}</description>
                        <pubDate>{self.publish_date.to_rss_string()}</pubDate>
                        <link>https://status.fake.system/abcdef</link>
                        <guid>https://status.fake.system/abcdef</guid>
                    </item>
                </channel>
            </rss>
            """
        self.feed.fetch_and_parse = AsyncMock(return_value=feedparser.parse(rss).entries)
        await self.feed.process()


    def assert_timestamps_equal(self, stamp1, stamp2):
        self.assertEqual(0, stamp1.diff(stamp2).in_seconds())


    async def test_process_empty(self):
        await self.process_feed('<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0"></rss>')
        self.feed.storage.save_event.assert_not_called()
        self.feed.alert.assert_not_called()
        self.storage.delete_event.assert_not_called()
        self.assertNotIn(self.feed.feed, self.storage.data)


    async def test_process_message_too_old(self):
        self.publish_date = self.publish_date.subtract(days=5)
        await self.process_feed()
        self.storage.save_event.assert_not_called()
        self.feed.alert.assert_not_called()
        self.storage.delete_event.assert_not_called()
        self.assertNotIn(self.feed.feed, self.storage.data)


    async def test_process_recent(self):
        self.publish_date = self.publish_date.subtract(minutes=5)
        await self.process_feed()
        self.feed.storage.save_event.assert_not_called()
        self.feed.alert.assert_called()
        self.feed.storage.delete_event.assert_not_called()
        self.assert_timestamps_equal(self.publish_date, self.feed.storage.data[self.feed.feed])


    async def test_process_new_future_event(self):
        self.publish_date = self.publish_date.add(minutes=10)
        await self.process_feed()
        self.assert_timestamps_equal(self.now, self.storage.data[self.storage_name()])
        self.feed.alert.assert_called()
        self.storage.delete_event.assert_not_called()
        self.assertNotIn(self.feed.feed, self.storage.data)


    async def test_process_seen_future_event_realert(self):
        self.publish_date = self.publish_date.add(minutes=10)
        storage_name = self.storage_name()
        self.storage.data[storage_name] = self.now.subtract(days=2)
        await self.process_feed()
        self.assert_timestamps_equal(self.now, self.storage.data[storage_name])
        self.feed.alert.assert_called()
        self.storage.delete_event.assert_not_called()
        self.assertNotIn(self.feed.feed, self.storage.data)


    async def test_process_seen_future_event_custom_realert(self):
        self.publish_date = self.publish_date.add(minutes=10)
        self.feed.cfg["re_alert"] = 1
        storage_name = self.storage_name()
        self.storage.data[storage_name] = self.now.subtract(hours=2)
        await self.process_feed()
        self.assert_timestamps_equal(self.now, self.storage.data[storage_name])
        self.feed.alert.assert_called()
        self.storage.delete_event.assert_not_called()
        self.assertNotIn(self.feed.feed, self.storage.data)


    async def test_process_seen_future_event(self):
        self.publish_date = self.publish_date.add(minutes=10)
        self.storage.data[self.storage_name()] = self.now.subtract(minutes=5)
        await self.process_feed()
        self.feed.storage.save_event.assert_not_called()
        self.feed.alert.assert_not_called()
        self.storage.delete_event.assert_not_called()
        self.assertNotIn(self.feed.feed, self.storage.data)


    async def test_process_seen_event_from_past(self):
        self.publish_date = self.publish_date.subtract(minutes=10)
        storage_name = self.storage_name()
        self.storage.data[storage_name] = self.now.subtract(hours=5)
        await self.process_feed()
        self.storage.save_event.assert_not_called()
        self.feed.alert.assert_called()
        self.assertNotIn(storage_name, self.storage.data)
        self.assert_timestamps_equal(self.publish_date, self.storage.data[self.feed.feed])


    async def test_process_multiple_messages(self):
        self.publish_date = self.publish_date.subtract(minutes=10)
        future_event_title = "Notice: The future is coming"
        future_event_description = "Issue summary: something's gonna happen but I forget what"
        rss = f"""
        <rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
            <channel>
                <title>Fake System Status</title>
                <link>https://status.fake.thing/</link>
                <description>Fake System Status Notices</description>
                <lastBuildDate>{self.publish_date.to_rss_string()}</lastBuildDate>
                <item>
                    <title>{future_event_title}</title>
                    <description>{future_event_description}</description>
                    <pubDate>{self.publish_date.add(days=2).to_rss_string()}</pubDate>
                    <link>https://status.fake.thing/zyxwvu</link>
                    <guid>https://status.fake.thing/zyxwvu</guid>
                </item>
                <item>
                    <title>Recovery: Things are okay I guess</title>
                    <description>Issue summary: yeah it's alright now</description>
                    <pubDate>{self.publish_date.to_rss_string()}</pubDate>
                    <link>https://status.fake.thing/ghijkl</link>
                    <guid>https://status.fake.thing/ghijkl</guid>
                </item>
                <item>
                    <title>{self.event_title}</title>
                    <description>{self.event_description}</description>
                    <pubDate>{self.publish_date.subtract(minutes=10).to_rss_string()}</pubDate>
                    <link>https://status.fake.thing/abcdef</link>
                    <guid>https://status.fake.thing/abcdef</guid>
                </item>
            </channel>
        </rss>
        """
        self.event_title = future_event_title
        self.event_description = future_event_description
        self.storage.data[self.storage_name()] = self.now.subtract(minutes=5)
        await self.process_feed(rss)
        self.storage.save_event.assert_not_called()
        self.assertEqual(2, self.feed.alert.call_count)
        self.storage.delete_event.assert_not_called()
        self.assert_timestamps_equal(self.publish_date, self.storage.data[self.feed.feed])
