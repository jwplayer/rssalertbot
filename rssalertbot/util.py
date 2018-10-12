import copy
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
    teststring = matchstring.lower()

    for key in rssalertbot.KEYS_GREEN:
        if key in teststring:
            return {"hipchat_color": "green", "slack_color": "good"}

    for key in rssalertbot.KEYS_YELLOW:
        if key in teststring:
            return {"hipchat_color": "yellow", "slack_color": "warning"}

    return {"hipchat_color": "red", "slack_color": "danger"}


def deepmerge(a, b):
    """Deeply merge nested dictionaries.

      Keys in dict `b` are given priority over those in `a`. Note that if
      `b` is not a dictionary, then `b` will be returned. This is useful
      if overriding a block.

      Args:
          a (dict): Base dictionary
          b (dict): Dictionary that will be merged on top of `a`

      Returns:
          dict: A dictionary where present in `b` are given priority over
              those in `a`.

      References:
          https://www.xormedia.com/recursively-merge-dictionaries-in-python/
    """

    if not isinstance(b, dict):
        return b

    merge = copy.deepcopy(a)
    for key, val in b.items():
        if key in merge and isinstance(merge[key], dict):
            merge[key] = deepmerge(merge[key], val)
        else:
            merge[key] = copy.deepcopy(val)
    return merge
