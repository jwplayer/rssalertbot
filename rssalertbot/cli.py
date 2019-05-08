import logging
from rssalertbot.main import main
from rssalertbot      import LOG_FORMAT

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

if __name__ == '__main__':
    main()
