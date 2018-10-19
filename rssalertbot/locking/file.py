import logging
import os
import pendulum
import zc.lockfile

from . import BaseLocker, Lock, LockNotAcquired

log = logging.getLogger(__name__)


class FileLocker(BaseLocker):
    """
    Use files for locking.
    """

    def __init__(self, path='/var/lock/'):
        self.basepath = path
        self.locks = {}


    def acquire_lock(self, key, lease_time=3600, **kwargs) -> Lock:

        lockfile = os.path.join(self.basepath, f'rssalertbot-{key}.lock')

        # create our release callback
        def release():
            self.release_lock(key)

        try:
            self.locks[key] = zc.lockfile.LockFile(lockfile, content_template='{pid};{hostname}')
            log.debug(f"Acquired lock '{key}' on {lockfile}")

            return Lock(release, expires = pendulum.now().add(3600))

        except zc.lockfile.LockError:

            # we've already got a lockfile here, so we should check the age of it
            # - if it's older than the lease time, we can re-acquire, otherwise
            # nope!
            stats = os.stat(lockfile)
            expires = pendulum.from_timestamp(stats.st_mtime)
            age = pendulum.now() - expires
            if age > lease_time:
                log.debug(f"Acquired lock '{key}' on {lockfile}")
                return Lock(release, expires)

            # no you can't have this lock
            log.debug(f"Lock '{key}' denied")
            raise LockNotAcquired()


    def release_lock(self, key, **kwargs):

        if key in self.locks:
            self.locks[key].close()
            del(self.locks[key])
            log.debug(f"Released lock '{key}'")
