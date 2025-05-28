"""Mistral OCR client library."""

from ._version import __version__
from .client import MistralOCRClient
from .models import OCRResult
from .settings import Settings, get_settings
from . import types
from . import constants
from .exceptions import (
    MistralOCRError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseOperationError,
    FileHandlingError,
    UnsupportedFileTypeError,
    NoValidFilesError,
    JobError,
    JobNotFoundError,
    InvalidJobIdError,
    JobNotCompletedError,
    JobSubmissionError,
    APIError,
    APIConnectionError,
    APIResponseError,
    ConfigurationError,
    InvalidConfigurationError,
    MissingConfigurationError,
    DocumentError,
    DocumentNotFoundError,
    DocumentCreationError,
    ResultError,
    ResultNotAvailableError,
    ResultDownloadError,
)

__all__ = [
    "MistralOCRClient", 
    "OCRResult", 
    "__version__",
    "Settings",
    "get_settings",
    "types",
    "constants",
    "MistralOCRError",
    "DatabaseError",
    "DatabaseConnectionError", 
    "DatabaseOperationError",
    "FileHandlingError",
    "UnsupportedFileTypeError",
    "NoValidFilesError",
    "JobError",
    "JobNotFoundError",
    "InvalidJobIdError",
    "JobNotCompletedError",
    "JobSubmissionError",
    "APIError",
    "APIConnectionError",
    "APIResponseError",
    "ConfigurationError",
    "InvalidConfigurationError",
    "MissingConfigurationError",
    "DocumentError",
    "DocumentNotFoundError",
    "DocumentCreationError",
    "ResultError",
    "ResultNotAvailableError",
    "ResultDownloadError",
]
