"""Logging and tracing setup for the AI service."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from src.config import config


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_FILE_PATH = "logs/service.log"


def setup_logging(*, debug: bool = False) -> None:
    """Configure Python logging.

    - Console output at INFO+ (or DEBUG+ when debug=True) for operational logs.
    - Rotating file output at DEBUG+ for deep diagnostics.
    - Consistent structured format for easier log parsing.
    """

    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE_PATH, maxBytes=2_000_000, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Avoid duplicate handlers when reloading in dev.
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def setup_langsmith() -> None:
    """Initialize LangSmith tracing if enabled.

    Tracing is optional and only activated when the API key is present and
    LANGSMITH_ENABLED is true. This minimizes overhead in environments that
    do not require observability.
    """

    if not config.LANGSMITH_ENABLED or not config.LANGSMITH_API_KEY:
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = config.LANGSMITH_API_KEY

    try:
        from langsmith import Client

        Client()
        logging.getLogger(__name__).info("LangSmith tracing enabled")
    except Exception as exc:  # pragma: no cover - optional dependency
        logging.getLogger(__name__).warning(
            "LangSmith initialization failed: %s", str(exc)
        )


logger = logging.getLogger(__name__)
