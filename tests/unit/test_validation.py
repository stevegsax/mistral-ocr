"""Unit tests for validation decorators."""

import pathlib
import pytest
import sqlite3

from mistral_ocr.validation import (
    validate_api_key,
    validate_job_id,
    validate_model_name,
    validate_timeout_range,
    validate_retry_count,
    validate_file_exists,
    validate_directory_path,
    require_database_connection,
    validate_supported_file_type
)
from mistral_ocr.exceptions import (
    InvalidConfigurationError,
    InvalidJobIdError,
    DatabaseConnectionError,
    UnsupportedFileTypeError
)


class TestValidateAPIKey:
    """Test API key validation decorator."""

    def test_valid_api_key_passes(self):
        """Test that valid API keys pass validation."""
        @validate_api_key
        def dummy_method(self, api_key: str) -> str:
            return f"processed {api_key}"
        
        result = dummy_method(None, "sk-1234567890abcdef")
        assert result == "processed sk-1234567890abcdef"

    def test_empty_api_key_raises_error(self):
        """Test that empty API key raises InvalidConfigurationError."""
        @validate_api_key
        def dummy_method(self, api_key: str) -> str:
            return f"processed {api_key}"
        
        with pytest.raises(InvalidConfigurationError, match="API key must be a non-empty string"):
            dummy_method(None, "")

    def test_none_api_key_raises_error(self):
        """Test that None API key raises InvalidConfigurationError."""
        @validate_api_key
        def dummy_method(self, api_key: str) -> str:
            return f"processed {api_key}"
        
        with pytest.raises(InvalidConfigurationError, match="API key must be a non-empty string"):
            dummy_method(None, None)

    def test_short_api_key_raises_error(self):
        """Test that short API key raises InvalidConfigurationError."""
        @validate_api_key
        def dummy_method(self, api_key: str) -> str:
            return f"processed {api_key}"
        
        with pytest.raises(InvalidConfigurationError, match="API key appears to be too short"):
            dummy_method(None, "x")

    def test_non_string_api_key_raises_error(self):
        """Test that non-string API key raises InvalidConfigurationError."""
        @validate_api_key
        def dummy_method(self, api_key: str) -> str:
            return f"processed {api_key}"
        
        with pytest.raises(InvalidConfigurationError, match="API key must be a non-empty string"):
            dummy_method(None, 12345)


class TestValidateJobID:
    """Test job ID validation decorator."""

    def test_valid_job_id_passes(self):
        """Test that valid job IDs pass validation."""
        @validate_job_id
        def dummy_method(self, job_id: str) -> str:
            return f"processed {job_id}"
        
        result = dummy_method(None, "job123")
        assert result == "processed job123"

    def test_invalid_job_id_raises_error(self):
        """Test that job ID containing 'invalid' raises InvalidJobIdError."""
        @validate_job_id
        def dummy_method(self, job_id: str) -> str:
            return f"processed {job_id}"
        
        with pytest.raises(InvalidJobIdError, match="Invalid job ID: invalid_job"):
            dummy_method(None, "invalid_job")

    def test_case_insensitive_invalid_job_id(self):
        """Test that 'invalid' check is case insensitive."""
        @validate_job_id
        def dummy_method(self, job_id: str) -> str:
            return f"processed {job_id}"
        
        with pytest.raises(InvalidJobIdError, match="Invalid job ID: INVALID"):
            dummy_method(None, "INVALID")
        
        with pytest.raises(InvalidJobIdError, match="Invalid job ID: Invalid_Test"):
            dummy_method(None, "Invalid_Test")


class TestValidateModelName:
    """Test model name validation decorator."""

    def test_valid_model_name_passes(self):
        """Test that valid model names pass validation."""
        @validate_model_name
        def dummy_method(self, model: str) -> str:
            return f"using model {model}"
        
        result = dummy_method(None, "mistral-ocr-latest")
        assert result == "using model mistral-ocr-latest"

    def test_empty_model_name_raises_error(self):
        """Test that empty model name raises InvalidConfigurationError."""
        @validate_model_name
        def dummy_method(self, model: str) -> str:
            return f"using model {model}"
        
        with pytest.raises(InvalidConfigurationError, match="Model name must be a non-empty string"):
            dummy_method(None, "")

    def test_whitespace_only_model_name_raises_error(self):
        """Test that whitespace-only model name raises InvalidConfigurationError."""
        @validate_model_name
        def dummy_method(self, model: str) -> str:
            return f"using model {model}"
        
        with pytest.raises(InvalidConfigurationError, match="Model name cannot be empty"):
            dummy_method(None, "   ")

    def test_none_model_name_raises_error(self):
        """Test that None model name raises InvalidConfigurationError."""
        @validate_model_name
        def dummy_method(self, model: str) -> str:
            return f"using model {model}"
        
        with pytest.raises(InvalidConfigurationError, match="Model name must be a non-empty string"):
            dummy_method(None, None)


class TestValidateTimeoutRange:
    """Test timeout range validation decorator."""

    def test_valid_timeout_passes(self):
        """Test that valid timeout values pass validation."""
        @validate_timeout_range
        def dummy_method(self, timeout: int) -> str:
            return f"timeout set to {timeout}"
        
        result = dummy_method(None, 30)
        assert result == "timeout set to 30"

    def test_timeout_at_minimum_passes(self):
        """Test that timeout at minimum value (1) passes."""
        @validate_timeout_range
        def dummy_method(self, timeout: int) -> str:
            return f"timeout set to {timeout}"
        
        result = dummy_method(None, 1)
        assert result == "timeout set to 1"

    def test_timeout_at_maximum_passes(self):
        """Test that timeout at maximum value passes."""
        @validate_timeout_range
        def dummy_method(self, timeout: int) -> str:
            return f"timeout set to {timeout}"
        
        result = dummy_method(None, 3600)  # MAX_API_TIMEOUT_SECONDS
        assert result == "timeout set to 3600"

    def test_zero_timeout_raises_error(self):
        """Test that zero timeout raises InvalidConfigurationError."""
        @validate_timeout_range
        def dummy_method(self, timeout: int) -> str:
            return f"timeout set to {timeout}"
        
        with pytest.raises(InvalidConfigurationError, match="Timeout must be an integer between 1 and 3600 seconds"):
            dummy_method(None, 0)

    def test_negative_timeout_raises_error(self):
        """Test that negative timeout raises InvalidConfigurationError."""
        @validate_timeout_range
        def dummy_method(self, timeout: int) -> str:
            return f"timeout set to {timeout}"
        
        with pytest.raises(InvalidConfigurationError, match="Timeout must be an integer between 1 and 3600 seconds"):
            dummy_method(None, -5)

    def test_excessive_timeout_raises_error(self):
        """Test that timeout above maximum raises InvalidConfigurationError."""
        @validate_timeout_range
        def dummy_method(self, timeout: int) -> str:
            return f"timeout set to {timeout}"
        
        with pytest.raises(InvalidConfigurationError, match="Timeout must be an integer between 1 and 3600 seconds"):
            dummy_method(None, 7200)

    def test_non_integer_timeout_raises_error(self):
        """Test that non-integer timeout raises InvalidConfigurationError."""
        @validate_timeout_range
        def dummy_method(self, timeout: int) -> str:
            return f"timeout set to {timeout}"
        
        with pytest.raises(InvalidConfigurationError, match="Timeout must be an integer between 1 and 3600 seconds"):
            dummy_method(None, "30")


class TestValidateRetryCount:
    """Test retry count validation decorator."""

    def test_valid_retry_count_passes(self):
        """Test that valid retry counts pass validation."""
        @validate_retry_count
        def dummy_method(self, retries: int) -> str:
            return f"retries set to {retries}"
        
        result = dummy_method(None, 3)
        assert result == "retries set to 3"

    def test_zero_retries_passes(self):
        """Test that zero retries passes validation."""
        @validate_retry_count
        def dummy_method(self, retries: int) -> str:
            return f"retries set to {retries}"
        
        result = dummy_method(None, 0)
        assert result == "retries set to 0"

    def test_maximum_retries_passes(self):
        """Test that maximum retry count passes."""
        @validate_retry_count
        def dummy_method(self, retries: int) -> str:
            return f"retries set to {retries}"
        
        result = dummy_method(None, 10)  # MAX_RETRIES_LIMIT
        assert result == "retries set to 10"

    def test_negative_retries_raises_error(self):
        """Test that negative retries raises InvalidConfigurationError."""
        @validate_retry_count
        def dummy_method(self, retries: int) -> str:
            return f"retries set to {retries}"
        
        with pytest.raises(InvalidConfigurationError, match="Max retries must be an integer between 0 and 10"):
            dummy_method(None, -1)

    def test_excessive_retries_raises_error(self):
        """Test that retries above maximum raises InvalidConfigurationError."""
        @validate_retry_count
        def dummy_method(self, retries: int) -> str:
            return f"retries set to {retries}"
        
        with pytest.raises(InvalidConfigurationError, match="Max retries must be an integer between 0 and 10"):
            dummy_method(None, 15)

    def test_non_integer_retries_raises_error(self):
        """Test that non-integer retries raises InvalidConfigurationError."""
        @validate_retry_count
        def dummy_method(self, retries: int) -> str:
            return f"retries set to {retries}"
        
        with pytest.raises(InvalidConfigurationError, match="Max retries must be an integer between 0 and 10"):
            dummy_method(None, "3")


class TestValidateFileExists:
    """Test file existence validation decorator."""

    def test_existing_file_passes(self, tmp_path):
        """Test that existing files pass validation."""
        @validate_file_exists
        def dummy_method(self, file_path: pathlib.Path) -> str:
            return f"processing {file_path.name}"
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = dummy_method(None, test_file)
        assert result == "processing test.txt"

    def test_nonexistent_file_raises_error(self, tmp_path):
        """Test that nonexistent file raises FileNotFoundError."""
        @validate_file_exists
        def dummy_method(self, file_path: pathlib.Path) -> str:
            return f"processing {file_path.name}"
        
        missing_file = tmp_path / "missing.txt"
        
        with pytest.raises(FileNotFoundError, match="File not found"):
            dummy_method(None, missing_file)


class TestValidateDirectoryPath:
    """Test directory path validation decorator."""

    def test_existing_directory_passes(self, tmp_path):
        """Test that existing directories pass validation."""
        @validate_directory_path
        def dummy_method(self, path: pathlib.Path) -> str:
            return f"using directory {path.name}"
        
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        result = dummy_method(None, test_dir)
        assert result == "using directory test_dir"

    def test_nonexistent_directory_gets_created(self, tmp_path):
        """Test that nonexistent directories are created automatically."""
        @validate_directory_path
        def dummy_method(self, path: pathlib.Path) -> str:
            return f"using directory {path.name}"
        
        new_dir = tmp_path / "new_dir" / "nested"
        
        result = dummy_method(None, new_dir)
        assert result == "using directory nested"
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_invalid_path_type_raises_error(self):
        """Test that non-Path objects raise InvalidConfigurationError."""
        @validate_directory_path
        def dummy_method(self, path: pathlib.Path) -> str:
            return f"using directory {path}"
        
        with pytest.raises(InvalidConfigurationError, match="Directory path must be a Path object"):
            dummy_method(None, "/some/string/path")


class TestRequireDatabaseConnection:
    """Test database connection requirement decorator."""

    def test_with_valid_connection_passes(self):
        """Test that method passes with valid database connection."""
        @require_database_connection
        def dummy_method(self) -> str:
            return "database operation successful"
        
        # Create mock object with connection
        mock_obj = type('MockDB', (), {'connection': sqlite3.connect(':memory:')})()
        
        result = dummy_method(mock_obj)
        assert result == "database operation successful"

    def test_without_connection_raises_error(self):
        """Test that method raises error without database connection."""
        @require_database_connection
        def dummy_method(self) -> str:
            return "database operation successful"
        
        # Create mock object without connection
        mock_obj = type('MockDB', (), {'connection': None})()
        
        with pytest.raises(DatabaseConnectionError, match="Database not connected"):
            dummy_method(mock_obj)

    def test_without_connection_attribute_raises_error(self):
        """Test that method raises error when connection attribute doesn't exist."""
        @require_database_connection
        def dummy_method(self) -> str:
            return "database operation successful"
        
        # Create mock object without connection attribute
        mock_obj = type('MockDB', (), {})()
        
        with pytest.raises(DatabaseConnectionError, match="Database not connected"):
            dummy_method(mock_obj)


class TestValidateSupportedFileType:
    """Test supported file type validation decorator."""

    def test_supported_extension_passes(self, tmp_path):
        """Test that supported file extensions pass validation."""
        supported_exts = {'.png', '.jpg', '.pdf'}
        
        @validate_supported_file_type(supported_exts)
        def dummy_method(self, file_path: pathlib.Path) -> str:
            return f"processing {file_path.suffix}"
        
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake png content")
        
        result = dummy_method(None, test_file)
        assert result == "processing .png"

    def test_unsupported_extension_raises_error(self, tmp_path):
        """Test that unsupported file extensions raise UnsupportedFileTypeError."""
        supported_exts = {'.png', '.jpg', '.pdf'}
        
        @validate_supported_file_type(supported_exts)
        def dummy_method(self, file_path: pathlib.Path) -> str:
            return f"processing {file_path.suffix}"
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("text content")
        
        with pytest.raises(UnsupportedFileTypeError, match="Unsupported file type: .txt"):
            dummy_method(None, test_file)

    def test_case_insensitive_extension_check(self, tmp_path):
        """Test that extension checking is case insensitive."""
        supported_exts = {'.png', '.jpg', '.pdf'}
        
        @validate_supported_file_type(supported_exts)
        def dummy_method(self, file_path: pathlib.Path) -> str:
            return f"processing {file_path.suffix}"
        
        test_file = tmp_path / "test.PNG"
        test_file.write_bytes(b"fake png content")
        
        result = dummy_method(None, test_file)
        assert result == "processing .PNG"

    def test_empty_extension_raises_error(self, tmp_path):
        """Test that files without extensions raise UnsupportedFileTypeError."""
        supported_exts = {'.png', '.jpg', '.pdf'}
        
        @validate_supported_file_type(supported_exts)
        def dummy_method(self, file_path: pathlib.Path) -> str:
            return f"processing {file_path.suffix}"
        
        test_file = tmp_path / "test"
        test_file.write_text("no extension")
        
        with pytest.raises(UnsupportedFileTypeError, match="Unsupported file type: "):
            dummy_method(None, test_file)