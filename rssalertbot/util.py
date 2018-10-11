import signal

from html.parser    import HTMLParser

import rssalertbot


def timeout(func, args=(), kwargs={}, timeout_duration=rssalertbot.FEED_TIMEOUT, default=None):
    class TimeoutError(Exception):
        pass

    def handler(signum, frame):
        raise TimeoutError()

    # set the timeout handler
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout_duration)
    try:
        result = func(*args, **kwargs)
    except TimeoutError as e:
        result = default
    finally:
        signal.alarm(0)

    return result



class HTMLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
        self.strict = False
        self.convert_charrefs = True

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_html(html):
    s = HTMLStripper()
    s.feed(html)
    return s.get_data()


def guess_color(matchstring):
    """Try to guess the color of the message"""

    for key in rssalertbot.KEYS_GREEN:
        if key in matchstring:
            return {"hipchat_color": "green", "slack_color": "good"}

    for key in rssalertbot.KEYS_YELLOW:
        if key in matchstring:
            return {"hipchat_color": "yellow", "slack_color": "warning"}

    return {"hipchat_color": "red", "slack_color": "danger"}
