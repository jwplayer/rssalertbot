import argparse
import asyncio
import logging

import rssalertbot
from .config    import Config
from .feed      import Feed
from .locking   import LockError


log = logging.getLogger(__name__)


def get_argparser():

    argparser = argparse.ArgumentParser()
    argparser.add_argument('-c', '--config', action='append', default=["config.yaml"],
                           help="config file (default: ./config.json)")
    argparser.add_argument('-t', '--feed_timeout', type=str, default=rssalertbot.FEED_TIMEOUT,
                           help=f"feed processing timeout in seconds (default: {rssalertbot.FEED_TIMEOUT})")
    argparser.add_argument('--no-notify', action='store_true',
                           help="Disable all notifications globally")

    argparser.add_argument('-v', action='count',
                           help="Verbose - repeat for increased debugging")
    argparser.add_argument('--version',  action='version',
                           version=f'%(prog)s {rssalertbot.__version__}')

    return argparser


def setup_storage(config):

    if 'file' in config:
        log.info("Using local files for storage")
        from .storage.file import FileStorage
        return FileStorage(path = config.get('file.path'))

    if 'dynamodb' in config:
        log.info("Using DynamoDB for storage")
        from .storage.dynamo import DynamoStorage
        return DynamoStorage(
            url    = config.get('dynamodb.url'),
            table  = config.get('dynamodb.table'),
            region = config.get('dynamodb.region', 'us-east-1'),
        )

    log.info("Defaulting to local files for storage")
    from .storage.file import FileStorage
    return FileStorage()


def setup_locking(config):
    if 'file' in config:
        log.info("Using local files for locking")
        from .locking.file import FileLocker
        return FileLocker(path = config.get('file.path'))

    if 'dynamodb' in config:
        log.info("Using DynamoDB for locking")
        from .locking.dynamo import DynamoLocker
        return DynamoLocker(
            url    = config.get('dynamodb.url'),
            table  = config.get('dynamodb.table'),
            region = config.get('dynamodb.region', 'us-east-1'),
        )

    log.info("Defaulting to local files for locking")
    from .locking.file import FileLocker
    return FileLocker()


def main():

    argparser = get_argparser()
    opts = argparser.parse_args()

    # Some third-party libraries are very verbose with logging, but we don't need that.
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('pynamodb').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('chardet').setLevel(logging.WARNING)

    # load the config
    cfg = Config()
    for cfgfile in opts.config:
        cfg.load(cfgfile)
    if cfg.get('loglevel'):
        log.setLevel(logging.getLevelName(cfg.get('loglevel')))

    # override log level if specified on command-line
    if opts.v:
        if opts.v >= 3:
            log.setLevel(logging.DEBUG)
        elif opts.v == 2:
            log.setLevel(logging.INFO)
        elif opts.v == 1:
            log.setLevel(logging.WARNING)

    # set some global options
    if opts.feed_timeout:
        cfg.set('timeout', int(opts.feed_timeout if opts.feed_timeout else 0))
    if opts.no_notify:
        cfg.set('no_notify', False)

    # startup our event loop and run stuff
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop, opts, cfg))
    loop.close()


async def run(loop, opts, cfg):

    storage = setup_storage(cfg.get('storage', {}))
    locker = setup_locking(cfg.get('locking', {}))

    tasks = []
    for group in cfg.get('feedgroups', []):
        for f in group['feeds']:
            feed = Feed(
                loop     = loop,
                cfg      = cfg,
                storage  = storage,
                group    = group,
                name     = f['name'],
                url      = f['url'])

            # create the async task
            tasks.append(feed.process(timeout = cfg.get('timeout')))

    try:
        lock = locker.acquire_lock('rssalertbot-main', 'rssalertbot')
    except LockError:
        log.warning("Lock not acquired, skipping this run.")
        return

    # now we wait for them to finish
    try:
        for task in tasks:
            await task
    finally:
        lock.release()
