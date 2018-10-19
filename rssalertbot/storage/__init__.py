import pendulum
from abc import ABC, abstractmethod


class BaseStorage(ABC):
    """
    Base class for storing state.
    """

    @abstractmethod
    def last_update(self, feed) -> pendulum.DateTime:
        """
        Get the last updated date for the given feed
        """
        pass


    @abstractmethod
    def save_date(self, feed, date: pendulum.DateTime):
        """
        Save the date for the current event
        """
        pass
