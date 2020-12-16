import logging
import pendulum

from pynamodb.attributes import (UnicodeAttribute, UTCDateTimeAttribute)
from pynamodb.exceptions import DoesNotExist
from pynamodb.models     import Model

from . import BaseStorage

log = logging.getLogger(__name__)


class FeedState(Model):

    class Meta:
        table_name = 'RSSAlertbotFeeds'
        write_capacity_units = 1
        read_capacity_units = 1

    name     = UnicodeAttribute(hash_key=True)
    last_run = UTCDateTimeAttribute()


class DynamoStorage(BaseStorage):
    """
    Base class for storing state.
    """
    def __init__(self, table=None, url=None, region='us-east-1'):

        self.url = url
        self.table = table
        self.region = region

#        if url:
#            log.warning(f"Using DynamoDB url: {url}")
#        if table:
#            log.warning(f"Using DynamoDB table: {table}")

        FeedState.create_table()


#    def create_table(self):
#        self.client.create_table(
#            TableName = self.table_name,
#            AttributeDefinitions = [
#                {'AttributeName': 'name',     'AttributeType': 'S'}
#                {'AttributeName': 'last_run', 'AttributeType': 'S'}
#            ],
#            KeySchema = [
#                {'AttributeName': 'name', 'KeyType': 'HASH'}
#            ],
#            ProvisionedThroughput={
#                'ReadCapacityUnits':  1,
#                'WriteCapacityUnits': 1
#            },
#        )


    def _read(self, name):
        obj = FeedState.get(name)
        return obj.last_run


    def _write(self, name, date):
        try:
            obj = FeedState.get(name)
        except DoesNotExist:
            obj = FeedState(name=name)
        obj.last_run = date
        obj.save()
        log.debug(f"Saved date for '{name}'")


    def last_update(self, feed) -> pendulum.DateTime:
        """
        Get the last updated date for the given feed
        """
        try:
            return self._read(feed)
        except DoesNotExist:
            return pendulum.yesterday('UTC')


    def save_date(self, feed, date: pendulum.DateTime):
        """
        Save the last updated date for the given feed
        """
        self._write(feed, date)


    def load_event(self, feed, event_id):
        """
        Load the last sent date for an event
        """
        try:
            return self._read(self._event_name(feed, event_id))
        except DoesNotExist:
            return None


    def save_event(self, feed, event_id, date: pendulum.DateTime):
        """
        Save the last sent date for an event
        """
        self._write(self._event_name(feed, event_id), date)


    def delete_event(self, feed, event_id):
        """
        Delete an event
        """
        obj = FeedState.get(self._event_name(feed, event_id))
        obj.delete()
