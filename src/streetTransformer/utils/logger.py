import logging
import sys
from pathlib import Path

# Set a default log file
LOG_FILE = Path("logs/log.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# configure the logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout), # Console
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    ]
)

def get_logger(name: str):
    """
    Return a logger instance with the specified name.
    """
    return logging.getLogger(name)
