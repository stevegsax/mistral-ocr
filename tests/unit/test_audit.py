"""Comprehensive tests for the audit trail and logging system."""

import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mistral_ocr.audit import (
    AuditEventType,
    AuditLogger,
    PerformanceLogger,
    SecurityLogger,
    get_audit_logger,
    get_performance_logger,
    get_security_logger,
)


class TestAuditEventType:
    """Test the AuditEventType enum."""

    def test_all_event_types_defined(self):
        """Test that all expected event types are defined."""
        expected_types = {
            "cli_command",
            "config_change",
            "file_submission",
            "file_discovery",
            "file_download",
            "file_access",
            "api_request",
            "api_response",
            "batch_submission",
            "job_operation",
            "application_start",
            "application_end",
            "authentication",
            "error_recovery",
            "database_operation",
            "data_processing",
            "result_retrieval",
        }

        actual_types = {event.value for event in AuditEventType}
        assert actual_types == expected_types

    def test_event_type_values_are_strings(self):
        """Test that all event type values are strings."""
        for event_type in AuditEventType:
            assert isinstance(event_type.value, str)
            assert event_type.value  # Not empty


class TestAuditLogger:
    """Test the AuditLogger class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def audit_logger(self, mock_logger):
        """Create an AuditLogger with mocked dependencies."""
        with patch("mistral_ocr.audit.get_logger", return_value=mock_logger):
            logger = AuditLogger("test_component")
            logger.logger = mock_logger
            return logger

    def test_audit_logger_initialization(self, audit_logger):
        """Test AuditLogger initialization."""
        assert audit_logger.component == "test_component"
        assert len(audit_logger._session_id) == 8
        # Session ID should be UUID format (hex characters)
        assert all(c in "0123456789abcdef" for c in audit_logger._session_id)

    def test_session_id_uniqueness(self):
        """Test that each AuditLogger gets a unique session ID."""
        with patch("mistral_ocr.audit.get_logger"):
            logger1 = AuditLogger("component1")
            logger2 = AuditLogger("component2")
            assert logger1._session_id != logger2._session_id

    def test_audit_basic_event(self, audit_logger, mock_logger):
        """Test basic audit event logging."""
        audit_logger.audit(AuditEventType.CLI_COMMAND, "Test message", operation="test_operation")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        # Check message
        assert call_args[0][0] == "Test message"

        # Check structured data
        kwargs = call_args[1]
        assert kwargs["event_type"] == "cli_command"
        assert kwargs["component"] == "test_component"
        assert kwargs["session_id"] == audit_logger._session_id
        assert kwargs["operation"] == "test_operation"
        assert kwargs["outcome"] == "success"  # Default
        assert "timestamp" in kwargs
        assert "details" in kwargs

    def test_audit_with_all_parameters(self, audit_logger, mock_logger):
        """Test audit logging with all parameters."""
        details = {"key": "value", "count": 42}

        audit_logger.audit(
            AuditEventType.AUTHENTICATION,
            "Authentication event",
            level="warning",
            user_id="user123",
            resource_id="resource456",
            operation="login_attempt",
            outcome="failure",
            details=details,
            extra_field="extra_value",
        )

        call_args = mock_logger.warning.call_args
        kwargs = call_args[1]

        assert kwargs["event_type"] == "authentication"
        assert kwargs["user_id"] == "user123"
        assert kwargs["resource_id"] == "resource456"
        assert kwargs["operation"] == "login_attempt"
        assert kwargs["outcome"] == "failure"
        assert kwargs["details"] == details
        assert kwargs["extra_field"] == "extra_value"

    def test_audit_removes_none_values(self, audit_logger, mock_logger):
        """Test that None values are removed from audit data."""
        audit_logger.audit(
            AuditEventType.DATA_PROCESSING,
            "Processing event",
            user_id=None,
            resource_id="resource123",
            operation=None,
        )

        call_args = mock_logger.info.call_args
        kwargs = call_args[1]

        assert "user_id" not in kwargs
        assert "operation" not in kwargs
        assert kwargs["resource_id"] == "resource123"

    def test_audit_timestamp_format(self, audit_logger, mock_logger):
        """Test that timestamp is in ISO format."""
        audit_logger.audit(AuditEventType.APPLICATION_START, "Start event")

        call_args = mock_logger.info.call_args
        timestamp = call_args[1]["timestamp"]

        # Should be parseable as ISO format
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert isinstance(parsed, datetime)

    def test_info_logging(self, audit_logger, mock_logger):
        """Test info level logging with audit context."""
        audit_logger.info("Info message", extra_data="value")

        mock_logger.info.assert_called_once_with(
            "Info message",
            component="test_component",
            session_id=audit_logger._session_id,
            extra_data="value",
        )

    def test_debug_logging(self, audit_logger, mock_logger):
        """Test debug level logging with audit context."""
        audit_logger.debug("Debug message", debug_info=True)

        mock_logger.debug.assert_called_once_with(
            "Debug message",
            component="test_component",
            session_id=audit_logger._session_id,
            debug_info=True,
        )

    def test_warning_logging(self, audit_logger, mock_logger):
        """Test warning level logging with audit context."""
        audit_logger.warning("Warning message", warning_code=123)

        mock_logger.warning.assert_called_once_with(
            "Warning message",
            component="test_component",
            session_id=audit_logger._session_id,
            warning_code=123,
        )

    def test_error_logging(self, audit_logger, mock_logger):
        """Test error level logging with audit context."""
        audit_logger.error("Error message", error_code=500)

        mock_logger.error.assert_called_once_with(
            "Error message",
            component="test_component",
            session_id=audit_logger._session_id,
            error_code=500,
        )

    def test_operation_context_success(self, audit_logger, mock_logger):
        """Test operation context manager for successful operations."""
        with audit_logger.operation_context(
            "test_operation",
            AuditEventType.DATA_PROCESSING,
            resource_id="resource123",
            batch_size=100,
        ) as context:
            # Simulate work
            time.sleep(0.01)
            assert "operation_id" in context
            assert len(context["operation_id"]) == 8

        # Should have two calls: start and completion
        assert mock_logger.info.call_count == 2

        # Check start call
        start_call = mock_logger.info.call_args_list[0]
        assert "Starting test_operation" in start_call[0][0]
        start_kwargs = start_call[1]
        assert start_kwargs["event_type"] == "data_processing"
        assert start_kwargs["operation"] == "test_operation"
        assert start_kwargs["resource_id"] == "resource123"
        assert start_kwargs["batch_size"] == 100

        # Check completion call
        completion_call = mock_logger.info.call_args_list[1]
        assert "Completed test_operation" in completion_call[0][0]
        completion_kwargs = completion_call[1]
        assert completion_kwargs["outcome"] == "success"
        assert "duration_seconds" in completion_kwargs
        assert completion_kwargs["duration_seconds"] > 0

    def test_operation_context_failure(self, audit_logger, mock_logger):
        """Test operation context manager for failed operations."""
        test_exception = ValueError("Test error")

        with pytest.raises(ValueError):
            with audit_logger.operation_context(
                "failing_operation", AuditEventType.API_REQUEST, resource_id="resource456"
            ):
                raise test_exception

        # Should have two calls: start and failure
        assert mock_logger.info.call_count == 1  # Start
        assert mock_logger.error.call_count == 1  # Failure

        # Check failure call
        failure_call = mock_logger.error.call_args
        assert "Failed failing_operation: Test error" in failure_call[0][0]
        failure_kwargs = failure_call[1]
        assert failure_kwargs["outcome"] == "failure"
        assert failure_kwargs["error_type"] == "ValueError"
        assert failure_kwargs["error_message"] == "Test error"
        assert "duration_seconds" in failure_kwargs


class TestPerformanceLogger:
    """Test the PerformanceLogger class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def perf_logger(self, mock_logger):
        """Create a PerformanceLogger with mocked dependencies."""
        with patch("mistral_ocr.audit.get_logger", return_value=mock_logger):
            logger = PerformanceLogger("test_component")
            logger.logger = mock_logger
            return logger

    def test_performance_logger_initialization(self, perf_logger):
        """Test PerformanceLogger initialization."""
        assert perf_logger.component == "test_component"

    def test_timing_basic(self, perf_logger, mock_logger):
        """Test basic timing information logging."""
        perf_logger.timing("test_operation", 2.5)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        assert call_args[0][0] == "Performance: test_operation"
        kwargs = call_args[1]
        assert kwargs["performance"] is True
        assert kwargs["component"] == "test_component"
        assert kwargs["operation"] == "test_operation"
        assert kwargs["duration_seconds"] == 2.5

    def test_timing_with_metrics(self, perf_logger, mock_logger):
        """Test timing with comprehensive metrics."""
        perf_logger.timing(
            "batch_processing",
            15.75,
            resource_count=100,
            resource_size=1024 * 1024 * 50,  # 50MB
            throughput=6.67,
            memory_usage=128.5,
            cpu_percent=85.2,
        )

        call_args = mock_logger.info.call_args
        kwargs = call_args[1]

        assert kwargs["duration_seconds"] == 15.75
        assert kwargs["resource_count"] == 100
        assert kwargs["resource_size_bytes"] == 50 * 1024 * 1024
        assert kwargs["throughput_items_per_second"] == 6.67
        assert kwargs["memory_usage"] == 128.5
        assert kwargs["cpu_percent"] == 85.2

    def test_timing_removes_none_values(self, perf_logger, mock_logger):
        """Test that None values are removed from performance data."""
        perf_logger.timing(
            "operation", 1.0, resource_count=None, resource_size=1024, throughput=None
        )

        call_args = mock_logger.info.call_args
        kwargs = call_args[1]

        assert "resource_count" not in kwargs
        assert "throughput_items_per_second" not in kwargs
        assert kwargs["resource_size_bytes"] == 1024

    def test_resource_usage_basic(self, perf_logger, mock_logger):
        """Test basic resource usage logging."""
        perf_logger.resource_usage("file_processing")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        assert call_args[0][0] == "Resource Usage: file_processing"
        kwargs = call_args[1]
        assert kwargs["resource_usage"] is True
        assert kwargs["component"] == "test_component"
        assert kwargs["operation"] == "file_processing"

    def test_resource_usage_with_metrics(self, perf_logger, mock_logger):
        """Test resource usage with comprehensive metrics."""
        perf_logger.resource_usage(
            "api_processing",
            memory_mb=256.7,
            cpu_percent=42.3,
            disk_usage_mb=1024.0,
            network_io_mb=15.5,
            active_threads=8,
        )

        call_args = mock_logger.info.call_args
        kwargs = call_args[1]

        assert kwargs["memory_mb"] == 256.7
        assert kwargs["cpu_percent"] == 42.3
        assert kwargs["disk_usage_mb"] == 1024.0
        assert kwargs["network_io_mb"] == 15.5
        assert kwargs["active_threads"] == 8


class TestSecurityLogger:
    """Test the SecurityLogger class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def security_logger(self, mock_logger):
        """Create a SecurityLogger with mocked dependencies."""
        with patch("mistral_ocr.audit.get_logger", return_value=mock_logger):
            logger = SecurityLogger("test_component")
            logger.logger = mock_logger
            return logger

    def test_security_logger_initialization(self, security_logger):
        """Test SecurityLogger initialization."""
        assert security_logger.component == "test_component"

    def test_authentication_event_success(self, security_logger, mock_logger):
        """Test successful authentication event logging."""
        security_logger.authentication_event(
            "API key validation",
            outcome="success",
            api_key_hash="a1b2c3d4e5f6",
            validation_details={"method": "environment"},
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        assert call_args[0][0] == "Authentication: API key validation"
        kwargs = call_args[1]
        assert kwargs["security"] is True
        assert kwargs["component"] == "test_component"
        assert kwargs["authentication_event"] == "API key validation"
        assert kwargs["outcome"] == "success"
        assert kwargs["api_key_hash"] == "a1b2c3d4e5f6"
        assert kwargs["validation_details"] == {"method": "environment"}

    def test_authentication_event_failure(self, security_logger, mock_logger):
        """Test failed authentication event logging."""
        security_logger.authentication_event(
            "Invalid API key", outcome="failure", validation_details={"error": "key_not_found"}
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args

        assert call_args[0][0] == "Authentication: Invalid API key"
        kwargs = call_args[1]
        assert kwargs["outcome"] == "failure"
        assert kwargs["validation_details"] == {"error": "key_not_found"}

    def test_authentication_event_removes_none(self, security_logger, mock_logger):
        """Test that None values are removed from authentication data."""
        security_logger.authentication_event(
            "Login attempt",
            api_key_hash=None,
            validation_details={"method": "config"},
            user_context=None,
        )

        call_args = mock_logger.info.call_args
        kwargs = call_args[1]

        assert "api_key_hash" not in kwargs
        assert "user_context" not in kwargs
        assert kwargs["validation_details"] == {"method": "config"}

    def test_data_access_success(self, security_logger, mock_logger):
        """Test successful data access event logging."""
        test_path = Path("/tmp/test_file.pdf")

        security_logger.data_access(
            "file",
            "read",
            resource_path=test_path,
            file_size=1024 * 1024,  # 1MB
            outcome="success",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        assert call_args[0][0] == "Data Access: file read"
        kwargs = call_args[1]
        assert kwargs["security"] is True
        assert kwargs["data_access"] is True
        assert kwargs["resource"] == "file"
        assert kwargs["action"] == "read"
        assert kwargs["resource_path"] == str(test_path)
        assert kwargs["file_size_bytes"] == 1024 * 1024
        assert kwargs["outcome"] == "success"

    def test_data_access_failure(self, security_logger, mock_logger):
        """Test failed data access event logging."""
        security_logger.data_access("database", "write", outcome="failure", error_code=403)

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args

        assert call_args[0][0] == "Data Access: database write"
        kwargs = call_args[1]
        assert kwargs["outcome"] == "failure"
        assert kwargs["error_code"] == 403

    def test_data_access_removes_none(self, security_logger, mock_logger):
        """Test that None values are removed from data access logs."""
        security_logger.data_access(
            "api", "request", resource_path=None, file_size=None, request_id="req123"
        )

        call_args = mock_logger.info.call_args
        kwargs = call_args[1]

        assert "resource_path" not in kwargs
        assert "file_size_bytes" not in kwargs
        assert kwargs["request_id"] == "req123"


class TestAuditFactoryFunctions:
    """Test the factory functions for creating loggers."""

    def test_get_audit_logger(self):
        """Test get_audit_logger factory function."""
        with patch("mistral_ocr.audit.get_logger"):
            logger = get_audit_logger("test_component")
            assert isinstance(logger, AuditLogger)
            assert logger.component == "test_component"

    def test_get_performance_logger(self):
        """Test get_performance_logger factory function."""
        with patch("mistral_ocr.audit.get_logger"):
            logger = get_performance_logger("test_component")
            assert isinstance(logger, PerformanceLogger)
            assert logger.component == "test_component"

    def test_get_security_logger(self):
        """Test get_security_logger factory function."""
        with patch("mistral_ocr.audit.get_logger"):
            logger = get_security_logger("test_component")
            assert isinstance(logger, SecurityLogger)
            assert logger.component == "test_component"


class TestAuditIntegration:
    """Integration tests for audit system components."""

    def test_multiple_loggers_unique_sessions(self):
        """Test that multiple audit loggers have unique session IDs."""
        with patch("mistral_ocr.audit.get_logger"):
            loggers = [AuditLogger(f"component_{i}") for i in range(5)]
            session_ids = {logger._session_id for logger in loggers}
            assert len(session_ids) == 5  # All unique

    def test_audit_logger_with_real_structlog(self):
        """Test AuditLogger with actual structlog integration."""
        # This test uses real structlog but with a test logger
        from io import StringIO

        import structlog

        output = StringIO()
        structlog.configure(
            processors=[structlog.processors.JSONRenderer()],
            logger_factory=lambda name: output,  # Accept name parameter
            cache_logger_on_first_use=False,
        )

        logger = AuditLogger("integration_test")
        logger.audit(
            AuditEventType.APPLICATION_START, "Integration test message", test_data={"key": "value"}
        )

        # The output should contain JSON-formatted log data
        log_output = output.getvalue()
        assert "integration_test" in log_output
        assert "application_start" in log_output
        assert "Integration test message" in log_output

    def test_concurrent_audit_logging(self):
        """Test that audit logging works correctly with concurrent access."""
        import queue
        import threading

        results = queue.Queue()

        def log_events(component_id):
            with patch("mistral_ocr.audit.get_logger") as mock_logger:
                mock_logger.return_value = MagicMock()
                logger = AuditLogger(f"component_{component_id}")
                logger.logger = mock_logger.return_value  # Use the mocked logger
                for i in range(10):
                    logger.audit(
                        AuditEventType.DATA_PROCESSING, f"Event {i}", operation=f"operation_{i}"
                    )
                results.put((component_id, logger._session_id, logger.logger.info.call_count))

        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=log_events, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        thread_results = []
        while not results.empty():
            thread_results.append(results.get())

        assert len(thread_results) == 3

        # Each thread should have unique session ID and 10 log calls
        session_ids = {result[1] for result in thread_results}
        assert len(session_ids) == 3  # All unique

        for component_id, session_id, call_count in thread_results:
            assert call_count == 10
