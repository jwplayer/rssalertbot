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

    def last_update(self, feed) -> pendulum.DateTime:
        """
        Get the last updated date for the given feed
        """
        try:
            obj = FeedState.get(feed)
            return obj.last_run
        except DoesNotExist:
            return pendulum.yesterday('UTC')


    def save_date(self, feed, date: pendulum.DateTime):
        """
        Save the date for the current event
        """
        try:
            obj = FeedState.get(feed)
            obj.last_run = date
            obj.save()
            log.debug(f"Saved date for '{feed}'")
        except DoesNotExist:
            obj = FeedState(name=feed, last_run=date)
            obj.save()
