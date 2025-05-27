"""Logging setup for Mistral OCR."""

import logging
import pathlib
import sys

import structlog


def setup_logging(log_dir: pathlib.Path) -> pathlib.Path:
    """Set up structlog and return the log file path.

    Args:
        log_dir: Directory where log file should be created

    Returns:
        Path to the created log file
    """
    # Ensure the log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "mistral.log"

    # Create the log file
    log_file.touch()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if sys.stderr.isatty()
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.WriteLoggerFactory(file=open(log_file, "a")),
        cache_logger_on_first_use=True,
    )

    return log_file


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog BoundLogger instance
    """
    return structlog.get_logger(name)
