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
    not_found_exception_class = DoesNotExist

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


    def _delete(self, name):
        obj = FeedState.get(name)
        obj.delete()
