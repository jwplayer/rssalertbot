import logging
import pendulum
import time

from pynamodb.attributes import (UnicodeAttribute, UTCDateTimeAttribute)
from pynamodb.exceptions import DoesNotExist
from pynamodb.models     import Model

from . import BaseLocker, LockNotGrantedError

log = logging.getLogger(__name__)


class DynamoLock(Model):
    class Meta:
        table_name           = "GlobalLocking"
        region               = "us-east-1"
        write_capacity_units = 1
        read_capacity_units  = 1

    key         = UnicodeAttribute(hash_key=True)
    owner_name  = UnicodeAttribute()
    expires     = UTCDateTimeAttribute()


class DynamoLocker(BaseLocker):

    def __init__(self, table=None, url=None, region='us-east-1'):

        DynamoLock.region = region
#        if url:
#            log.warning(f"Using DynamoDB url: {url}")
#        if table:
#            log.warning(f"Using DynamoDB table: {table}")

        DynamoLock.create_table()


    def acquire_lock(self, key, owner_name: str='unknown', lease_time: int=3600) -> bool:
        """
        Acquire a lock.

        Args:
            key (str):        The key representing the log
            owner_name (str): Owner associated with the lock.
            lease_time (int): Length of lock, in seconds

        Return:
            bool: whether you got a lock or not
        """

        try:
            old = DynamoLock.get(key)
            # If the lock is not yet expired, and you aren't the owner, you can't have it
            if (pendulum.now('UTC') < old.expires) and old.owner_name != owner_name:
                log.debug(f"Lock {key} denied")
                return False

            # delete the old lock
            old.delete()

        except DoesNotExist:
            pass

        # create the new lock
        lock = DynamoLock(
            key         = key,
            expires     = pendulum.now('UTC').add(seconds = lease_time),
            owner_name  = owner_name,
        )
        lock.save()
        log.debug(f"Lock {lock.key} acquired, expires {lock.expires}")
        return True


    def acquire_lock_wait(self, key, owner_name: str='unknown', lease_time: int=3600, wait: int=5, count: int=5) -> bool:

        for _ in range(count):
            res = self.acquire_lock(key, owner_name, lease_time)
            if res:
                return
            time.sleep(wait)
        return False


    def release_lock(self, key, owner_name='unknown'):
        """
        Release a lock.

        Args:
            key (str):        The key representing the log
            owner_name (str): Owner associated with the lock.
        """

        try:
            lock = DynamoLock.get(key)
            if lock.owner_name != owner_name:
                log.debug(f"found lock: {lock.key} owned by {lock.owner_name}")
                raise LockNotGrantedError()
            lock.delete()
            log.debug(f"Lock {key} released")

        # if it doesn't exist, just do nothing
        except DoesNotExist:
            return
