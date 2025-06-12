import logging
import sys

class AnsiColorFormatter(logging.Formatter):
    COLOR_CODES = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[1;31m" # Bold Red
    }
    RESET_CODE = "\033[0m"

    def format(self, record):
        color = self.COLOR_CODES.get(record.levelno, self.RESET_CODE)
        message = super().format(record)
        return f"{color}{message}{self.RESET_CODE}"



def get_flasknova_logger() -> logging.Logger:
    logger = logging.getLogger("flasknova")

    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    formatter = AnsiColorFormatter(
        "[FLASKNOVA] %(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger
