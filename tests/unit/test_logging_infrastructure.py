"""Comprehensive tests for the enhanced logging infrastructure."""

import hashlib
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from mistral_ocr.logging import (
    AuditProcessor,
    configure_log_level,
    get_audit_log_path,
    get_logger,
    get_performance_log_path,
    setup_audit_logging,
    setup_logging,
)


class TestAuditProcessor:
    """Test the AuditProcessor class for structured logging."""

    def test_audit_processor_initialization(self):
        """Test AuditProcessor initialization."""
        processor = AuditProcessor()
        assert processor is not None

    def test_audit_processor_adds_audit_trail_marker(self):
        """Test that AuditProcessor adds audit trail markers."""
        processor = AuditProcessor()

        # Event with audit markers
        event_dict = {"event": "Test event", "event_type": "cli_command", "component": "test"}

        result = processor(None, "info", event_dict)

        assert result["audit_trail"] is True
        assert result["event"] == "Test event"
        assert result["event_type"] == "cli_command"

    def test_audit_processor_security_marker(self):
        """Test audit trail marker for security events."""
        processor = AuditProcessor()

        event_dict = {"event": "Security event", "security": True, "component": "auth"}

        result = processor(None, "warning", event_dict)

        assert result["audit_trail"] is True
        assert result["security"] is True

    def test_audit_processor_performance_marker(self):
        """Test audit trail marker for performance events."""
        processor = AuditProcessor()

        event_dict = {
            "event": "Performance event",
            "performance": True,
            "operation": "batch_processing",
        }

        result = processor(None, "info", event_dict)

        assert result["audit_trail"] is True
        assert result["performance"] is True

    def test_audit_processor_no_audit_marker(self):
        """Test that regular events don't get audit trail marker."""
        processor = AuditProcessor()

        event_dict = {"event": "Regular event", "component": "test"}

        result = processor(None, "info", event_dict)

        assert "audit_trail" not in result
        assert result["event"] == "Regular event"

    def test_audit_processor_api_key_sanitization(self):
        """Test API key sanitization in audit processor."""
        processor = AuditProcessor()

        api_key = "sk-test-api-key-12345"
        event_dict = {"event": "API call", "api_key": api_key, "operation": "authentication"}

        result = processor(None, "info", event_dict)

        # API key should be removed
        assert "api_key" not in result

        # Should have hash instead
        assert "api_key_hash" in result
        expected_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        assert result["api_key_hash"] == expected_hash

    def test_audit_processor_empty_api_key(self):
        """Test handling of empty API key."""
        processor = AuditProcessor()

        event_dict = {"event": "API call", "api_key": "", "operation": "authentication"}

        result = processor(None, "info", event_dict)

        # Empty API key should be removed without adding hash
        assert "api_key" not in result
        assert "api_key_hash" not in result

    def test_audit_processor_none_api_key(self):
        """Test handling of None API key."""
        processor = AuditProcessor()

        event_dict = {"event": "API call", "api_key": None, "operation": "authentication"}

        result = processor(None, "info", event_dict)

        # None API key should be removed without adding hash
        assert "api_key" not in result
        assert "api_key_hash" not in result

    def test_audit_processor_preserves_other_fields(self):
        """Test that processor preserves other fields."""
        processor = AuditProcessor()

        event_dict = {
            "event": "Test event",
            "event_type": "data_processing",
            "api_key": "test-key",
            "user_id": "user123",
            "operation": "file_upload",
            "duration": 2.5,
            "file_count": 10,
        }

        result = processor(None, "info", event_dict)

        # All fields except api_key should be preserved
        assert result["event"] == "Test event"
        assert result["event_type"] == "data_processing"
        assert result["user_id"] == "user123"
        assert result["operation"] == "file_upload"
        assert result["duration"] == 2.5
        assert result["file_count"] == 10
        assert result["audit_trail"] is True
        assert "api_key_hash" in result


class TestSetupLogging:
    """Test the setup_logging function."""

    def test_setup_logging_creates_log_directory(self):
        """Test that setup_logging creates the log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"
            assert not log_dir.exists()

            setup_logging(log_dir)

            assert log_dir.exists()
            assert log_dir.is_dir()

    def test_setup_logging_creates_log_files(self):
        """Test that setup_logging creates required log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            setup_logging(log_dir)

            # Main log file should be created
            main_log = log_dir / "mistral.log"
            assert main_log.exists()

            # Audit log file should be created
            audit_log = log_dir / "audit.log"
            assert audit_log.exists()

            # Performance log file should be created
            perf_log = log_dir / "performance.log"
            assert perf_log.exists()

    def test_setup_logging_returns_main_log_path(self):
        """Test that setup_logging returns the main log file path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            result = setup_logging(log_dir)

            expected_path = log_dir / "mistral.log"
            assert result == expected_path

    def test_setup_logging_with_custom_level(self):
        """Test setup_logging with custom log level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"
            
            # Clear all existing handlers to test logging configuration from scratch
            root_logger = logging.getLogger()
            original_level = root_logger.level
            original_handlers = root_logger.handlers[:]
            root_logger.handlers.clear()
            
            try:
                setup_logging(log_dir, level="DEBUG")
                
                # Should configure logging at DEBUG level
                assert root_logger.level == logging.DEBUG
            finally:
                # Restore original state
                root_logger.setLevel(original_level)
                root_logger.handlers[:] = original_handlers

    def test_setup_logging_with_custom_rotation_settings(self):
        """Test setup_logging with custom rotation settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            max_bytes = 10 * 1024 * 1024  # 10MB
            backup_count = 3

            setup_logging(log_dir, max_bytes=max_bytes, backup_count=backup_count)

            # Log files should be created
            main_log = log_dir / "mistral.log"
            assert main_log.exists()

    def test_setup_logging_console_enabled(self):
        """Test setup_logging ignores console parameter (file-only by design)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            with patch("mistral_ocr.logging.logging.basicConfig") as mock_config:
                setup_logging(log_dir, enable_console=True)
                
                # Even with console=True, should only configure file handler
                mock_config.assert_called_once()
                call_kwargs = mock_config.call_args[1]
                assert len(call_kwargs['handlers']) == 1  # File only (design choice)

    def test_setup_logging_console_disabled(self):
        """Test setup_logging with console output disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            with patch("mistral_ocr.logging.logging.basicConfig") as mock_config:
                setup_logging(log_dir, enable_console=False)

                # Should only configure file handler
                mock_config.assert_called_once()
                call_kwargs = mock_config.call_args[1]
                assert len(call_kwargs["handlers"]) == 1  # File only

    @patch("mistral_ocr.logging.structlog.configure")
    def test_setup_logging_configures_structlog(self, mock_configure):
        """Test that setup_logging configures structlog."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            setup_logging(log_dir)

            # Should configure structlog
            mock_configure.assert_called_once()
            call_kwargs = mock_configure.call_args[1]
            assert "processors" in call_kwargs
            assert "wrapper_class" in call_kwargs
            assert "logger_factory" in call_kwargs

    @patch('sys.stderr.isatty', return_value=True)
    @patch('mistral_ocr.logging.structlog.configure')
    def test_setup_logging_json_processors_for_file_only(self, mock_configure, mock_isatty):
        """Test that JSON processors are used for file-only logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            setup_logging(log_dir, enable_console=True)
            
            # Should use JSON processors for file-only output
            mock_configure.assert_called_once()
            call_kwargs = mock_configure.call_args[1]
            processors = call_kwargs['processors']
            
            # Should include JSONRenderer (not ConsoleRenderer)
            processor_types = [type(p).__name__ for p in processors]
            assert 'JSONRenderer' in processor_types
            assert 'ConsoleRenderer' not in processor_types

    @patch('sys.stderr.isatty', return_value=False)
    @patch('mistral_ocr.logging.structlog.configure')
    def test_setup_logging_consistent_json_processors(self, mock_configure, mock_isatty):
        """Test that JSON processors are consistently used regardless of TTY."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            setup_logging(log_dir, enable_console=True)
            
            # Should use JSON processors consistently
            mock_configure.assert_called_once()
            call_kwargs = mock_configure.call_args[1]
            processors = call_kwargs["processors"]

            # Should include JSONRenderer
            processor_types = [type(p).__name__ for p in processors]
            assert "JSONRenderer" in processor_types


class TestSetupAuditLogging:
    """Test the setup_audit_logging function."""

    def test_setup_audit_logging_creates_directory(self):
        """Test that setup_audit_logging creates the directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "audit_logs"
            assert not log_dir.exists()

            setup_audit_logging(log_dir)

            assert log_dir.exists()
            assert log_dir.is_dir()

    def test_setup_audit_logging_creates_all_files(self):
        """Test that setup_audit_logging creates all required files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "audit_logs"

            result = setup_audit_logging(log_dir)

            # Should return dictionary with all log file paths
            assert isinstance(result, dict)
            assert "audit" in result
            assert "security" in result
            assert "performance" in result
            assert "api" in result

            # All files should be created
            for log_type, log_path in result.items():
                assert log_path.exists()
                assert log_path.is_file()

    def test_setup_audit_logging_returns_correct_paths(self):
        """Test that setup_audit_logging returns correct file paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "audit_logs"

            result = setup_audit_logging(log_dir)

            assert result["audit"] == log_dir / "audit.log"
            assert result["security"] == log_dir / "security.log"
            assert result["performance"] == log_dir / "performance.log"
            assert result["api"] == log_dir / "api.log"


class TestGetLogger:
    """Test the get_logger function."""

    @patch("mistral_ocr.logging.structlog.get_logger")
    def test_get_logger_calls_structlog(self, mock_get_logger):
        """Test that get_logger calls structlog.get_logger."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        result = get_logger("test_component")

        mock_get_logger.assert_called_once_with("test_component")
        assert result == mock_logger

    def test_get_logger_returns_logger_instance(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test_component")

        # Should have logger methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")


class TestLogPathHelpers:
    """Test the log path helper functions."""

    def test_get_audit_log_path(self):
        """Test get_audit_log_path function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            result = get_audit_log_path(log_dir)

            assert result == log_dir / "audit.log"

    def test_get_performance_log_path(self):
        """Test get_performance_log_path function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"

            result = get_performance_log_path(log_dir)

            assert result == log_dir / "performance.log"


class TestConfigureLogLevel:
    """Test the configure_log_level function."""

    @patch("mistral_ocr.logging.structlog.configure")
    @patch("mistral_ocr.logging.logging.getLogger")
    def test_configure_log_level_debug(self, mock_get_logger, mock_configure):
        """Test configuring log level to DEBUG."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        configure_log_level("DEBUG")

        # Should configure structlog
        mock_configure.assert_called_once()

        # Should set Python logging level
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)

    @patch("mistral_ocr.logging.structlog.configure")
    @patch("mistral_ocr.logging.logging.getLogger")
    def test_configure_log_level_info(self, mock_get_logger, mock_configure):
        """Test configuring log level to INFO."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        configure_log_level("INFO")

        mock_logger.setLevel.assert_called_once_with(logging.INFO)

    @patch("mistral_ocr.logging.structlog.configure")
    @patch("mistral_ocr.logging.logging.getLogger")
    def test_configure_log_level_warning(self, mock_get_logger, mock_configure):
        """Test configuring log level to WARNING."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        configure_log_level("WARNING")

        mock_logger.setLevel.assert_called_once_with(logging.WARNING)

    @patch("mistral_ocr.logging.structlog.configure")
    @patch("mistral_ocr.logging.logging.getLogger")
    def test_configure_log_level_error(self, mock_get_logger, mock_configure):
        """Test configuring log level to ERROR."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        configure_log_level("ERROR")

        mock_logger.setLevel.assert_called_once_with(logging.ERROR)

    @patch("mistral_ocr.logging.structlog.configure")
    def test_configure_log_level_updates_structlog_wrapper(self, mock_configure):
        """Test that configure_log_level updates structlog wrapper class."""
        configure_log_level("WARNING")

        mock_configure.assert_called_once()
        call_kwargs = mock_configure.call_args[1]
        assert "wrapper_class" in call_kwargs


class TestLoggingIntegration:
    """Integration tests for logging infrastructure."""

    def test_complete_logging_setup_workflow(self):
        """Test complete logging setup workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "integration_logs"

            # Setup main logging
            main_log_path = setup_logging(log_dir, level="DEBUG")

            # Setup audit logging
            audit_paths = setup_audit_logging(log_dir)

            # Get a logger and test it
            logger = get_logger("integration_test")

            # Log messages at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            # All log files should exist
            assert main_log_path.exists()
            for audit_path in audit_paths.values():
                assert audit_path.exists()

    def test_audit_processor_with_real_event(self):
        """Test AuditProcessor with realistic event data."""
        processor = AuditProcessor()

        # Realistic audit event
        event_dict = {
            "event": "User authentication successful",
            "event_type": "authentication",
            "component": "auth_service",
            "user_id": "user_12345",
            "api_key": "sk-real-api-key-abcdef",
            "timestamp": "2024-01-01T12:00:00Z",
            "outcome": "success",
            "details": {"method": "api_key", "source_ip": "192.168.1.100"},
        }

        result = processor(None, "info", event_dict)

        # Should add audit trail marker
        assert result["audit_trail"] is True

        # Should sanitize API key
        assert "api_key" not in result
        assert "api_key_hash" in result

        # Should preserve other fields
        assert result["event"] == "User authentication successful"
        assert result["user_id"] == "user_12345"
        assert result["outcome"] == "success"
        assert result["details"]["source_ip"] == "192.168.1.100"

    def test_log_rotation_configuration(self):
        """Test that log rotation is properly configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "rotation_test"

            # Setup with small file size for testing
            setup_logging(
                log_dir,
                max_bytes=1024,  # 1KB
                backup_count=2,
            )

            # Log files should be created
            main_log = log_dir / "mistral.log"
            assert main_log.exists()

    def test_multiple_logger_instances(self):
        """Test that multiple logger instances work correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "multi_logger_test"
            setup_logging(log_dir)

            # Create multiple loggers
            logger1 = get_logger("component1")
            logger2 = get_logger("component2")
            logger3 = get_logger("component3")

            # All should be usable
            logger1.info("Message from component1")
            logger2.warning("Message from component2")
            logger3.error("Message from component3")

    def test_logging_with_structured_data(self):
        """Test logging with complex structured data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "structured_test"
            setup_logging(log_dir, level="DEBUG")

            logger = get_logger("structured_test")

            # Log with complex structured data
            logger.info(
                "Batch processing completed",
                batch_id="batch_12345",
                file_count=150,
                processing_time=45.7,
                files_processed=[
                    {"name": "file1.pdf", "size": 1024, "status": "success"},
                    {"name": "file2.png", "size": 2048, "status": "success"},
                ],
                metadata={"user_id": "user_789", "job_type": "ocr_batch", "priority": "high"},
            )

    def test_error_handling_in_logging(self):
        """Test that logging handles errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "error_test"
            setup_logging(log_dir)

            logger = get_logger("error_test")

            # Should handle various data types without errors
            logger.info("Test with None", data=None)
            logger.info("Test with empty dict", data={})
            logger.info("Test with circular reference", data={"self": "circular"})

    def test_performance_of_logging_setup(self):
        """Test that logging setup is performant."""
        import time

        start_time = time.time()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "performance_test"

            # Setup logging multiple times
            for i in range(10):
                setup_logging(log_dir / f"test_{i}")

        duration = time.time() - start_time

        # Should complete quickly
        assert duration < 2.0  # Less than 2 seconds for 10 setups
