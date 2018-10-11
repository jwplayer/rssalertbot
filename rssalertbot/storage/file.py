import datetime
import os
import pendulum

from . import BaseStorage


class FileStorage(BaseStorage):
    """
    Store state in files.
    """

    def __init__(self, path='/var/run/rss_state'):
        self.basepath = path


    def last_update(self, feed) -> pendulum.DateTime:
        """
        Get the last updated date for the given feed
        """
        datafile = os.path.join(self.basepath, f'last.{feed}.dat')
        try:
            with open(datafile, 'rb') as f:
                return pendulum.parse(f.read().strip())
        except IOError as e:
            return pendulum.yesterday('UTC')


    def save_date(self, feed, date: pendulum.DateTime):
        """
        Save the date for the current event.
        """
        # just in case someone didn't follow the type hints
        if isinstance(datetime.datetime):
            date = pendulum.from_timestamp(date.timestamp())

        datafile = os.path.join(self.basepath, f'last.{feed}.dat')
        with open(datafile, 'w') as f:
            f.write(str(date.in_tz('UTC')))
