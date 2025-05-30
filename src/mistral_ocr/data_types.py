"""Type definitions for Mistral OCR data structures."""

from typing import Any, Dict, List, Optional

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass


class DictAccessMixin:
    """Mixin to provide dictionary-like access for backward compatibility."""

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style attribute access."""
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style attribute setting."""
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute with default value like dict.get()."""
        return getattr(self, key, default)


@dataclass(config=ConfigDict(extra="forbid", validate_assignment=True))
class JobInfo(DictAccessMixin):
    """Basic job information for job listings."""

    id: str
    status: str
    submitted: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    file_count: Optional[int] = None
    input_files: Optional[List[str]] = None
    output_file: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    last_api_refresh: Optional[str] = None


@dataclass(config=ConfigDict(extra="forbid"))
class JobDetails(DictAccessMixin):
    """Detailed job information including metadata."""

    id: str
    status: str
    submitted: str
    updated: str
    document_name: str
    file_count: Optional[int] = None
    last_api_refresh: Optional[str] = None
    api_response_json: Optional[str] = None
    completed: Optional[str] = None
    error: Optional[str] = None
    # API fields
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    input_files: Optional[List[str]] = None
    output_file: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass(config=ConfigDict(extra="forbid"))
class DocumentInfo:
    """Document information from database."""

    uuid: str
    name: str
    created_at: str
    downloaded: bool = False


@dataclass(config=ConfigDict(extra="forbid"))
class PageInfo:
    """Page information for file tracking."""

    id: str
    file_path: str
    document_uuid: str
    job_id: str
    uploaded_at: str


@dataclass(config=ConfigDict(extra="allow"))
class APIJobResponse(DictAccessMixin):
    """API response structure for job details."""

    id: str
    status: str
    refresh_timestamp: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    input_files: Optional[List[str]] = None
    output_file: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None
    total_requests: Optional[int] = None


@dataclass(config=ConfigDict(extra="forbid"))
class FullJobInfo:
    """Complete job information with all API fields for storage."""

    # Database fields
    id: str
    status: str
    document_uuid: str
    document_name: str
    submitted: str
    updated: str
    last_api_refresh: Optional[str] = None
    api_response_json: Optional[str] = None
    # API fields
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    file_count: Optional[int] = None
    total_requests: Optional[int] = None
    input_files: Optional[List[str]] = None
    output_file: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass(config=ConfigDict(extra="allow"))
class ConfigData:
    """Configuration file structure."""

    api_key: Optional[str] = None
    default_model: Optional[str] = None
    download_directory: Optional[str] = None
    api_timeout: Optional[str] = None
    max_retries: Optional[str] = None


@dataclass(config=ConfigDict(extra="forbid"))
class DocumentContent:
    """Document content for batch processing."""

    type: str
    image_url: str


@dataclass(config=ConfigDict(extra="forbid"))
class BatchFileBody:
    """Batch file body content."""

    document: DocumentContent
    include_image_base64: bool


@dataclass(config=ConfigDict(extra="forbid"))
class BatchFileEntry:
    """JSONL batch file entry structure."""

    custom_id: str
    body: BatchFileBody


# OCR Result Download Data Models

@dataclass(config=ConfigDict(extra="forbid"))
class OCRPage:
    """OCR result for a single page."""
    
    text: Optional[str] = None
    markdown: Optional[str] = None


@dataclass(config=ConfigDict(extra="forbid"))
class OCRResponseBody:
    """OCR API response body structure."""
    
    pages: Optional[List[OCRPage]] = None
    text: Optional[str] = None
    content: Optional[str] = None
    markdown: Optional[str] = None
    choices: Optional[List[Dict[str, Any]]] = None


@dataclass(config=ConfigDict(extra="forbid"))
class OCRApiResponse:
    """OCR API response structure."""
    
    body: OCRResponseBody
    status_code: Optional[int] = None


@dataclass(config=ConfigDict(extra="forbid"))
class BatchResultEntry:
    """Single result entry from batch JSONL output."""
    
    custom_id: str
    response: OCRApiResponse


@dataclass(config=ConfigDict(extra="forbid"))
class ProcessedOCRResult:
    """Processed OCR result ready for storage."""
    
    text: str
    markdown: str
    file_name: str
    job_id: str
    custom_id: str
