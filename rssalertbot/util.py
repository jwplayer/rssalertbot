"""
Miscellaneous utilities.
"""

import copy
from html.parser import HTMLParser

import rssalertbot


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
    """
    Strip HTML from the given data.

    Args:
        html (str): HTML string

    Returns:
        str: stripped data
    """
    s = HTMLStripper()
    s.feed(html)
    return s.get_data()


def guess_color(message):
    """
    Try to guess the color of the message.

    Args:
        message (str): the message to search

    Returns:
        dict: a dictionary where the key is the output type (i.e. 'slack')
              and the value is the string which represents the color.

    """
    teststring = message.lower()

    if any(key in teststring for key in rssalertbot.KEYS_GREEN):
            return {"slack": "good"}

    if any(key in teststring for key in rssalertbot.KEYS_YELLOW):
            return {"slack": "warning"}

    return {"slack": "danger"}


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
