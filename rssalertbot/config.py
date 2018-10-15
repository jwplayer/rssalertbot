"""
For handling the config file data.
"""

import json
import os
import yaml

from box import Box
from .util import deepmerge


class Config(Box):
    """
    A class to deal with our config file in a nice way.
    """

    def __init__(self, *args, **kwargs):
        kwargs['box_it_up'] = True
        super().__init__(*args, **kwargs)


    def get(self, key, default=None):
        """
        Works just like :py:meth:`dict.get` except it allows for
        "dotted notation" to get values far down the dict tree::

            >>> c.set('foo.bar', 1)
            >>> c.get('foo.bar')
            1

        Args:
            key (str): dictionary key
            default:   return this if the key is not found

        Returns:
            value: whatever's there, else the default

        """
        if '.' not in key:
            return super().get(key, default)

        k, rest = key.split('.', 1)
        v = super().get(k, default)

        if isinstance(v, (dict, Config)):
            return v.get(rest, default)

        elif v:
            return v

        else:
            return default


    def set(self, key, value):
        """
        Stores a value in the dictionary.  Works just like
        you'd expect, but 'key' can be in "dotted notation"
        to set deep values::

            >>> c.set('foo.bar', 1)
            >>> c.get('foo.bar')
            1

        Args:
            key (str): where to store the value
            value: data to store.

        """
        if '.' not in key:
            self[key] = value
        else:
            # otherwise we do a crazy mergin' thing
            self.merge_dict(dict_from_dotted_key(key, value))


    def load(self, cfgfile, encoding='utf-8'):
        """Load a config file."""

        if not os.path.isfile(cfgfile):
            raise ValueError(f"Cannot read config file '{cfgfile}'")

        with open(cfgfile, 'r', encoding=encoding) as f:
            if cfgfile.endswith('.json'):
                data_dict = json.load(f)
            elif cfgfile.endswith('.yaml') or cfgfile.endswith('.yml'):
                data_dict = yaml.safe_load(f.read())
            else:
                raise ValueError("unknown file format")

            self.merge_dict(data_dict)


    def merge_dict(self, data):
        """
        Merge a dictionary into the config.
        """

        if not isinstance(data, dict):
            raise TypeError("Argument 'data' must be of type 'dict'")

        self.update(deepmerge(self.to_dict(), data))


def dict_from_dotted_key(key, value):
    """
    Make a dict from a dotted key::

        >>> dict_from_dotted_key('foo.bar.baz', 1)
        {'foo': {'bar': {'baz': 1}}}

    Args:
        key (str): dotted key
        value: value

    Returns:
        dict
    """

    d = {}
    if '.' not in key:
        d[key] = value
        return d

    components = key.split('.')
    last = components.pop()

    leaf = d
    for c in components:
        leaf[c] = {}
        leaf = leaf[c]

    leaf[last] = value
    return d
