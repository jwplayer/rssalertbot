import pendulum
from abc import ABC, abstractmethod


class BaseStorage(ABC):
    """
    Base class for storing state.
    """
    not_found_exception_class = Exception

    @abstractmethod
    def _read(self, name):
        pass


    @abstractmethod
    def _write(self, name, date):
        pass


    @abstractmethod
    def _delete(self, name):
        pass


    def _event_name(self, feed, event_id):
        return '-'.join((feed, event_id))


    def _read_or_none(self, name):
        try:
            return self._read(name)
        except self.not_found_exception_class:
            return None


    def last_update(self, feed) -> pendulum.DateTime:
        """
        Get the last updated date for the given feed
        """
        return self._read_or_none(feed)


    def save_date(self, feed, date: pendulum.DateTime):
        """
        Save the last updated date for the given feed
        """
        self._write(feed, date)


    def load_event(self, feed, event_id):
        """
        Load the last sent date for an event
        """
        return self._read_or_none(self._event_name(feed, event_id))


    def save_event(self, feed, event_id, date: pendulum.DateTime):
        """
        Save the last sent date for an event
        """
        self._write(self._event_name(feed, event_id), date)


    def delete_event(self, feed, event_id):
        """
        Delete an event
        """
        self._delete(self._event_name(feed, event_id))
