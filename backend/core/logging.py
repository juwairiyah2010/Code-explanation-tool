"""Application logging configuration."""

import logging
import sys
from backend.config import get_settings

settings = get_settings()


def setup_logging() -> logging.Logger:
    """Configure and return root logger for the application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("code_explainer")


logger = setup_logging()
