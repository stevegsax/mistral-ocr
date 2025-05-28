"""Unit tests for file operations utilities."""

import json
import pathlib
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from mistral_ocr.utils.file_operations import (
    FileSystemUtils,
    FileIOUtils,
    FileEncodingUtils,
    FileTypeUtils,
    TempFileUtils,
    PathUtils
)


class TestFileSystemUtils:
    """Test FileSystemUtils functionality."""

    def test_validate_path_exists_with_existing_path(self, tmp_path):
        """Test path validation with existing path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        # Should not raise any exception
        FileSystemUtils.validate_path_exists(test_file)

    def test_validate_path_exists_with_nonexistent_path(self, tmp_path):
        """Test path validation with nonexistent path."""
        missing_path = tmp_path / "missing.txt"
        
        with pytest.raises(FileNotFoundError, match="Path not found"):
            FileSystemUtils.validate_path_exists(missing_path)

    def test_ensure_directory_exists_creates_directory(self, tmp_path):
        """Test directory creation with parents."""
        new_dir = tmp_path / "new" / "nested" / "directory"
        
        result = FileSystemUtils.ensure_directory_exists(new_dir)
        
        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_exists_with_existing_directory(self, tmp_path):
        """Test directory creation when directory already exists."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        
        result = FileSystemUtils.ensure_directory_exists(existing_dir)
        
        assert result == existing_dir
        assert existing_dir.exists()

    def test_safe_delete_file_removes_existing_file(self, tmp_path):
        """Test safe file deletion with existing file."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("content")
        
        result = FileSystemUtils.safe_delete_file(test_file)
        
        assert result is True
        assert not test_file.exists()

    def test_safe_delete_file_with_nonexistent_file(self, tmp_path):
        """Test safe file deletion with nonexistent file."""
        missing_file = tmp_path / "missing.txt"
        
        result = FileSystemUtils.safe_delete_file(missing_file)
        
        assert result is True  # Should succeed even if file doesn't exist

    def test_safe_delete_file_with_logger(self, tmp_path):
        """Test safe file deletion with logger."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("content")
        
        mock_logger = MagicMock()
        result = FileSystemUtils.safe_delete_file(test_file, mock_logger)
        
        assert result is True
        assert not test_file.exists()
        mock_logger.debug.assert_called_once()

    def test_safe_delete_file_handles_permission_error(self, tmp_path):
        """Test safe file deletion handles permission errors gracefully."""
        test_file = tmp_path / "protected.txt"
        test_file.write_text("content")
        
        # Mock unlink to raise OSError
        with patch.object(pathlib.Path, 'unlink', side_effect=OSError("Permission denied")):
            result = FileSystemUtils.safe_delete_file(test_file)
            
        assert result is False

    def test_check_file_size_returns_correct_size(self, tmp_path):
        """Test file size checking returns correct size."""
        test_file = tmp_path / "test.txt"
        content = "test content"
        test_file.write_text(content)
        
        size = FileSystemUtils.check_file_size(test_file)
        
        assert size == len(content.encode())

    def test_check_file_size_with_limit_passes(self, tmp_path):
        """Test file size checking with limit that passes."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("small")
        
        size = FileSystemUtils.check_file_size(test_file, max_size=100)
        
        assert size == 5

    def test_check_file_size_with_limit_fails(self, tmp_path):
        """Test file size checking with limit that fails."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("large content that exceeds limit")
        
        with pytest.raises(ValueError, match="exceeds limit"):
            FileSystemUtils.check_file_size(test_file, max_size=5)

    def test_check_file_size_with_nonexistent_file(self, tmp_path):
        """Test file size checking with nonexistent file."""
        missing_file = tmp_path / "missing.txt"
        
        with pytest.raises(FileNotFoundError, match="File not found"):
            FileSystemUtils.check_file_size(missing_file)

    def test_is_hidden_file_with_hidden_file(self):
        """Test hidden file detection with hidden file."""
        hidden_file = pathlib.Path(".hidden")
        
        result = FileSystemUtils.is_hidden_file(hidden_file)
        
        assert result is True

    def test_is_hidden_file_with_normal_file(self):
        """Test hidden file detection with normal file."""
        normal_file = pathlib.Path("normal.txt")
        
        result = FileSystemUtils.is_hidden_file(normal_file)
        
        assert result is False


class TestFileIOUtils:
    """Test FileIOUtils functionality."""

    def test_read_json_file_success(self, tmp_path):
        """Test JSON file reading success."""
        test_data = {"key": "value", "number": 42}
        json_file = tmp_path / "test.json"
        
        with open(json_file, 'w') as f:
            json.dump(test_data, f)
        
        result = FileIOUtils.read_json_file(json_file)
        
        assert result == test_data

    def test_read_json_file_with_nonexistent_file(self, tmp_path):
        """Test JSON file reading with nonexistent file."""
        missing_file = tmp_path / "missing.json"
        
        with pytest.raises(FileNotFoundError):
            FileIOUtils.read_json_file(missing_file)

    def test_read_json_file_with_invalid_json(self, tmp_path):
        """Test JSON file reading with invalid JSON."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("invalid json content")
        
        with pytest.raises(json.JSONDecodeError):
            FileIOUtils.read_json_file(json_file)

    def test_write_json_file_success(self, tmp_path):
        """Test JSON file writing success."""
        test_data = {"key": "value", "list": [1, 2, 3]}
        json_file = tmp_path / "output.json"
        
        FileIOUtils.write_json_file(json_file, test_data)
        
        assert json_file.exists()
        with open(json_file, 'r') as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

    def test_write_json_file_creates_parent_directory(self, tmp_path):
        """Test JSON file writing creates parent directories."""
        test_data = {"nested": "data"}
        json_file = tmp_path / "nested" / "dir" / "output.json"
        
        FileIOUtils.write_json_file(json_file, test_data, indent=4)
        
        assert json_file.exists()
        assert json_file.parent.exists()

    def test_read_binary_file_success(self, tmp_path):
        """Test binary file reading success."""
        binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(binary_data)
        
        result = FileIOUtils.read_binary_file(binary_file)
        
        assert result == binary_data

    def test_read_binary_file_with_nonexistent_file(self, tmp_path):
        """Test binary file reading with nonexistent file."""
        missing_file = tmp_path / "missing.bin"
        
        with pytest.raises(FileNotFoundError):
            FileIOUtils.read_binary_file(missing_file)

    def test_write_text_file_success(self, tmp_path):
        """Test text file writing success."""
        content = "Hello, World!\nLine 2\nUnicode: 🎉"
        text_file = tmp_path / "output.txt"
        
        FileIOUtils.write_text_file(text_file, content)
        
        assert text_file.exists()
        assert text_file.read_text(encoding="utf-8") == content

    def test_write_text_file_with_custom_encoding(self, tmp_path):
        """Test text file writing with custom encoding."""
        content = "ASCII content only"
        text_file = tmp_path / "ascii.txt"
        
        FileIOUtils.write_text_file(text_file, content, encoding="ascii")
        
        assert text_file.exists()
        assert text_file.read_text(encoding="ascii") == content

    def test_write_text_file_creates_parent_directory(self, tmp_path):
        """Test text file writing creates parent directories."""
        content = "Nested file content"
        text_file = tmp_path / "deep" / "nested" / "output.txt"
        
        FileIOUtils.write_text_file(text_file, content)
        
        assert text_file.exists()
        assert text_file.parent.exists()

    def test_read_text_file_success(self, tmp_path):
        """Test text file reading success."""
        content = "Test content with unicode: 🚀"
        text_file = tmp_path / "test.txt"
        text_file.write_text(content, encoding="utf-8")
        
        result = FileIOUtils.read_text_file(text_file)
        
        assert result == content

    def test_read_text_file_with_custom_encoding(self, tmp_path):
        """Test text file reading with custom encoding."""
        content = "ASCII only content"
        text_file = tmp_path / "ascii.txt"
        text_file.write_text(content, encoding="ascii")
        
        result = FileIOUtils.read_text_file(text_file, encoding="ascii")
        
        assert result == content

    def test_read_text_file_with_nonexistent_file(self, tmp_path):
        """Test text file reading with nonexistent file."""
        missing_file = tmp_path / "missing.txt"
        
        with pytest.raises(FileNotFoundError):
            FileIOUtils.read_text_file(missing_file)


class TestFileEncodingUtils:
    """Test FileEncodingUtils functionality."""

    def test_encode_to_base64_success(self, tmp_path):
        """Test base64 encoding success."""
        content = b"Hello, World!"
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(content)
        
        result = FileEncodingUtils.encode_to_base64(test_file)
        
        import base64
        expected = base64.b64encode(content).decode("utf-8")
        assert result == expected

    def test_encode_to_base64_with_nonexistent_file(self, tmp_path):
        """Test base64 encoding with nonexistent file."""
        missing_file = tmp_path / "missing.txt"
        
        with pytest.raises(FileNotFoundError):
            FileEncodingUtils.encode_to_base64(missing_file)

    def test_encode_to_data_url_with_png(self, tmp_path):
        """Test data URL encoding with PNG file."""
        png_content = b"\x89PNG\r\n\x1a\n"
        png_file = tmp_path / "test.png"
        png_file.write_bytes(png_content)
        
        result = FileEncodingUtils.encode_to_data_url(png_file)
        
        assert result.startswith("data:image/png;base64,")
        
        # Verify the base64 part is correct
        import base64
        expected_b64 = base64.b64encode(png_content).decode("utf-8")
        assert result == f"data:image/png;base64,{expected_b64}"

    def test_encode_to_data_url_with_jpg(self, tmp_path):
        """Test data URL encoding with JPEG file."""
        jpg_content = b"\xff\xd8\xff\xe0"
        jpg_file = tmp_path / "test.jpg"
        jpg_file.write_bytes(jpg_content)
        
        result = FileEncodingUtils.encode_to_data_url(jpg_file)
        
        assert result.startswith("data:image/jpeg;base64,")

    def test_encode_to_data_url_with_pdf(self, tmp_path):
        """Test data URL encoding with PDF file."""
        pdf_content = b"%PDF-1.4"
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(pdf_content)
        
        result = FileEncodingUtils.encode_to_data_url(pdf_file)
        
        assert result.startswith("data:application/pdf;base64,")


class TestFileTypeUtils:
    """Test FileTypeUtils functionality."""

    def test_is_supported_extension_with_supported_type(self):
        """Test supported extension check with supported type."""
        supported_exts = {'.png', '.jpg', '.pdf'}
        test_path = pathlib.Path("test.png")
        
        result = FileTypeUtils.is_supported_extension(test_path, supported_exts)
        
        assert result is True

    def test_is_supported_extension_case_insensitive(self):
        """Test supported extension check is case insensitive."""
        supported_exts = {'.png', '.jpg', '.pdf'}
        test_path = pathlib.Path("test.PNG")
        
        result = FileTypeUtils.is_supported_extension(test_path, supported_exts)
        
        assert result is True

    def test_is_supported_extension_with_unsupported_type(self):
        """Test supported extension check with unsupported type."""
        supported_exts = {'.png', '.jpg', '.pdf'}
        test_path = pathlib.Path("test.txt")
        
        result = FileTypeUtils.is_supported_extension(test_path, supported_exts)
        
        assert result is False

    def test_get_mime_type_for_png(self):
        """Test MIME type detection for PNG."""
        png_path = pathlib.Path("test.png")
        
        result = FileTypeUtils.get_mime_type(png_path)
        
        assert result == "image/png"

    def test_get_mime_type_for_jpeg(self):
        """Test MIME type detection for JPEG."""
        jpg_path = pathlib.Path("test.jpg")
        
        result = FileTypeUtils.get_mime_type(jpg_path)
        
        assert result == "image/jpeg"
        
        # Test .jpeg extension as well
        jpeg_path = pathlib.Path("test.jpeg")
        result = FileTypeUtils.get_mime_type(jpeg_path)
        assert result == "image/jpeg"

    def test_get_mime_type_for_pdf(self):
        """Test MIME type detection for PDF."""
        pdf_path = pathlib.Path("test.pdf")
        
        result = FileTypeUtils.get_mime_type(pdf_path)
        
        assert result == "application/pdf"

    def test_get_mime_type_fallback(self):
        """Test MIME type detection fallback for unknown types."""
        unknown_path = pathlib.Path("test.unknownext")
        
        result = FileTypeUtils.get_mime_type(unknown_path)
        
        assert result == "application/octet-stream"

    def test_filter_supported_files_success(self, tmp_path):
        """Test file filtering with supported files."""
        # Create test files
        supported_files = []
        unsupported_files = []
        
        for ext in ['.png', '.jpg', '.pdf']:
            file_path = tmp_path / f"test{ext}"
            file_path.write_bytes(b"content")
            supported_files.append(file_path)
        
        for ext in ['.txt', '.doc']:
            file_path = tmp_path / f"test{ext}"
            file_path.write_bytes(b"content")
            unsupported_files.append(file_path)
        
        all_files = supported_files + unsupported_files
        supported_exts = {'.png', '.jpg', '.pdf'}
        
        result = FileTypeUtils.filter_supported_files(all_files, supported_exts)
        
        assert len(result) == 3
        assert all(path in result for path in supported_files)
        assert all(path not in result for path in unsupported_files)

    def test_filter_supported_files_excludes_hidden_by_default(self, tmp_path):
        """Test file filtering excludes hidden files by default."""
        # Create regular and hidden files
        regular_file = tmp_path / "test.png"
        hidden_file = tmp_path / ".hidden.png"
        
        regular_file.write_bytes(b"content")
        hidden_file.write_bytes(b"content")
        
        all_files = [regular_file, hidden_file]
        supported_exts = {'.png'}
        
        result = FileTypeUtils.filter_supported_files(all_files, supported_exts)
        
        assert len(result) == 1
        assert regular_file in result
        assert hidden_file not in result

    def test_filter_supported_files_includes_hidden_when_requested(self, tmp_path):
        """Test file filtering includes hidden files when requested."""
        # Create regular and hidden files
        regular_file = tmp_path / "test.png"
        hidden_file = tmp_path / ".hidden.png"
        
        regular_file.write_bytes(b"content")
        hidden_file.write_bytes(b"content")
        
        all_files = [regular_file, hidden_file]
        supported_exts = {'.png'}
        
        result = FileTypeUtils.filter_supported_files(all_files, supported_exts, include_hidden=True)
        
        assert len(result) == 2
        assert regular_file in result
        assert hidden_file in result

    def test_filter_supported_files_only_includes_files(self, tmp_path):
        """Test file filtering only includes actual files, not directories."""
        # Create file and directory
        test_file = tmp_path / "test.png"
        test_dir = tmp_path / "test_dir.png"  # Directory with file extension
        
        test_file.write_bytes(b"content")
        test_dir.mkdir()
        
        all_paths = [test_file, test_dir]
        supported_exts = {'.png'}
        
        result = FileTypeUtils.filter_supported_files(all_paths, supported_exts)
        
        assert len(result) == 1
        assert test_file in result
        assert test_dir not in result


class TestTempFileUtils:
    """Test TempFileUtils functionality."""

    def test_create_temp_file_success(self):
        """Test temporary file creation success."""
        temp_path, fd = TempFileUtils.create_temp_file(suffix=".test", prefix="test_")
        
        try:
            assert temp_path.exists()
            assert temp_path.name.startswith("test_")
            assert temp_path.name.endswith(".test")
            assert isinstance(fd, int)
        finally:
            import os
            os.close(fd)
            temp_path.unlink(missing_ok=True)

    def test_create_temp_file_default_parameters(self):
        """Test temporary file creation with default parameters."""
        temp_path, fd = TempFileUtils.create_temp_file()
        
        try:
            assert temp_path.exists()
            assert temp_path.name.startswith("mistral_ocr_")
        finally:
            import os
            os.close(fd)
            temp_path.unlink(missing_ok=True)

    def test_cleanup_temp_file_success(self, tmp_path):
        """Test temporary file cleanup success."""
        temp_file = tmp_path / "temp_test.tmp"
        temp_file.write_text("temporary content")
        
        TempFileUtils.cleanup_temp_file(temp_file)
        
        assert not temp_file.exists()

    def test_cleanup_temp_file_with_logger(self, tmp_path):
        """Test temporary file cleanup with logger."""
        temp_file = tmp_path / "temp_test.tmp"
        temp_file.write_text("temporary content")
        
        mock_logger = MagicMock()
        TempFileUtils.cleanup_temp_file(temp_file, mock_logger)
        
        assert not temp_file.exists()
        mock_logger.debug.assert_called_once()

    def test_cleanup_temp_file_with_nonexistent_file(self, tmp_path):
        """Test temporary file cleanup with nonexistent file."""
        missing_file = tmp_path / "missing.tmp"
        
        # Should not raise exception
        TempFileUtils.cleanup_temp_file(missing_file)

    def test_create_temp_directory_success(self):
        """Test temporary directory creation success."""
        temp_dir = TempFileUtils.create_temp_directory(suffix="_test", prefix="test_")
        
        try:
            assert temp_dir.exists()
            assert temp_dir.is_dir()
            assert temp_dir.name.startswith("test_")
            assert temp_dir.name.endswith("_test")
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_temp_directory_default_parameters(self):
        """Test temporary directory creation with default parameters."""
        temp_dir = TempFileUtils.create_temp_directory()
        
        try:
            assert temp_dir.exists()
            assert temp_dir.is_dir()
            assert temp_dir.name.startswith("mistral_ocr_")
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestPathUtils:
    """Test PathUtils functionality."""

    def test_resolve_with_fallback_uses_primary(self, tmp_path):
        """Test path resolution uses primary path when available."""
        primary_path = tmp_path / "primary"
        fallback_path = tmp_path / "fallback"
        
        result = PathUtils.resolve_with_fallback(primary_path, fallback_path)
        
        assert result == primary_path

    def test_resolve_with_fallback_uses_string_primary(self, tmp_path):
        """Test path resolution converts string primary to Path."""
        primary_str = str(tmp_path / "primary")
        fallback_path = tmp_path / "fallback"
        
        result = PathUtils.resolve_with_fallback(primary_str, fallback_path)
        
        assert result == pathlib.Path(primary_str)

    def test_resolve_with_fallback_uses_fallback_when_primary_none(self, tmp_path):
        """Test path resolution uses fallback when primary is None."""
        fallback_path = tmp_path / "fallback"
        
        result = PathUtils.resolve_with_fallback(None, fallback_path)
        
        assert result == fallback_path

    def test_resolve_with_fallback_uses_fallback_when_primary_empty(self, tmp_path):
        """Test path resolution uses fallback when primary is empty string."""
        fallback_path = tmp_path / "fallback"
        
        result = PathUtils.resolve_with_fallback("", fallback_path)
        
        assert result == fallback_path

    def test_normalize_path_with_relative_path(self, tmp_path):
        """Test path normalization with relative path."""
        relative_path = "relative/path"
        
        result = PathUtils.normalize_path(relative_path)
        
        assert result.is_absolute()
        assert result == pathlib.Path(relative_path).resolve()

    def test_normalize_path_with_absolute_path(self, tmp_path):
        """Test path normalization with absolute path."""
        absolute_path = tmp_path / "absolute" / "path"
        
        result = PathUtils.normalize_path(absolute_path)
        
        assert result.is_absolute()
        assert result == absolute_path.resolve()

    def test_normalize_path_with_string(self):
        """Test path normalization with string input."""
        path_str = "/some/path"
        
        result = PathUtils.normalize_path(path_str)
        
        assert result.is_absolute()
        assert result == pathlib.Path(path_str).resolve()

    def test_generate_unique_filename_with_nonexistent_file(self, tmp_path):
        """Test unique filename generation when file doesn't exist."""
        result = PathUtils.generate_unique_filename(tmp_path, prefix="test", suffix=".txt")
        
        assert result == tmp_path / "test.txt"
        assert not result.exists()

    def test_generate_unique_filename_with_existing_file(self, tmp_path):
        """Test unique filename generation when file exists."""
        # Create existing file
        existing_file = tmp_path / "test.txt"
        existing_file.write_text("existing")
        
        result = PathUtils.generate_unique_filename(tmp_path, prefix="test", suffix=".txt")
        
        assert result == tmp_path / "test_002.txt"
        assert not result.exists()

    def test_generate_unique_filename_with_multiple_existing_files(self, tmp_path):
        """Test unique filename generation with multiple existing files."""
        # Create multiple existing files
        (tmp_path / "test.txt").write_text("existing")
        (tmp_path / "test_001.txt").write_text("existing")
        (tmp_path / "test_002.txt").write_text("existing")
        
        result = PathUtils.generate_unique_filename(tmp_path, prefix="test", suffix=".txt")
        
        assert result == tmp_path / "test_003.txt"
        assert not result.exists()

    def test_generate_unique_filename_with_empty_prefix(self, tmp_path):
        """Test unique filename generation with empty prefix."""
        result = PathUtils.generate_unique_filename(tmp_path, prefix="", suffix=".txt")
        
        assert result == tmp_path / ".txt"

    def test_generate_unique_filename_handles_prefix_with_trailing_underscore(self, tmp_path):
        """Test unique filename generation handles prefix with trailing underscore."""
        existing_file = tmp_path / "test_.txt"
        existing_file.write_text("existing")
        
        result = PathUtils.generate_unique_filename(tmp_path, prefix="test_", suffix=".txt")
        
        assert result == tmp_path / "test_002.txt"