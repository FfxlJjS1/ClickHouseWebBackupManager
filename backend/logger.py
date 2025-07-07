import logging
import os
from sys import stdout

CONTAINER_NAME = os.environ.get('HOSTNAME') if 'HOSTNAME' in os.environ.keys() else 'usick.backend_native'
DEBUG = os.environ.get('DEBUG') == "true" if 'DEBUG' in os.environ.keys() else True

# Define logger
logger = logging.getLogger(CONTAINER_NAME)

if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

logFormatter = logging.Formatter\
("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")

consoleHandler = logging.StreamHandler(stdout) #set streamhandler to stdout
consoleHandler.setFormatter(logFormatter)

logger.addHandler(consoleHandler)
