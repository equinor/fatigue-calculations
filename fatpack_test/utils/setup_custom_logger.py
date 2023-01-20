import logging
import sys

import datetime
import logging

class TimeFilter(logging.Filter):

    def filter(self, record):
        try:
          last = self.last
        except AttributeError:
          last = record.relativeCreated

        delta = datetime.datetime.fromtimestamp(record.relativeCreated/1000.0) - datetime.datetime.fromtimestamp(last/1000.0)

        record.relative = '{0:.2f}'.format(delta.seconds + delta.microseconds/1000000.0)

        self.last = record.relativeCreated
        return True

# https://stackoverflow.com/questions/28330317/print-timestamp-for-logging-in-python

def setup_custom_logger(name):
    # TODO add a function which also adds "time since last logging event" to easier track time between them
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.FileHandler('log.txt', mode='w')
    handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.addHandler(screen_handler)
    return logger

