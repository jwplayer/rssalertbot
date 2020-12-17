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
    not_found_exception_class = IOError

    def __init__(self, path='/var/run/rss_state'):
        self.basepath = path


    def _datafile(self, filename):
        return os.path.join(self.basepath, f'last.{filename}.dat')


    def _read(self, name):
        with open(self._datafile(name), 'r') as f:
            return pendulum.parse(f.read().strip())


    def _write(self, name, date):
        # just in case someone didn't follow the type hints
        if isinstance(date, datetime.datetime):
            date = pendulum.from_timestamp(date.timestamp())
        with open(self._datafile(name), 'w') as f:
            f.write(str(date.in_tz('UTC')))


    def _delete(self, name):
        os.remove(self._datafile(name))
