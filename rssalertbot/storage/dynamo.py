from pynamodb.models     import Model
from pynamodb.attributes import (BooleanAttribute, UnicodeAttribute, UTCDateTimeAttribute)


class FeedState:

    class Meta:
        table_name = 'RSSAlertbot'
        write_capacity_units = 1
        read_capacity_units = 1

    feed     = UnicodeAttribute(hash_key=True)
    last_run = UTCDateTimeAttribute()
