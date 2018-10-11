from abc import ABC, abstractmethod


class LockError(Exception):
    pass


class LockNotGrantedError(Exception):
    pass


class BaseLocker(ABC):

    @abstractmethod
    def acquire_lock(self, key: str, data: str, owner_name: str='unknown', lease_time: int=3600) -> bool:
        pass


    @abstractmethod
    def release_lock(self, key: str, owner_name: str='unknown'):
        pass
