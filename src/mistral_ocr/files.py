"""File handling utilities for OCR processing."""

import pathlib
from typing import List, Set

import structlog

from .exceptions import NoValidFilesError, UnsupportedFileTypeError
from .validation import validate_file_exists, validate_supported_file_type


class FileCollector:
    """Utility class for collecting and validating files for OCR processing."""

    SUPPORTED_FILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
    """Set of file extensions supported for OCR processing.
    
    Supported formats:
    - .png: Portable Network Graphics images
    - .jpg/.jpeg: JPEG images  
    - .pdf: Portable Document Format files
    """

    def __init__(self, logger: structlog.BoundLogger):
        """Initialize the file collector.

        Args:
            logger: Logger instance for reporting
        """
        self.logger = logger

    def gather_valid_files_for_processing(
        self, file_paths: List[pathlib.Path], process_directories_recursively: bool = False
    ) -> List[pathlib.Path]:
        """Collect all valid files from the given paths.

        Args:
            file_paths: List of file paths or directories to process
            process_directories_recursively: If True, process directories recursively

        Returns:
            List of valid file paths for OCR processing

        Raises:
            FileNotFoundError: If any path does not exist
            ValueError: If no valid files are found or unsupported file types are encountered
        """
        self.logger.info(f"Starting file collection for {len(file_paths)} path(s)")
        all_valid_files = []

        for current_path in file_paths:
            if not current_path.exists():
                error_msg = f"File not found: {current_path}"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            if current_path.is_dir():
                directory_files = self._collect_from_directory(current_path, process_directories_recursively)
                all_valid_files.extend(directory_files)
            elif current_path.is_file():
                self._validate_file_type(current_path)
                all_valid_files.append(current_path)
                self.logger.debug(f"Added file: {current_path}")

        if not all_valid_files:
            self.logger.error("No valid files found to process")
            raise NoValidFilesError("No valid files found to process")

        self.logger.info(f"Total files collected: {len(all_valid_files)}")
        return all_valid_files

    def _collect_from_directory(
        self, directory: pathlib.Path, process_recursively: bool
    ) -> List[pathlib.Path]:
        """Collect files from a directory.

        Args:
            directory: Directory to scan
            process_recursively: Whether to scan recursively

        Returns:
            List of valid files found in the directory
        """
        self.logger.info(f"Scanning directory: {directory} (recursive={process_recursively})")
        valid_files = []

        if process_recursively:
            file_iterator = directory.rglob("*")
        else:
            file_iterator = directory.iterdir()

        for individual_file_path in file_iterator:
            if (
                individual_file_path.is_file()
                and individual_file_path.suffix.lower() in self.SUPPORTED_FILE_EXTENSIONS
                and not individual_file_path.name.startswith(".")
            ):
                valid_files.append(individual_file_path)

        self.logger.info(f"Found {len(valid_files)} supported files in {directory}")
        return valid_files

    @validate_supported_file_type({".png", ".jpg", ".jpeg", ".pdf"})
    def _validate_file_type(self, file_path: pathlib.Path) -> None:
        """Validate that a file has a supported extension.

        Args:
            file_path: File to validate

        Raises:
            UnsupportedFileTypeError: If file type is not supported
        """
        # File type validation is now handled by the decorator
        pass

    @classmethod
    def get_supported_extensions(cls) -> Set[str]:
        """Get the set of supported file extensions.

        Returns:
            Set of supported file extensions (including the dot)
        """
        return cls.SUPPORTED_FILE_EXTENSIONS.copy()
