"""Simplified SQLAlchemy models for Mistral OCR database.

This simplified design treats batch jobs as atomic units rather than tracking
individual pages separately, reducing complexity while maintaining functionality.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Document(Base):
    """Document model for storing document metadata.
    
    A document represents a collection of files submitted together,
    identified by name or UUID. Multiple batch jobs can belong to the same document.
    """

    __tablename__ = "documents"

    uuid: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    
    # Relationships
    batch_jobs: Mapped[list["BatchJob"]] = relationship("BatchJob", back_populates="document")


class BatchJob(Base):
    """Simplified batch job model that represents the entire batch as a unit.
    
    This combines what were previously separate Job, Page, and Download records
    into a single cohesive unit. Each batch job contains:
    - Job metadata (status, timing, API response)
    - Input file information (file paths, count)
    - Output/download information (result paths, download status)
    """

    __tablename__ = "batch_jobs"

    # Primary identification
    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    document_uuid: Mapped[str] = mapped_column(String, ForeignKey("documents.uuid"), nullable=False)
    
    # Job status and metadata
    status: Mapped[str] = mapped_column(String, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    
    # API integration fields
    last_api_refresh: Mapped[Optional[datetime]] = mapped_column(DateTime)
    api_response_json: Mapped[Optional[str]] = mapped_column(Text)
    api_created_at: Mapped[Optional[str]] = mapped_column(String)
    api_completed_at: Mapped[Optional[str]] = mapped_column(String)
    total_requests: Mapped[Optional[int]] = mapped_column(Integer)
    output_file_url: Mapped[Optional[str]] = mapped_column(String)
    errors_json: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)
    
    # Input file information (stored as JSON)
    input_files_json: Mapped[Optional[str]] = mapped_column(Text)  # List of original file paths
    input_file_ids_json: Mapped[Optional[str]] = mapped_column(Text)  # List of uploaded file IDs
    
    # Output/download information
    downloaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    download_directory: Mapped[Optional[str]] = mapped_column(String)  # Local download path
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    result_count: Mapped[Optional[int]] = mapped_column(Integer)  # Number of result files
    
    # Relationships
    document: Mapped[Document] = relationship("Document", back_populates="batch_jobs")
    
    def get_input_files(self) -> list[str]:
        """Get input file paths as a list."""
        if not self.input_files_json:
            return []
        import json
        return json.loads(self.input_files_json)
    
    def set_input_files(self, files: list[str]) -> None:
        """Set input file paths from a list."""
        import json
        self.input_files_json = json.dumps(files)
    
    def get_input_file_ids(self) -> list[str]:
        """Get uploaded file IDs as a list."""
        if not self.input_file_ids_json:
            return []
        import json
        return json.loads(self.input_file_ids_json)
    
    def set_input_file_ids(self, file_ids: list[str]) -> None:
        """Set uploaded file IDs from a list."""
        import json
        self.input_file_ids_json = json.dumps(file_ids)
    
    def get_errors(self) -> list[dict]:
        """Get errors as a list of dictionaries."""
        if not self.errors_json:
            return []
        import json
        return json.loads(self.errors_json)
    
    def set_errors(self, errors: list[dict]) -> None:
        """Set errors from a list of dictionaries."""
        import json
        self.errors_json = json.dumps(errors)
    
    def get_metadata(self) -> dict:
        """Get metadata as a dictionary."""
        if not self.metadata_json:
            return {}
        import json
        return json.loads(self.metadata_json)
    
    def set_metadata(self, metadata: dict) -> None:
        """Set metadata from a dictionary."""
        import json
        self.metadata_json = json.dumps(metadata)


# Migration Notes:
# 
# The simplified schema removes these tables:
# - pages: Individual file tracking is now part of BatchJob.input_files
# - downloads: Download tracking is now part of BatchJob (downloaded, download_directory, etc.)
# 
# Benefits:
# 1. Single source of truth: All job information in one place
# 2. Atomic operations: Download/status updates affect the entire batch
# 3. Simplified queries: No complex joins needed
# 4. Better performance: Fewer tables and relationships
# 5. Easier maintenance: Less complex schema to maintain
# 
# Data Migration Strategy:
# 1. Keep existing data during transition
# 2. Add new simplified tables alongside existing ones
# 3. Migrate data from old schema to new schema
# 4. Update application code to use new schema
# 5. Remove old tables once migration is complete