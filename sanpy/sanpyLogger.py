# 20210525
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

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

from platformdirs import user_log_dir


_LOG_BACKUP_COUNT = 1


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


def getLoggerText() -> str:
    """Return all retained SanPy log text in chronological order.

    The rotating file handler retains numbered backups alongside the active
    log. Missing files are ignored because a new installation may not have
    written or rotated its log yet.

    Returns:
        Contents of the retained log files, or a diagnostic when none can be
        read.
    """
    log_path = Path(getLoggerFile())
    retained_paths = [
        log_path.with_name(f"{log_path.name}.{index}")
        for index in range(_LOG_BACKUP_COUNT, 0, -1)
    ]
    retained_paths.append(log_path)

    log_text = ""
    read_errors: list[str] = []
    for retained_path in retained_paths:
        try:
            text = retained_path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        except OSError as error:
            read_errors.append(f'{retained_path}: {error}')
            continue

        if log_text and not log_text.endswith("\n") and text:
            log_text += "\n"
        log_text += text

    if read_errors:
        diagnostic = "Log file unavailable: " + "; ".join(read_errors)
        if log_text and not log_text.endswith("\n"):
            log_text += "\n"
        log_text += diagnostic

    if not log_text:
        return f"Log file unavailable: no log files found for {log_path}"
    return log_text


def get_logger(name, level=logging.DEBUG):
    """ """

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
        c_handler.setLevel(level)

        # Create formatters and add it to handlers
        consoleFormat = "%(levelname)5s %(name)8s  %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s"
        c_format = logging.Formatter(consoleFormat)
        c_handler.setFormatter(c_format)
        logger.addHandler(c_handler)

        try:
            logPath = getLoggerFile()
            f_handler = RotatingFileHandler(
                logPath, maxBytes=2_000_000, backupCount=_LOG_BACKUP_COUNT
            )
        except OSError as error:
            logger.warning("File logging is unavailable: %s", error)
        else:
            f_handler.setLevel(level)
            fileFormat = "%(asctime)s  %(levelname)5s %(name)8s  %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s"
            f_handler.setFormatter(logging.Formatter(fileFormat))
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
