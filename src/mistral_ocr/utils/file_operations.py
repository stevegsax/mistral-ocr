"""File operation utilities for common patterns."""

import base64
import json
import mimetypes
import pathlib
import tempfile
from typing import Dict, Optional, Set, Tuple, Any, Union

import structlog


class FileSystemUtils:
    """Utilities for file system operations."""

    @staticmethod
    def validate_path_exists(path: pathlib.Path) -> None:
        """Validate that a file or directory exists.
        
        Args:
            path: Path to validate
            
        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

    @staticmethod
    def ensure_directory_exists(path: pathlib.Path) -> pathlib.Path:
        """Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Directory path to create
            
        Returns:
            The validated directory path
            
        Raises:
            OSError: If directory cannot be created
        """
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def safe_delete_file(path: pathlib.Path, logger: Optional[structlog.stdlib.BoundLogger] = None) -> bool:
        """Safely delete a file if it exists.
        
        Args:
            path: File path to delete
            logger: Optional logger for debug messages
            
        Returns:
            True if file was deleted or didn't exist, False if deletion failed
        """
        try:
            if path.exists():
                path.unlink()
                if logger:
                    logger.debug(f"Deleted file: {path.name}")
                return True
            return True  # File didn't exist, consider success
        except OSError as e:
            if logger:
                logger.warning(f"Failed to delete file {path}: {e}")
            return False

    @staticmethod
    def check_file_size(path: pathlib.Path, max_size: Optional[int] = None) -> int:
        """Check file size and optionally validate against a limit.
        
        Args:
            path: File path to check
            max_size: Optional maximum size in bytes
            
        Returns:
            File size in bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file exceeds max_size
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        size = path.stat().st_size
        
        if max_size is not None and size > max_size:
            raise ValueError(f"File {path.name} size ({size} bytes) exceeds limit ({max_size} bytes)")
        
        return size

    @staticmethod
    def is_hidden_file(path: pathlib.Path) -> bool:
        """Check if a file is hidden (starts with dot).
        
        Args:
            path: File path to check
            
        Returns:
            True if file is hidden
        """
        return path.name.startswith(".")


class FileIOUtils:
    """Utilities for file input/output operations."""

    @staticmethod
    def read_json_file(path: pathlib.Path) -> Dict[str, Any]:
        """Read and parse a JSON file.
        
        Args:
            path: Path to JSON file
            
        Returns:
            Parsed JSON data as dictionary
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def write_json_file(path: pathlib.Path, data: Dict[str, Any], indent: int = 2) -> None:
        """Write data to a JSON file.
        
        Args:
            path: Path to write JSON file
            data: Data to serialize as JSON
            indent: JSON indentation level
            
        Raises:
            OSError: If file cannot be written
        """
        # Ensure parent directory exists
        FileSystemUtils.ensure_directory_exists(path.parent)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

    @staticmethod
    def read_binary_file(path: pathlib.Path) -> bytes:
        """Read a file as binary data.
        
        Args:
            path: Path to file
            
        Returns:
            File contents as bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        with open(path, "rb") as f:
            return f.read()

    @staticmethod
    def write_text_file(path: pathlib.Path, content: str, encoding: str = "utf-8") -> None:
        """Write text content to a file.
        
        Args:
            path: Path to write file
            content: Text content to write
            encoding: Text encoding (default: utf-8)
            
        Raises:
            OSError: If file cannot be written
        """
        # Ensure parent directory exists
        FileSystemUtils.ensure_directory_exists(path.parent)
        
        with open(path, "w", encoding=encoding) as f:
            f.write(content)

    @staticmethod
    def read_text_file(path: pathlib.Path, encoding: str = "utf-8") -> str:
        """Read text content from a file.
        
        Args:
            path: Path to file
            encoding: Text encoding (default: utf-8)
            
        Returns:
            File contents as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        with open(path, "r", encoding=encoding) as f:
            return f.read()


class FileEncodingUtils:
    """Utilities for file encoding operations."""

    @staticmethod
    def encode_to_base64(file_path: pathlib.Path) -> str:
        """Encode a file to base64 string.
        
        Args:
            file_path: Path to file to encode
            
        Returns:
            Base64 encoded string
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_data = FileIOUtils.read_binary_file(file_path)
        return base64.b64encode(file_data).decode("utf-8")

    @staticmethod
    def encode_to_data_url(file_path: pathlib.Path) -> str:
        """Encode a file to data URL format.
        
        Args:
            file_path: Path to file to encode
            
        Returns:
            Data URL string (data:mime/type;base64,...)
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        mime_type = FileTypeUtils.get_mime_type(file_path)
        base64_data = FileEncodingUtils.encode_to_base64(file_path)
        return f"data:{mime_type};base64,{base64_data}"


class FileTypeUtils:
    """Utilities for file type detection and validation."""

    @staticmethod
    def is_supported_extension(path: pathlib.Path, supported_extensions: Set[str]) -> bool:
        """Check if file has a supported extension.
        
        Args:
            path: File path to check
            supported_extensions: Set of supported extensions (with dots)
            
        Returns:
            True if extension is supported
        """
        return path.suffix.lower() in supported_extensions

    @staticmethod
    def get_mime_type(path: pathlib.Path) -> str:
        """Get MIME type for a file path.
        
        Args:
            path: File path
            
        Returns:
            MIME type string
        """
        # Get extension
        ext = path.suffix.lower()
        
        # Handle specific cases for better accuracy
        if ext in {".png"}:
            return "image/png"
        elif ext in {".jpg", ".jpeg"}:
            return "image/jpeg"
        elif ext in {".pdf"}:
            return "application/pdf"
        else:
            # Fallback to mimetypes library
            mime_type, _ = mimetypes.guess_type(str(path))
            return mime_type or "application/octet-stream"

    @staticmethod
    def filter_supported_files(paths: list[pathlib.Path], supported_extensions: Set[str], 
                             include_hidden: bool = False) -> list[pathlib.Path]:
        """Filter a list of paths to only supported file types.
        
        Args:
            paths: List of file paths to filter
            supported_extensions: Set of supported extensions
            include_hidden: Whether to include hidden files
            
        Returns:
            Filtered list of supported file paths
        """
        valid_files = []
        for path in paths:
            if (path.is_file() and 
                FileTypeUtils.is_supported_extension(path, supported_extensions) and
                (include_hidden or not FileSystemUtils.is_hidden_file(path))):
                valid_files.append(path)
        return valid_files


class TempFileUtils:
    """Utilities for temporary file operations."""

    @staticmethod
    def create_temp_file(suffix: str = "", prefix: str = "mistral_ocr_") -> Tuple[pathlib.Path, int]:
        """Create a temporary file.
        
        Args:
            suffix: File suffix (e.g., ".jsonl")
            prefix: File prefix
            
        Returns:
            Tuple of (Path to temp file, file descriptor)
        """
        temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        return pathlib.Path(temp_path), temp_fd

    @staticmethod
    def cleanup_temp_file(path: pathlib.Path, logger: Optional[structlog.stdlib.BoundLogger] = None) -> None:
        """Clean up a temporary file.
        
        Args:
            path: Path to temporary file
            logger: Optional logger for debug messages
        """
        FileSystemUtils.safe_delete_file(path, logger)

    @staticmethod
    def create_temp_directory(suffix: str = "", prefix: str = "mistral_ocr_") -> pathlib.Path:
        """Create a temporary directory.
        
        Args:
            suffix: Directory suffix
            prefix: Directory prefix
            
        Returns:
            Path to temporary directory
        """
        temp_dir = tempfile.mkdtemp(suffix=suffix, prefix=prefix)
        return pathlib.Path(temp_dir)


class PathUtils:
    """Utilities for path manipulation and resolution."""

    @staticmethod
    def resolve_with_fallback(primary_path: Optional[Union[str, pathlib.Path]], 
                            fallback_path: pathlib.Path) -> pathlib.Path:
        """Resolve a path with fallback if primary is None or empty.
        
        Args:
            primary_path: Primary path to use (can be None)
            fallback_path: Fallback path if primary is unavailable
            
        Returns:
            Resolved path
        """
        if primary_path:
            return pathlib.Path(primary_path)
        return fallback_path

    @staticmethod
    def normalize_path(path: Union[str, pathlib.Path]) -> pathlib.Path:
        """Normalize a path to absolute form.
        
        Args:
            path: Path to normalize
            
        Returns:
            Normalized absolute path
        """
        return pathlib.Path(path).resolve()

    @staticmethod
    def generate_unique_filename(base_path: pathlib.Path, prefix: str = "", suffix: str = "") -> pathlib.Path:
        """Generate a unique filename by adding counter if file exists.
        
        Args:
            base_path: Base directory for the file
            prefix: Filename prefix
            suffix: Filename suffix/extension
            
        Returns:
            Unique file path
        """
        counter = 1
        while True:
            if counter == 1:
                filename = f"{prefix}{suffix}"
            else:
                name_part = prefix.rstrip('_')
                filename = f"{name_part}_{counter:03d}{suffix}"
            
            file_path = base_path / filename
            if not file_path.exists():
                return file_path
            counter += 1