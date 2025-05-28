"""
Custom exception hierarchy for the Mistral OCR application.

This module defines a structured exception hierarchy that provides clear,
specific error types for different failure scenarios in the application.
"""

from typing import Optional


class MistralOCRError(Exception):
    """Base exception for all Mistral OCR related errors."""
    
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


# Database related exceptions
class DatabaseError(MistralOCRError):
    """Base exception for database-related errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails or is not established."""
    pass


class DatabaseOperationError(DatabaseError):
    """Raised when a database operation fails."""
    pass


# File handling exceptions
class FileHandlingError(MistralOCRError):
    """Base exception for file-related errors."""
    pass


class UnsupportedFileTypeError(FileHandlingError):
    """Raised when attempting to process an unsupported file type."""
    pass


class NoValidFilesError(FileHandlingError):
    """Raised when no valid files are found for processing."""
    pass


# Job management exceptions
class JobError(MistralOCRError):
    """Base exception for job-related errors."""
    pass


class JobNotFoundError(JobError):
    """Raised when a requested job cannot be found."""
    pass


class InvalidJobIdError(JobError):
    """Raised when an invalid job ID is provided."""
    pass


class JobNotCompletedError(JobError):
    """Raised when attempting operations that require a completed job."""
    pass


class JobSubmissionError(JobError):
    """Raised when job submission to the API fails."""
    pass


# API related exceptions
class APIError(MistralOCRError):
    """Base exception for API-related errors."""
    pass


class APIConnectionError(APIError):
    """Raised when API connection fails."""
    pass


class APIResponseError(APIError):
    """Raised when API returns an unexpected response."""
    pass


# Configuration exceptions
class ConfigurationError(MistralOCRError):
    """Base exception for configuration-related errors."""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration values are invalid."""
    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""
    pass


# Document management exceptions
class DocumentError(MistralOCRError):
    """Base exception for document-related errors."""
    pass


class DocumentNotFoundError(DocumentError):
    """Raised when a requested document cannot be found."""
    pass


class DocumentCreationError(DocumentError):
    """Raised when document creation fails."""
    pass


# Result management exceptions
class ResultError(MistralOCRError):
    """Base exception for result-related errors."""
    pass


class ResultNotAvailableError(ResultError):
    """Raised when results are not available for download."""
    pass


class ResultDownloadError(ResultError):
    """Raised when result download fails."""
    pass