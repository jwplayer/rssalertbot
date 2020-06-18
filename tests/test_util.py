
import unittest
from parameterized import parameterized

import rssalertbot
import rssalertbot.util as util


class UtilTest(unittest.TestCase):

    def test_strip_html(self):
        message = """<html>
    <head>
      <title>this is a test file</title>
    </head>
    <body>
      <p>Hello world!</p>
    </body>
</html>"""

        stripped = util.strip_html(message)
        self.assertNotIn('<', stripped)
        self.assertIn('Hello world!', stripped)


    @parameterized.expand(rssalertbot.KEYS_GREEN)
    def test_guess_level_good(self, text):
        result = util.guess_level(text)
        self.assertEqual(result, 'good')

    @parameterized.expand(rssalertbot.KEYS_YELLOW)
    def test_guess_level_warning(self, text):
        result = util.guess_level(text)
        self.assertEqual(result, 'warning')

    @parameterized.expand(('bogus', 'error', 'panic'))
    def test_guess_level_alert(self, text):
        result = util.guess_level(text)
        self.assertEqual(result, 'alert')
