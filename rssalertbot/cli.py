
import argparse
import asyncio
import logging
import sys

import rssalertbot
from .config    import Config
from .feed      import Feed


logging.basicConfig(level=logging.ERROR,
                    format='%(levelname)-7s [%(module)s.%(funcName)s:%(lineno)d] %(message)s')
log = logging.getLogger()


def get_argparser():

    argparser = argparse.ArgumentParser()
    argparser.add_argument('-c', '--config', type=str, default="config.json",
                           help="config file (default: ./config.json)")
    argparser.add_argument('-t', '--feed_timeout', type=str, default=rssalertbot.FEED_TIMEOUT,
                           help=f"feed processing timeout in seconds (default: {rssalertbot.FEED_TIMEOUT})")
    argparser.add_argument('--no-notify', action='store_true',
                           help="Disable all notifications globally")

    argparser.add_argument('--dry-run', '--dry_run', action='store_true',
                           help="Simulate, don't act")
    argparser.add_argument('-v', action='count',
                           help="Verbose - repeat for increased debugging")
    argparser.add_argument('--version',  action='version',
                           version=f'%(prog)s {rssalertbot.__version__}')

    return argparser


def main():

    argparser = get_argparser()

    opts = argparser.parse_args(sys.argv[1:])

    # TODO: handle locking here - bail if there's already an instance running

    if opts.v:
        if opts.v >= 3:
            log.setLevel(logging.DEBUG)
        elif opts.v == 2:
            log.setLevel(logging.INFO)
        elif opts.v == 1:
            log.setLevel(logging.WARNING)

    # load the config
    cfg = Config()
    cfg.load(opts.config)

    if opts.feed_timeout:
        cfg.set('timeout', int(opts.feed_timeout if opts.feed_timeout else 0))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop, opts, cfg))
    loop.close()


async def run(loop, opts, cfg):
    tasks = []
    for group in cfg.get('feedgroups', []):
        for f in group['feeds']:
            feed = Feed(loop, cfg, group, f['name'], f['url'], loglevel=log.getEffectiveLevel())
            # create the async task
            tasks.append(feed.process(timeout = cfg.get('timeout'), dry_run = opts.dry_run))

    # now we wait for them to finish
    for task in tasks:
        await task


if __name__ == '__main__':
    main()
