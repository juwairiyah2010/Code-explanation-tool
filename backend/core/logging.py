"""Application logging configuration supporting human-readable text and production JSON structured logging."""

from datetime import datetime, timezone
import json
import logging
import sys
from backend.config import get_settings


class JSONFormatter(logging.Formatter):
    """Format log records as structured single-line JSON objects for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_obj.update(record.extra_fields)
        return json.dumps(log_obj)


def setup_logging() -> logging.Logger:
    """Configure and return root logger for the application based on environment settings."""
    settings = get_settings()

    level_name = getattr(settings, "LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers on re-invocations
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    log_format = getattr(settings, "LOG_FORMAT", "text").lower()
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        text_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        handler.setFormatter(logging.Formatter(text_fmt))

    root_logger.addHandler(handler)
    return logging.getLogger("code_explainer")


logger = setup_logging()
