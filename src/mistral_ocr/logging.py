"""Enhanced logging setup for Mistral OCR with audit trails and performance monitoring."""

import hashlib
import logging
import logging.handlers
import pathlib
from typing import Any, Dict

import structlog

from .constants import LOG_FILE_NAME


class AuditProcessor:
    """Custom structlog processor for audit trail formatting."""

    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Process log events to add audit trail metadata."""
        # Add audit trail marker for structured events
        if any(key in event_dict for key in ["event_type", "security", "performance"]):
            event_dict["audit_trail"] = True

        # Sanitize sensitive data
        if "api_key" in event_dict:
            if event_dict["api_key"]:
                # Hash API key for identification without exposure
                api_key_hash = hashlib.sha256(str(event_dict["api_key"]).encode()).hexdigest()[:16]
                event_dict["api_key_hash"] = api_key_hash
            del event_dict["api_key"]

        return event_dict


def setup_logging(
    log_dir: pathlib.Path,
    level: str = "INFO",
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 5,
    enable_console: bool = False,  # Changed default to False
) -> pathlib.Path:
    """Set up enhanced logging with rotation and audit capabilities.

    Args:
        log_dir: Directory where log files should be created
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        max_bytes: Maximum size per log file before rotation
        backup_count: Number of backup log files to keep
        enable_console: Whether to enable console output

    Returns:
        Path to the main log file
    """
    # Ensure the log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set up main log file with rotation
    log_file = log_dir / LOG_FILE_NAME
    log_file.touch()

    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )

    # Set up separate audit log file
    audit_log_file = log_dir / "audit.log"
    audit_log_file.touch()

    # Set up performance log file
    performance_log_file = log_dir / "performance.log"
    performance_log_file.touch()

    # Configure processors for file-only output
    file_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        AuditProcessor(),
        structlog.processors.JSONRenderer(),
    ]

    # Always use file-only processors (no console output)
    processors = file_processors

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        logger_factory=structlog.WriteLoggerFactory(file=open(log_file, "a", encoding="utf-8")),
        cache_logger_on_first_use=True,
    )

    # Set up Python logging to work with structlog (file-only)
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=[file_handler],  # Only file handler, no console output
        format="%(message)s",
    )

    return log_file


def setup_audit_logging(log_dir: pathlib.Path) -> Dict[str, pathlib.Path]:
    """Set up specialized audit logging files.

    Args:
        log_dir: Directory where audit log files should be created

    Returns:
        Dictionary mapping log types to their file paths
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    log_files = {
        "audit": log_dir / "audit.log",
        "security": log_dir / "security.log",
        "performance": log_dir / "performance.log",
        "api": log_dir / "api.log",
    }

    # Create all log files
    for log_file in log_files.values():
        log_file.touch()

    return log_files


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ or component name)

    Returns:
        Configured structlog BoundLogger instance
    """
    return structlog.get_logger(name)


def get_audit_log_path(log_dir: pathlib.Path) -> pathlib.Path:
    """Get the path to the audit log file.

    Args:
        log_dir: Directory containing log files

    Returns:
        Path to the audit log file
    """
    return log_dir / "audit.log"


def get_performance_log_path(log_dir: pathlib.Path) -> pathlib.Path:
    """Get the path to the performance log file.

    Args:
        log_dir: Directory containing log files

    Returns:
        Path to the performance log file
    """
    return log_dir / "performance.log"


def configure_log_level(level: str) -> None:
    """Dynamically change the logging level.

    Args:
        level: New logging level (DEBUG, INFO, WARNING, ERROR)
    """
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
    )
    logging.getLogger().setLevel(getattr(logging, level.upper()))
