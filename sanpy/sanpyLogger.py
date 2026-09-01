# 20210525
import os
import sys
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

"""
LOGLEVEL = os.environ.get('LOGLEVEL', 'WARNING').upper()
print('LOGLEVEL:', LOGLEVEL)
print('os.environ')
for k,v in os.environ.items():
    print(f'  {k}: {v}')
sys.exit(1)
"""

# basedir = os.path.dirname(__file__)
# print('sanpyLogger basedir:', basedir)

# from sanpy._util import _getUserPreferencesFolder

from platformdirs import user_log_dir


def getLoggerFile():
    """Get the path to save the log file.

    macOS: ~/Library/Logs/SanPy/sanpy.log
    Windows: %LOCALAPPDATA%/SanPy/Logs/sanpy.log
    """
    # 202609 - upgrade to packaging
    # Frozen apps must not write into the .app / .exe, or SanPy-User-Files
    # (first-run copytree). platformdirs, not a hand-rolled path table.
    log_dir = user_log_dir("SanPy", appauthor=False, ensure_exists=True)
    return os.path.join(log_dir, "sanpy.log")


def get_logger(name, level=logging.DEBUG):
    """ """

    # if getattr(sys, 'frozen', False):
    #     # running in a bundle (frozen)
    #     myPath = sys._MEIPASS
    # else:
    #     # running in a normal Python environment
    #     myPath = pathlib.Path(__file__).parent.absolute()

    # fileName = 'sanpy.log'
    # logPath = os.path.join(myPath, fileName)

    logPath = getLoggerFile()

    # print('logPath:', logPath)

    # Create a custom logger
    logger = logging.getLogger(name)
    logger.setLevel(level)  # abb 20220609

    # abb removed 20220609
    logger.propagate = False  # don't propogate to root (o.w. prints twice)
    # print('   ', logger, 'level:', level)
    if not logger.handlers:
        # print('=== sanpyLogger.get_logger() creating handlers')
        # print('    ', logger.handlers)

        # Create handlers
        c_handler = logging.StreamHandler()
        f_handler = RotatingFileHandler(logPath, maxBytes=2e6, backupCount=1)
        # f_handler = logging.FileHandler(logPath)

        c_handler.setLevel(level)
        f_handler.setLevel(level)

        # Create formatters and add it to handlers
        consoleFormat = "%(levelname)5s %(name)8s  %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s"
        c_format = logging.Formatter(consoleFormat)

        fileFormat = "%(asctime)s  %(levelname)5s %(name)8s  %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s"
        f_format = logging.Formatter(fileFormat)

        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        # Add handlers to the logger
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)
    #
    #
    return logger


# see: https://stackoverflow.com/questions/6234405/logging-uncaught-exceptions-in-python
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception

# This does not seem like a good idea, without it, we get exception calling
# logger.error in handle_exception (above)
logger = get_logger(__name__)


def test():
    logger.error("111")


if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.error("WORKS")

    test()

    # print(1/0)

    """
    a = 5
    b = 0
    try:
        c = a / b
    except Exception as e:
        logger.exception("Exception occurred")
    """
