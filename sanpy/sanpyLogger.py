# 20210525
import os
import sys
import logging
import logging.handlers

from platformdirs import user_data_dir

"""
DEBUG
INFO
WARNING
ERROR
CRITICAL
"""

def getLoggerFile() -> str:
    """Get the path to save the log file.
    """

    APP_NAME = "SanPy"
    APP_AUTHOR = "SanPyTeam"

    log_dir = user_data_dir(appname=APP_NAME, appauthor=APP_AUTHOR)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "sanpy.log")

    return log_file

    # userPath = pathlib.Path.home()
    # userPreferencesFolder = os.path.join(userPath, "Documents", "SanPy-User-Files", "preferences")
        
    # # print(f'202507 kym looking for userPreferencesFolder: {userPreferencesFolder}')
    # if os.path.isdir(userPreferencesFolder):
    #     # print('  userPreferencesFolder exists')
    #     myPath = userPreferencesFolder
    #     # print('  my path 1:', myPath)
    # elif getattr(sys, "frozen", False):
    #     # 201507 was this
    #     # running in a bundle (frozen)
    #     if 0:
    #         # print('  elif frozen')
    #         myPath = sys._MEIPASS
    #         # print('  my path 2:', myPath)
    #     # now this
    #     myPath = userPreferencesFolder

    # else:
    #     # running in a normal Python environment
    #     # myPath = os.path.dirname(os.path.abspath(__file__))
    #     # print('  else clause')
    #     myPath = pathlib.Path(__file__).parent.absolute()
    #     # print('  my path 3:', myPath)

    # # print(f'202507 kym myPath: {myPath}')

    # fileName = "sanpy.log"
    # logPath = os.path.join(myPath, fileName)
    # # print(f'202507 kym logPath:{logPath}')
    # return logPath


def get_logger(name, level=logging.DEBUG):
    """ """


    logPath = getLoggerFile()

    # Create a custom logger
    logger = logging.getLogger(name)
    logger.setLevel(level)  # abb 20220609
    logger.propagate = False  # don't propogate to root (o.w. prints twice)

    if not logger.handlers:

        # Create handlers
        c_handler = logging.StreamHandler()
        f_handler = logging.handlers.RotatingFileHandler(logPath, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')

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


# abb 202507 removed
# see: https://stackoverflow.com/questions/6234405/logging-uncaught-exceptions-in-python
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


# abb 202507 removed
sys.excepthook = handle_exception

# This does not seem like a good idea, without it, we get exception calling
# logger.error in handle_exception (above)
# abb 201507 removed
logger = get_logger(__name__)

