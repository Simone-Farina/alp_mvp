from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog

LOG_LEVEL = os.getenv("ALP_LOG_LEVEL", "INFO").upper()
LOG_JSON = os.getenv("ALP_LOG_JSON", "1") not in ("0", "false", "False")
SERVICE_NAME = os.getenv("ALP_SERVICE_NAME", "alp-app")


def _add_service(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict["service"] = SERVICE_NAME
    return event_dict


def configure_logging() -> None:
    """Configure stdlib + structlog once at process start."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors = [
        timestamper,
        _add_service,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if LOG_JSON:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            *shared_processors,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, LOG_LEVEL, logging.INFO)),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # stdlib logging -> structlog
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str | None = None):
    return structlog.get_logger(name or SERVICE_NAME)
