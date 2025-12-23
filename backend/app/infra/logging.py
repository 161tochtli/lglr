"""
Logging configuration using structlog.

This module provides structured logging with automatic request correlation ID injection.
Uses asgi-correlation-id for request tracking and structlog for structured output.
"""

from __future__ import annotations

import logging
import sys

import structlog
from asgi_correlation_id import correlation_id

_CONFIGURED = False


def _add_service_name(service_name: str):
    def processor(
        logger: logging.Logger,
        method_name: str,
        event_dict: dict,
    ) -> dict:
        event_dict["service"] = service_name
        return event_dict

    return processor


def add_correlation_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Add correlation_id to every log entry."""
    request_id = correlation_id.get()
    event_dict["request_id"] = request_id or "-"
    return event_dict


def configure_logging(service_name: str = "api", *, json_output: bool = False) -> None:
    """
    Configure structlog for the application.

    Args:
        service_name: Name to identify this service in logs.
        json_output: If True, output JSON (for production). If False, use pretty console output.
    """
    # Idempotency: avoid duplicating handlers/formatters in tests and reload scenarios.
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_service_name(service_name),
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_correlation_id,
    ]

    if json_output:
        # Production: JSON output
        renderer: structlog.typing.Processor = structlog.processors.JSONRenderer()
    else:
        # Development: pretty console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog formatting
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Reduce noise from third-party libraries
    for noisy_logger in ("uvicorn", "uvicorn.error", "uvicorn.access", "httpx"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger with the given name."""
    return structlog.get_logger(name)

