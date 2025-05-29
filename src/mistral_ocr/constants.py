"""Constants for Mistral OCR application.

This module centralizes all magic numbers and strings used throughout
the application to improve maintainability and consistency.
"""

# Batch Processing
MAX_BATCH_SIZE = 100
"""Maximum number of files that can be processed in a single batch."""

# API Configuration
DEFAULT_OCR_MODEL = "mistral-ocr-latest"
"""Default OCR model used when none is specified."""

OCR_BATCH_ENDPOINT = "/v1/ocr"
"""API endpoint for OCR batch processing."""

BATCH_FILE_PURPOSE = "batch"
"""Purpose identifier for batch file uploads."""

# Validation Limits
MIN_API_KEY_LENGTH = 10
"""Minimum acceptable length for API keys."""

DEFAULT_API_TIMEOUT_SECONDS = 300
"""Default timeout for API requests in seconds (5 minutes)."""

MAX_API_TIMEOUT_SECONDS = 3600
"""Maximum allowed timeout for API requests in seconds (1 hour)."""

DEFAULT_MAX_RETRIES = 3
"""Default maximum number of retry attempts for failed requests."""

MAX_RETRIES_LIMIT = 10
"""Maximum allowed retry limit."""

# Display Formatting
TEXT_PREVIEW_LENGTH = 200
"""Length of text preview shown in results display."""

TABLE_SEPARATOR_LENGTH = 90
"""Length of separator lines in table displays."""

JOB_ID_COLUMN_WIDTH = 36
"""Column width for job ID in table displays."""

STATUS_COLUMN_WIDTH = 12
"""Column width for status in table displays."""

SUBMITTED_COLUMN_WIDTH = 20
"""Column width for submission time in table displays."""

API_REFRESH_COLUMN_WIDTH = 20
"""Column width for API refresh timestamp in table displays."""

JSON_INDENT_SPACES = 2
"""Number of spaces for JSON indentation in pretty-printing."""

UUID_PREFIX_LENGTH = 8
"""Length of UUID prefix used in display names and identifiers."""

# Environment Variables
API_KEY_ENV_VAR = "MISTRAL_API_KEY"
"""Environment variable name for API key."""

MOCK_MODE_ENV_VAR = "MISTRAL_OCR_MOCK_MODE"
"""Environment variable name for enabling mock mode."""

# File Names
LOG_FILE_NAME = "mistral.log"
"""Name of the application log file."""

AUDIT_LOG_FILE_NAME = "audit.log"
"""Name of the audit trail log file."""

SECURITY_LOG_FILE_NAME = "security.log"
"""Name of the security events log file."""

PERFORMANCE_LOG_FILE_NAME = "performance.log"
"""Name of the performance metrics log file."""

API_LOG_FILE_NAME = "api.log"
"""Name of the API request/response log file."""

DATABASE_FILE_NAME = "mistral_ocr.db"
"""Name of the SQLite database file."""

CONFIG_FILE_NAME = "config.json"
"""Name of the configuration file."""

# Job Status Values
JOB_STATUS_PENDING = "pending"
"""Job status indicating job is queued but not yet started."""

JOB_STATUS_COMPLETED = "completed"
"""Job status indicating job has finished successfully."""

JOB_STATUS_SUCCESS = "SUCCESS"
"""API job status indicating successful completion."""

JOB_STATUS_SUCCEEDED = "SUCCEEDED"
"""Alternative API job status indicating successful completion."""

JOB_STATUS_CANCELLED = "cancelled"
"""Job status indicating job was cancelled."""

JOB_STATUS_FAILED = "FAILED"
"""Job status indicating job failed during processing."""

JOB_STATUS_RUNNING = "running"
"""Job status indicating job is currently being processed."""

# Job Status Groups
FINAL_JOB_STATUSES = {
    JOB_STATUS_SUCCESS,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_SUCCEEDED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
}
"""Set of job statuses that indicate the job has finished processing."""


# MIME Types
MIME_TYPE_PNG = "image/png"
"""MIME type for PNG image files."""

MIME_TYPE_JPEG = "image/jpeg"
"""MIME type for JPEG image files."""

MIME_TYPE_PDF = "application/pdf"
"""MIME type for PDF files."""

MIME_TYPE_OCTET_STREAM = "application/octet-stream"
"""Generic MIME type for binary files."""

# File Templates
DOCUMENT_NAME_TEMPLATE = "Document_{uuid_prefix}"
"""Template for auto-generated document names."""

MOCK_JOB_ID_TEMPLATE = "job_{sequence:03d}"
"""Template for mock job IDs in testing."""

MOCK_FILE_ID_TEMPLATE = "file_{sequence:03d}"
"""Template for mock file IDs in testing."""

SERVER_JOB_DOC_TEMPLATE = "server-job-{job_prefix}"
"""Template for server job document names."""

SERVER_JOB_NAME_TEMPLATE = "ServerJob_{job_prefix}"
"""Template for server job display names."""

# Mock Test API Key
MOCK_API_KEY = "test"
"""API key value that triggers mock mode for testing."""

# Database Schema
PRAGMA_FOREIGN_KEYS = "PRAGMA foreign_keys = ON"
"""SQL pragma to enable foreign key constraints."""

# Default Values for Settings
DEFAULT_DOWNLOAD_DIR_NAME = "downloads"
"""Default subdirectory name for downloaded results."""

# Progress and UI Configuration
DEFAULT_PROGRESS_ENABLED = True
"""Default setting for progress bar display."""

DEFAULT_PROGRESS_REFRESH_RATE = 0.5
"""Default refresh rate for progress displays in Hz."""

DEFAULT_JOB_MONITOR_INTERVAL = 10
"""Default interval for job status monitoring in seconds."""

# Logging Configuration
DEFAULT_LOG_LEVEL = "INFO"
"""Default logging level for the application."""

DEFAULT_LOG_MAX_BYTES = 50 * 1024 * 1024  # 50MB
"""Default maximum size per log file before rotation."""

DEFAULT_LOG_BACKUP_COUNT = 5
"""Default number of backup log files to keep."""

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
"""Valid logging levels."""
