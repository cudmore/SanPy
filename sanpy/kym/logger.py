import logging
import logging.handlers
import os
from pathlib import Path

def setup_logger(name: str = None) -> logging.Logger:
    """
    Set up a logger with both console and file handlers.
    
    Parameters
    ----------
    name : str, optional
        Logger name. If None, uses the calling module's name.
    
    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    # Get the logger name from the calling module if not provided
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Set the base logging level
    logger.setLevel(logging.DEBUG)
    
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent.parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # File handler with rotation (1MB max size, keep 5 backup files)
    log_file = logs_dir / 'kym.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=1024*1024,  # 1MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatters
    # File formatter: detailed with date/time, filename, function, line
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console formatter: simpler without date/time
    console_formatter = logging.Formatter(
        '%(levelname)s - %(name)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Set formatters
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance. Creates one if it doesn't exist.
    
    Parameters
    ----------
    name : str, optional
        Logger name. If None, uses the calling module's name.
    
    Returns
    -------
    logging.Logger
        Logger instance
    """
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    logger = logging.getLogger(name)
    
    # If logger doesn't have handlers, set it up
    if not logger.handlers:
        logger = setup_logger(name)
    
    return logger 