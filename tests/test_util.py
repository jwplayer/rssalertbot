
import unittest

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


    def test_guess_color(self):
        """
        In which we test all the colors are those we think they should be.
        """
        result = util.guess_color("monkey")
        self.assertIn('slack', result)
        self.assertEqual(result['slack'], 'danger')

        for key in rssalertbot.KEYS_YELLOW:
            result = util.guess_color(key)
            self.assertIn('slack', result)
            self.assertEqual(result['slack'], 'warning')

        for key in rssalertbot.KEYS_GREEN:
            result = util.guess_color(key)
            self.assertIn('slack', result)
            self.assertEqual(result['slack'], 'good')
