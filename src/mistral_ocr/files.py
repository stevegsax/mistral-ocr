"""File handling utilities for OCR processing."""

import logging
import pathlib
from typing import List, Set


class FileCollector:
    """Utility class for collecting and validating files for OCR processing."""

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}

    def __init__(self, logger: logging.Logger):
        """Initialize the file collector.

        Args:
            logger: Logger instance for reporting
        """
        self.logger = logger

    def collect_files(
        self, paths: List[pathlib.Path], recursive: bool = False
    ) -> List[pathlib.Path]:
        """Collect all valid files from the given paths.

        Args:
            paths: List of file paths or directories to process
            recursive: If True, process directories recursively

        Returns:
            List of valid file paths for OCR processing

        Raises:
            FileNotFoundError: If any path does not exist
            ValueError: If no valid files are found or unsupported file types are encountered
        """
        self.logger.info(f"Starting file collection for {len(paths)} path(s)")
        all_files = []

        for path in paths:
            if not path.exists():
                error_msg = f"File not found: {path}"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            if path.is_dir():
                directory_files = self._collect_from_directory(path, recursive)
                all_files.extend(directory_files)
            elif path.is_file():
                self._validate_file_type(path)
                all_files.append(path)
                self.logger.debug(f"Added file: {path}")

        if not all_files:
            self.logger.error("No valid files found to process")
            raise ValueError("No valid files found to process")

        self.logger.info(f"Total files collected: {len(all_files)}")
        return all_files

    def _collect_from_directory(
        self, directory: pathlib.Path, recursive: bool
    ) -> List[pathlib.Path]:
        """Collect files from a directory.

        Args:
            directory: Directory to scan
            recursive: Whether to scan recursively

        Returns:
            List of valid files found in the directory
        """
        self.logger.info(f"Scanning directory: {directory} (recursive={recursive})")
        files = []

        if recursive:
            file_iterator = directory.rglob("*")
        else:
            file_iterator = directory.iterdir()

        for file_path in file_iterator:
            if (
                file_path.is_file()
                and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
                and not file_path.name.startswith(".")
            ):
                files.append(file_path)

        self.logger.info(f"Found {len(files)} supported files in {directory}")
        return files

    def _validate_file_type(self, file_path: pathlib.Path) -> None:
        """Validate that a file has a supported extension.

        Args:
            file_path: File to validate

        Raises:
            ValueError: If file type is not supported
        """
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            error_msg = f"Unsupported file type: {file_path.suffix} for file {file_path}"
            self.logger.error(error_msg)
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    @classmethod
    def get_supported_extensions(cls) -> Set[str]:
        """Get the set of supported file extensions.

        Returns:
            Set of supported file extensions (including the dot)
        """
        return cls.SUPPORTED_EXTENSIONS.copy()
