import logging
import pendulum

from pynamodb.attributes import (UnicodeAttribute, UTCDateTimeAttribute)
from pynamodb.exceptions import DoesNotExist
from pynamodb.models     import Model

from . import BaseLocker, Lock, LockAccessDenied

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
    """
    Use DynamoDB for locking.
    """

    def __init__(self, table=None, url=None, region='us-east-1'):

        DynamoLock.region = region
#        if url:
#            log.warning(f"Using DynamoDB url: {url}")
#        if table:
#            log.warning(f"Using DynamoDB table: {table}")

        DynamoLock.create_table()


    def acquire_lock(self, key, owner_name: str='unknown', lease_time: int=3600) -> Lock:

        try:
            old = DynamoLock.get(key)
            # If the lock is not yet expired, and you aren't the owner, you can't have it
            if (pendulum.now('UTC') < old.expires) and old.owner_name != owner_name:
                log.debug(f"Lock {key} denied")
                raise LockAccessDenied()

            # delete the old lock
            old.delete()

        except DoesNotExist:
            pass

        # create the new lock
        rec = DynamoLock(
            key         = key,
            expires     = pendulum.now('UTC').add(seconds = lease_time),
            owner_name  = owner_name,
        )
        rec.save()
        log.debug(f"Lock {rec.key} acquired, expires {rec.expires}")

        def release():
            self.release_lock(key, owner_name)

        # return lock
        return Lock(release, expires=rec.expires)


    def release_lock(self, key, owner_name='unknown'):

        try:
            lock = DynamoLock.get(key)
            if lock.owner_name != owner_name:
                log.debug(f"found lock: {lock.key} owned by {lock.owner_name}")
                raise LockAccessDenied()
            lock.delete()
            log.debug(f"Lock {key} released")

        # if it doesn't exist, just do nothing
        except DoesNotExist:
            return
