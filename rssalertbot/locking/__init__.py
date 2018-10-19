"""
Locking base classes.
"""

import time
from abc import ABC, abstractmethod


class LockError(Exception):
    """Base class for all locking exceptions"""
    pass


class LockAccessDenied(LockError):
    """Access to the lock was denied"""
    pass


class LockNotAcquired(LockError):
    """Raised when the lock acquisition attempt times out."""
    pass


class Lock:
    """
    A lock.

    Call ``Lock.release()`` to release.
    """

    def __init__(self, release, expires=None):
        if not callable(release):
            raise TypeError("'release' must be a callable function")

        self.release = release
        self.expires = expires


class BaseLocker(ABC):
    """
    Abstract base class from which to implement lockers.
    """

    @abstractmethod
    def acquire_lock(self, key: str, data: str, owner_name: str='unknown', lease_time: int=3600) -> bool:
        """
        Acquire a lock.

        Args:
            key (str):        The key representing the log
            owner_name (str): Owner associated with the lock.
            lease_time (int): Length of lock, in seconds

        Return:
            Lock: a lock, call :meth:`release` to release
        """
        pass


    def acquire_lock_wait(self, key, owner_name: str='unknown', lease_time: int=3600, wait: int=5, count: int=1) -> Lock:
        """
        Attempt to acquire a lock, but wait if it's not available.

        Args:
            wait (int): how much time to wait
            count (int): how many times to attempt

        Raises:
            LockNotAcquired: time + tries elapsed
        """

        for _ in range(count):
            res = self.acquire_lock(key, owner_name, lease_time)
            if res:
                return
            time.sleep(wait)

        raise LockNotAcquired("timed out")


    @abstractmethod
    def release_lock(self, key: str, owner_name: str='unknown'):
        """
        Release a lock.

        Args:
            key (str):        The key representing the log
            owner_name (str): Owner associated with the lock.
        """
        pass

