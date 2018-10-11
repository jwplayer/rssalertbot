import logging
import os
import pendulum
import zc.lockfile

from . import BaseLocker

log = logging.getLogger(__name__)


class FileLocker(BaseLocker):

    def __init__(self, path='/var/lock/'):
        self.basepath = path
        self.locks = {}


    def acquire_lock(self, key, lease_time=3600, **kwargs) -> bool:
        """
        Acquire a lock.

        Args:
            key (str):        The key representing the log
            lease_time (int): Length of lock, in seconds

        Return:
            bool: whether you got a lock or not
        """

        lockfile = os.path.join(self.basepath, f'rssalertbot-{key}.lock')

        try:
            self.locks[key] = zc.lockfile.LockFile(lockfile, content_template='{pid};{hostname}')
            log.debug(f"Acquired lock '{key}' on {lockfile}")
            return True
        except zc.lockfile.LockError:

            # we've already got a lockfile here, so we should check the age of it
            # - if it's older than the lease time, we can re-acquire, otherwise
            # nope!
            stats = os.stat(lockfile)
            age = pendulum.now() - pendulum.from_timestamp(stats.st_mtime)
            if age > lease_time:
                log.debug(f"Acquired lock '{key}' on {lockfile}")
                return True

            # no you can't have this lock
            log.debug(f"Lock '{key}' denied")
            return False


    def release_lock(self, key, **kwargs):
        """
        Release a lock.

        Args:
            key (str):        The key representing the log
        """
        if key in self.locks:
            self.locks[key].close()
            del(self.locks[key])
            log.debug(f"Released lock '{key}'")
