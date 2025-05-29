"""Comprehensive audit trail and enhanced logging for Mistral OCR."""

import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .logging import get_logger


class AuditEventType(Enum):
    """Types of audit events tracked by the system."""

    # User Actions
    CLI_COMMAND = "cli_command"
    CONFIG_CHANGE = "config_change"

    # File Operations
    FILE_SUBMISSION = "file_submission"
    FILE_DISCOVERY = "file_discovery"
    FILE_DOWNLOAD = "file_download"
    FILE_ACCESS = "file_access"

    # API Operations
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    BATCH_SUBMISSION = "batch_submission"
    JOB_OPERATION = "job_operation"

    # System Events
    APPLICATION_START = "application_start"
    APPLICATION_END = "application_end"
    AUTHENTICATION = "authentication"
    ERROR_RECOVERY = "error_recovery"

    # Data Operations
    DATABASE_OPERATION = "database_operation"
    DATA_PROCESSING = "data_processing"
    RESULT_RETRIEVAL = "result_retrieval"


class AuditLogger:
    """Enhanced logging with audit trail capabilities."""

    def __init__(self, component: str):
        """Initialize audit logger for a specific component.

        Args:
            component: Name of the component using this logger
        """
        self.component = component
        self.logger = get_logger(component)
        self._session_id = str(uuid.uuid4())[:8]

    def audit(
        self,
        event_type: AuditEventType,
        message: str,
        *,
        level: str = "info",
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        operation: Optional[str] = None,
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Log an audit event with structured metadata.

        Args:
            event_type: Type of audit event
            message: Human-readable message
            level: Log level (debug, info, warning, error)
            user_id: Identifier for the user performing the action
            resource_id: Identifier for the resource being accessed
            operation: Specific operation being performed
            outcome: Result of the operation (success, failure, partial)
            details: Additional structured data
            **kwargs: Additional fields to include in the log
        """
        audit_data = {
            "event_type": event_type.value,
            "component": self.component,
            "session_id": self._session_id,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "resource_id": resource_id,
            "operation": operation,
            "outcome": outcome,
            "details": details or {},
            **kwargs,
        }

        # Remove None values to keep logs clean
        audit_data = {k: v for k, v in audit_data.items() if v is not None}

        log_method = getattr(self.logger, level)
        log_method(message, **audit_data)

    def info(self, message: str, **kwargs) -> None:
        """Log info level message with audit context."""
        self.logger.info(message, component=self.component, session_id=self._session_id, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug level message with audit context."""
        self.logger.debug(message, component=self.component, session_id=self._session_id, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning level message with audit context."""
        self.logger.warning(
            message, component=self.component, session_id=self._session_id, **kwargs
        )

    def error(self, message: str, **kwargs) -> None:
        """Log error level message with audit context."""
        self.logger.error(message, component=self.component, session_id=self._session_id, **kwargs)

    @contextmanager
    def operation_context(
        self,
        operation: str,
        event_type: AuditEventType = AuditEventType.DATA_PROCESSING,
        resource_id: Optional[str] = None,
        **context_data,
    ):
        """Context manager for tracking operations with timing and outcomes.

        Args:
            operation: Name of the operation being performed
            event_type: Type of audit event
            resource_id: Identifier for the resource being processed
            **context_data: Additional context data
        """
        start_time = time.time()
        operation_id = str(uuid.uuid4())[:8]

        self.audit(
            event_type,
            f"Starting {operation}",
            operation=operation,
            resource_id=resource_id,
            operation_id=operation_id,
            **context_data,
        )

        try:
            yield {"operation_id": operation_id}

            duration = time.time() - start_time
            self.audit(
                event_type,
                f"Completed {operation}",
                operation=operation,
                resource_id=resource_id,
                operation_id=operation_id,
                outcome="success",
                duration_seconds=round(duration, 3),
                **context_data,
            )

        except Exception as e:
            duration = time.time() - start_time
            self.audit(
                event_type,
                f"Failed {operation}: {str(e)}",
                level="error",
                operation=operation,
                resource_id=resource_id,
                operation_id=operation_id,
                outcome="failure",
                duration_seconds=round(duration, 3),
                error_type=type(e).__name__,
                error_message=str(e),
                **context_data,
            )
            raise


class PerformanceLogger:
    """Logger for performance metrics and system monitoring."""

    def __init__(self, component: str):
        self.component = component
        self.logger = get_logger(f"{component}.performance")

    def timing(
        self,
        operation: str,
        duration: float,
        *,
        resource_count: Optional[int] = None,
        resource_size: Optional[int] = None,
        throughput: Optional[float] = None,
        **metrics,
    ) -> None:
        """Log performance timing information.

        Args:
            operation: Name of the timed operation
            duration: Duration in seconds
            resource_count: Number of items processed
            resource_size: Size of data processed (bytes)
            throughput: Items per second
            **metrics: Additional performance metrics
        """
        perf_data = {
            "performance": True,
            "component": self.component,
            "operation": operation,
            "duration_seconds": round(duration, 3),
            "resource_count": resource_count,
            "resource_size_bytes": resource_size,
            "throughput_items_per_second": throughput,
            **metrics,
        }

        # Remove None values
        perf_data = {k: v for k, v in perf_data.items() if v is not None}

        self.logger.info(f"Performance: {operation}", **perf_data)

    def resource_usage(
        self,
        operation: str,
        *,
        memory_mb: Optional[float] = None,
        cpu_percent: Optional[float] = None,
        disk_usage_mb: Optional[float] = None,
        **resources,
    ) -> None:
        """Log resource usage information.

        Args:
            operation: Name of the operation
            memory_mb: Memory usage in MB
            cpu_percent: CPU usage percentage
            disk_usage_mb: Disk usage in MB
            **resources: Additional resource metrics
        """
        resource_data = {
            "resource_usage": True,
            "component": self.component,
            "operation": operation,
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "disk_usage_mb": disk_usage_mb,
            **resources,
        }

        # Remove None values
        resource_data = {k: v for k, v in resource_data.items() if v is not None}

        self.logger.info(f"Resource Usage: {operation}", **resource_data)


class SecurityLogger:
    """Logger for security-related events and authentication."""

    def __init__(self, component: str):
        self.component = component
        self.logger = get_logger(f"{component}.security")

    def authentication_event(
        self,
        event: str,
        outcome: str = "success",
        *,
        api_key_hash: Optional[str] = None,
        validation_details: Optional[Dict[str, Any]] = None,
        **context,
    ) -> None:
        """Log authentication-related events.

        Args:
            event: Description of the authentication event
            outcome: Result (success, failure, invalid)
            api_key_hash: Hashed version of API key for identification
            validation_details: Details about validation process
            **context: Additional context
        """
        auth_data = {
            "security": True,
            "component": self.component,
            "authentication_event": event,
            "outcome": outcome,
            "api_key_hash": api_key_hash,
            "validation_details": validation_details,
            **context,
        }

        # Remove None values
        auth_data = {k: v for k, v in auth_data.items() if v is not None}

        level = "warning" if outcome != "success" else "info"
        log_method = getattr(self.logger, level)
        log_method(f"Authentication: {event}", **auth_data)

    def data_access(
        self,
        resource: str,
        action: str,
        *,
        resource_path: Optional[Union[str, Path]] = None,
        file_size: Optional[int] = None,
        outcome: str = "success",
        **context,
    ) -> None:
        """Log data access events.

        Args:
            resource: Type of resource accessed
            action: Action performed (read, write, delete, etc.)
            resource_path: Path to the resource
            file_size: Size of file accessed
            outcome: Result of the access attempt
            **context: Additional context
        """
        access_data = {
            "security": True,
            "component": self.component,
            "data_access": True,
            "resource": resource,
            "action": action,
            "resource_path": str(resource_path) if resource_path else None,
            "file_size_bytes": file_size,
            "outcome": outcome,
            **context,
        }

        # Remove None values
        access_data = {k: v for k, v in access_data.items() if v is not None}

        level = "warning" if outcome != "success" else "info"
        log_method = getattr(self.logger, level)
        log_method(f"Data Access: {resource} {action}", **access_data)


def get_audit_logger(component: str) -> AuditLogger:
    """Get an audit logger instance for a component.

    Args:
        component: Name of the component

    Returns:
        Configured AuditLogger instance
    """
    return AuditLogger(component)


def get_performance_logger(component: str) -> PerformanceLogger:
    """Get a performance logger instance for a component.

    Args:
        component: Name of the component

    Returns:
        Configured PerformanceLogger instance
    """
    return PerformanceLogger(component)


def get_security_logger(component: str) -> SecurityLogger:
    """Get a security logger instance for a component.

    Args:
        component: Name of the component

    Returns:
        Configured SecurityLogger instance
    """
    return SecurityLogger(component)
