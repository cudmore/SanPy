# 20210525
import os, sys
import logging
from logging.handlers import RotatingFileHandler
import pathlib

"""
DEBUG
INFO
WARNING
ERROR
CRITICAL
"""

def get_logger(name):
	"""
	"""
	if getattr(sys, 'frozen', False):
		# running in a bundle (frozen)
		myPath = sys._MEIPASS
	else:
		# running in a normal Python environment
		#myPath = os.path.dirname(os.path.abspath(__file__))
		myPath = pathlib.Path(__file__).parent.absolute()

	fileName = 'sanpy.log'
	logPath = os.path.join(myPath, fileName)

	# Create a custom logger
	logger = logging.getLogger(name)
	logger.propagate = False # don't propogate to root (o.w. prints twice)

	if not logger.handlers:
		# Create handlers
		c_handler = logging.StreamHandler()
		f_handler = RotatingFileHandler(logPath, maxBytes=2000, backupCount=0)
		#f_handler = logging.FileHandler(logPath)
		c_handler.setLevel(logging.NOTSET)
		f_handler.setLevel(logging.NOTSET)

		# Create formatters and add it to handlers
		consoleFormat = '%(levelname)5s %(name)8s  %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s'
		c_format = logging.Formatter(consoleFormat)

		fileFormat = '%(asctime)s  %(levelname)5s %(name)8s  %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s'
		f_format = logging.Formatter(fileFormat)

		c_handler.setFormatter(c_format)
		f_handler.setFormatter(f_format)

		# Add handlers to the logger
		logger.addHandler(c_handler)
		logger.addHandler(f_handler)

		#logger.info('Added console and file handlers')
		logger.info(f'Logging to file {logPath}')
	#
	return logger

def test():
	logger.error('111')

if __name__ == '__main__':
	logger = get_logger(__name__)
	logger.error('WORKS')

	test()

	a = 5
	b = 0
	try:
		c = a / b
	except Exception as e:
		logger.exception("Exception occurred")
