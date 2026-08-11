from __future__ import annotations

from flask import request, g, Flask
import typing as t
import logging
import time
import json
import sys


def _level_handler(logger: logging.Logger) -> bool:
    level: int = logger.getEffectiveLevel()
    current = logger

    while current:
        if any(handler.level <= level for handler in current.handlers):
            return True
        if not current.propagate:
            break
        current = current.parent  # type: ignore[assignment]
    return False


def _error_stream() -> t.TextIO:
    if request:
        return request.environ["wsgi.errors"]
    return sys.stderr


class AnsiColorJsonFormatter(logging.Formatter):
    COLOR_CODES: dict[int, str] = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[1;31m",  # Bold Red
    }
    RESET_CODE = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color: str = self.COLOR_CODES.get(record.levelno, self.RESET_CODE)

        log_data: dict[str, str] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }

        if request and hasattr(g, "trace_id"):
            log_data["trace_id"] = g.trace_id
        else:
            log_data["trace_id"] = "system-level"

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        message = json.dumps(log_data)
        return f"{color}{message}{self.RESET_CODE}"

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        ct = self.converter(record.created)
        t: str = time.strftime("%Y-%m-%dT%H:%M:%S", ct)
        return f"{t}.{int(record.msecs):03d}Z"


_handler = logging.StreamHandler(_error_stream())
_handler.setFormatter(AnsiColorJsonFormatter())


def json_logger(app: Flask) -> logging.Logger:
    """
    Structured Json Logger \n
    Configure:
    ```
    app.config["ANSI_COLOR_JSON_FORMATTER"] = True
    ```
    to get json-strutured logs
    """
    logger = logging.getLogger(app.name)

    if logger.hasHandlers():
        return logger

    if app.debug and not logger.level:
        logger.setLevel(logging.DEBUG)

    if not _level_handler(logger):
        logger.addHandler(_handler)

    return logger


def get_flasknova_logger() -> logging.Logger:
    """
    Colorful text logger for logs outside app
    ```
    logger = get_flasknova_logger()
    def home_service():
        # ...Logic
        logger.info("Home")
        return {"msg": "Welcome Home"}

    ```
    #### alternative
    set `ANSI_COLOR_JSON_FORMATTER` config to get colorful and json \n
    note: this override the app text log and gives you colorful-structured json log
    ```
    app.config["ANSI_COLOR_JSON_FORMATTER"] = True

    @app.get("/")
    def home():
        app.info("Home")
        return {"msg": "Welcome Home"}
    ```
    """
    logger = logging.getLogger("flasknova")

    if logger.hasHandlers():
        return logger
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = AnsiColorJsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
