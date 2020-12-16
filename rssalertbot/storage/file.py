import datetime
import logging
import os
import pendulum

from . import BaseStorage

log = logging.getLogger(__name__)


class FileStorage(BaseStorage):
    """
    Store state in files.
    """

    def __init__(self, path='/var/run/rss_state'):
        self.basepath = path


    def _datafile(self, filename):
        return os.path.join(self.basepath, f'last.{filename}.dat')


    def _read_file(self, filename):
        try:
            with open(self._datafile(filename), 'r') as f:
                return pendulum.parse(f.read().strip())
        except IOError:
            return None


    def _write_file(self, filename, date):
        # just in case someone didn't follow the type hints
        if isinstance(date, datetime.datetime):
            date = pendulum.from_timestamp(date.timestamp())
        with open(self._datafile(filename), 'w') as f:
            f.write(str(date.in_tz('UTC')))


    def last_update(self, feed) -> pendulum.DateTime:
        """
        Get the last updated date for the given feed
        """
        return self._read_file(feed)


    def save_date(self, feed, date: pendulum.DateTime):
        """
        Save the last updated date for the given feed
        """
        self._write_file(feed, date)


    def load_event(self, feed, event_id):
        """
        Load the last sent date for an event
        """
        return self._read_file(self._event_name(feed, event_id))


    def save_event(self, feed, event_id, date: pendulum.DateTime):
        """
        Save the last sent date for an event
        """
        self._write_file(self._event_name(feed, event_id), date)


    def delete_event(self, feed, event_id):
        """
        Delete an event
        """
        os.remove(self._datafile(self._event_name(feed, event_id)))
