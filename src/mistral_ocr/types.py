"""Type definitions for Mistral OCR data structures."""

from typing import Optional, TypedDict


class JobInfo(TypedDict):
    """Basic job information for job listings."""
    id: str
    status: str
    submitted: str
    created_at: Optional[str]
    completed_at: Optional[str]
    file_count: Optional[int]
    input_files: Optional[list]
    output_file: Optional[str]
    errors: Optional[list]
    metadata: Optional[dict]


class JobDetails(TypedDict):
    """Detailed job information including metadata."""
    id: str
    status: str
    file_count: Optional[int]
    submitted: str
    updated: str
    document_name: str
    last_api_refresh: Optional[str]
    api_response_json: Optional[str]
    completed: Optional[str]
    error: Optional[str]
    # API fields
    created_at: Optional[str]
    completed_at: Optional[str]
    input_files: Optional[list]
    output_file: Optional[str]
    errors: Optional[list]
    metadata: Optional[dict]


class DocumentInfo(TypedDict):
    """Document information from database."""
    uuid: str
    name: str
    created_at: str


class PageInfo(TypedDict):
    """Page information for file tracking."""
    id: str
    file_path: str
    document_uuid: str
    job_id: str
    uploaded_at: str


class APIJobResponse(TypedDict, total=False):
    """API response structure for job details."""
    id: str
    status: str
    created_at: Optional[str]
    completed_at: Optional[str]
    metadata: Optional[dict]
    input_files: Optional[list]
    output_file: Optional[str]
    errors: Optional[list]
    total_requests: Optional[int]
    refresh_timestamp: str


class FullJobInfo(TypedDict):
    """Complete job information with all API fields for storage."""
    # Database fields
    id: str
    status: str
    document_uuid: str
    document_name: str
    submitted: str
    updated: str
    last_api_refresh: Optional[str]
    api_response_json: Optional[str]
    # API fields
    created_at: Optional[str]
    completed_at: Optional[str]
    file_count: Optional[int]
    total_requests: Optional[int]
    input_files: Optional[list]
    output_file: Optional[str]
    errors: Optional[list]
    metadata: Optional[dict]


class ConfigData(TypedDict, total=False):
    """Configuration file structure."""
    api_key: str
    default_model: str
    download_directory: str
    api_timeout: str
    max_retries: str


class DocumentContent(TypedDict):
    """Document content for batch processing."""
    type: str
    image_url: str


class BatchFileBody(TypedDict):
    """Batch file body content."""
    document: DocumentContent
    include_image_base64: bool


class BatchFileEntry(TypedDict):
    """JSONL batch file entry structure."""
    custom_id: str
    body: BatchFileBody