import pendulum
from abc import ABC, abstractmethod


class BaseStorage(ABC):
    """
    Base class for storing state.
    """


    def _event_name(self, feed, event_id):
        return '-'.join((feed, event_id))


    @abstractmethod
    def last_update(self, feed) -> pendulum.DateTime:
        """
        Get the last updated date for the given feed
        """
        pass


    @abstractmethod
    def save_date(self, feed, date: pendulum.DateTime):
        """
        Save the last updated date for the given feed
        """
        pass


    @abstractmethod
    def load_event(self, feed, event_id):
        """
        Load the last sent date for an event
        """
        pass


    @abstractmethod
    def save_event(self, feed, event_id, date: pendulum.DateTime):
        """
        Save the last sent date for an event
        """
        pass


    @abstractmethod
    def delete_event(self, feed, event_id):
        """
        Delete an event
        """
        pass
