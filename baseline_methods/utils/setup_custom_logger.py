import logging
import sys
import datetime
import logging
import os
import logaugment
import time 

def round_timedelta_to_closest_second(delta: datetime.timedelta):
    if delta.microseconds >= 500_000:
        delta += datetime.timedelta(seconds = 1) # round up
    return delta - datetime.timedelta(microseconds = delta.microseconds)

def process_record(record):
  # https://stackoverflow.com/questions/31521859/python-logging-module-time-since-last-log
  now = datetime.datetime.utcnow()
  try:
      delta = now - process_record.now
  except AttributeError: # no previous log -> add delta = 0s 
      delta = (datetime.datetime.utcnow() - datetime.datetime.utcnow()) # 0s in a formatted way
  process_record.now = now
  return {'time_since_last': round_timedelta_to_closest_second(delta)}

def setup_custom_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s, dT: %(time_since_last)s | %(levelname)-6s | %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    
    path = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(path):
      os.makedirs(path)
    
    handler = logging.FileHandler(os.path.join(path, f"{name}_log.txt"), mode='w')
    handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.addHandler(screen_handler)
    logaugment.add(logger, process_record)
    return logger

if __name__ == '__main__':
  
  logger = setup_custom_logger('tester')
  logger.info('Start')
  time.sleep(3)
  logger.debug('Deb')
  time.sleep(5)
  logger.error('T')
  print('End')
  
