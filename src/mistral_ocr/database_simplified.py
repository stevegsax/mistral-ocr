"""Simplified database layer for Mistral OCR.

This simplified database design treats batch jobs as atomic units,
eliminating the complexity of individual page tracking.
"""

import json
import pathlib
from typing import Any, List, Optional, Tuple
from datetime import datetime

from sqlalchemy import create_engine, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from .db_models_simplified import Base, Document, BatchJob
from .exceptions import DatabaseConnectionError
from .data_types import APIJobResponse, JobDetails, JobInfo
from .validation import require_database_connection


class SimplifiedDatabase:
    """Simplified database connection and operations for Mistral OCR."""

    def __init__(self, db_path: pathlib.Path) -> None:
        """Initialize database with path.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session: Optional[Session] = None

    def connect(self) -> None:
        """Connect to the database."""
        self.session = self.SessionLocal()
        # Enable foreign key constraints in SQLite
        self.session.execute(text("PRAGMA foreign_keys=ON"))

    @require_database_connection
    def initialize_schema(self) -> None:
        """Initialize the simplified database schema."""
        Base.metadata.create_all(self.engine)

    def close(self) -> None:
        """Close the database connection."""
        if self.session:
            self.session.close()
            self.session = None

    # Document operations
    
    @require_database_connection
    def store_document(self, uuid: str, name: str) -> None:
        """Store document metadata.

        Args:
            uuid: Document UUID
            name: Document name
        """
        document = Document(uuid=uuid, name=name)
        self.session.merge(document)  # Use merge to handle duplicates
        self.session.commit()

    @require_database_connection
    def get_recent_document_by_name(self, name: str) -> Optional[str]:
        """Get the most recent document UUID by name.

        Args:
            name: Document name to search for

        Returns:
            Document UUID if found, None otherwise
        """
        stmt = (
            select(Document.uuid)
            .where(Document.name == name)
            .order_by(Document.created_at.desc())
            .limit(1)
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return result

    # Batch job operations

    @require_database_connection
    def create_batch_job(
        self,
        job_id: str,
        document_uuid: str,
        input_files: List[str],
        input_file_ids: List[str],
        status: str = "validating",
    ) -> None:
        """Create a new batch job with all input file information.

        Args:
            job_id: Unique job identifier
            document_uuid: Associated document UUID
            input_files: List of original file paths
            input_file_ids: List of uploaded file IDs
            status: Initial job status
        """
        batch_job = BatchJob(
            job_id=job_id,
            document_uuid=document_uuid,
            status=status,
            file_count=len(input_files),
        )
        batch_job.set_input_files(input_files)
        batch_job.set_input_file_ids(input_file_ids)
        
        self.session.add(batch_job)
        self.session.commit()

    @require_database_connection
    def update_batch_job_status(self, job_id: str, status: str) -> None:
        """Update batch job status.

        Args:
            job_id: Job ID to update
            status: New status
        """
        stmt = (
            update(BatchJob)
            .where(BatchJob.job_id == job_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        self.session.execute(stmt)
        self.session.commit()

    @require_database_connection
    def update_batch_job_api_data(self, job_id: str, api_data: APIJobResponse) -> None:
        """Update batch job with API response data.

        Args:
            job_id: Job ID to update
            api_data: API response data
        """
        update_values = {
            "status": api_data.status,
            "last_api_refresh": datetime.utcnow(),
            "api_response_json": json.dumps(api_data.__dict__),
            "updated_at": datetime.utcnow(),
        }
        
        # Add optional fields if present
        if api_data.created_at:
            update_values["api_created_at"] = api_data.created_at
        if api_data.completed_at:
            update_values["api_completed_at"] = api_data.completed_at
        if api_data.total_requests:
            update_values["total_requests"] = api_data.total_requests
        if api_data.output_file:
            update_values["output_file_url"] = api_data.output_file
        if api_data.errors:
            update_values["errors_json"] = json.dumps(api_data.errors)
        if api_data.metadata:
            update_values["metadata_json"] = json.dumps(api_data.metadata)

        stmt = update(BatchJob).where(BatchJob.job_id == job_id).values(**update_values)
        self.session.execute(stmt)
        self.session.commit()

    @require_database_connection
    def mark_batch_job_downloaded(
        self,
        job_id: str,
        download_directory: str,
        result_count: int,
    ) -> None:
        """Mark a batch job as downloaded with result information.

        Args:
            job_id: Job ID to update
            download_directory: Local directory where results were saved
            result_count: Number of result files downloaded
        """
        stmt = (
            update(BatchJob)
            .where(BatchJob.job_id == job_id)
            .values(
                downloaded=True,
                download_directory=download_directory,
                downloaded_at=datetime.utcnow(),
                result_count=result_count,
                updated_at=datetime.utcnow(),
            )
        )
        self.session.execute(stmt)
        self.session.commit()

    # Query operations

    @require_database_connection
    def get_all_batch_jobs(self) -> List[JobInfo]:
        """Get all batch jobs as JobInfo objects.

        Returns:
            List of JobInfo objects with batch job data
        """
        stmt = select(BatchJob).order_by(BatchJob.created_at.desc())
        batch_jobs = self.session.execute(stmt).scalars().all()

        job_infos = []
        for job in batch_jobs:
            job_info = JobInfo(
                id=job.job_id,
                status=job.status,
                submitted=job.created_at.isoformat() if job.created_at else "",
                created_at=job.api_created_at,
                completed_at=job.api_completed_at,
                file_count=job.file_count,
                input_files=job.get_input_files(),
                output_file=job.output_file_url,
                errors=job.get_errors(),
                metadata=job.get_metadata(),
                last_api_refresh=job.last_api_refresh.isoformat() if job.last_api_refresh else None,
            )
            job_infos.append(job_info)

        return job_infos

    @require_database_connection
    def get_batch_job_details(self, job_id: str) -> Optional[JobDetails]:
        """Get detailed information for a specific batch job.

        Args:
            job_id: Job ID to get details for

        Returns:
            JobDetails object if found, None otherwise
        """
        stmt = (
            select(BatchJob, Document.name)
            .join(Document, BatchJob.document_uuid == Document.uuid)
            .where(BatchJob.job_id == job_id)
        )
        result = self.session.execute(stmt).first()
        
        if not result:
            return None

        job, document_name = result

        return JobDetails(
            id=job.job_id,
            status=job.status,
            submitted=job.created_at.isoformat() if job.created_at else "",
            updated=job.updated_at.isoformat() if job.updated_at else "",
            document_name=document_name,
            file_count=job.file_count,
            last_api_refresh=job.last_api_refresh.isoformat() if job.last_api_refresh else None,
            api_response_json=job.api_response_json,
            completed=job.api_completed_at,
            error=json.dumps(job.get_errors()) if job.get_errors() else None,
            created_at=job.api_created_at,
            completed_at=job.api_completed_at,
            input_files=job.get_input_files(),
            output_file=job.output_file_url,
            errors=job.get_errors(),
            metadata=job.get_metadata(),
        )

    @require_database_connection
    def get_jobs_by_document_name(self, name: str) -> List[str]:
        """Get all job IDs for a document by name.

        Args:
            name: Document name to search for

        Returns:
            List of job IDs
        """
        stmt = (
            select(BatchJob.job_id)
            .join(Document, BatchJob.document_uuid == Document.uuid)
            .where(Document.name == name)
            .order_by(BatchJob.created_at.desc())
        )
        results = self.session.execute(stmt).scalars().all()
        return list(results)

    @require_database_connection
    def get_document_by_job(self, job_id: str) -> Optional[Tuple[str, str]]:
        """Get document UUID and name for a job.

        Args:
            job_id: Job ID to look up

        Returns:
            Tuple of (document_uuid, document_name) if found, None otherwise
        """
        stmt = (
            select(Document.uuid, Document.name)
            .join(BatchJob, Document.uuid == BatchJob.document_uuid)
            .where(BatchJob.job_id == job_id)
        )
        result = self.session.execute(stmt).first()
        return result if result else None

    @require_database_connection
    def get_jobs_by_document_identifier(self, identifier: str) -> List[str]:
        """Get jobs by document name or UUID.

        Args:
            identifier: Document name or UUID

        Returns:
            List of job IDs
        """
        # Try as UUID first, then as name
        stmt = (
            select(BatchJob.job_id)
            .join(Document, BatchJob.document_uuid == Document.uuid)
            .where((Document.uuid == identifier) | (Document.name == identifier))
            .order_by(BatchJob.created_at.desc())
        )
        results = self.session.execute(stmt).scalars().all()
        return list(results)

    @require_database_connection
    def is_batch_job_downloaded(self, job_id: str) -> bool:
        """Check if a batch job has been downloaded.

        Args:
            job_id: Job ID to check

        Returns:
            True if downloaded, False otherwise
        """
        stmt = select(BatchJob.downloaded).where(BatchJob.job_id == job_id)
        result = self.session.execute(stmt).scalar_one_or_none()
        return bool(result) if result is not None else False

    @require_database_connection
    def get_batch_job_download_info(self, job_id: str) -> Optional[Tuple[str, int]]:
        """Get download information for a batch job.

        Args:
            job_id: Job ID to get download info for

        Returns:
            Tuple of (download_directory, result_count) if downloaded, None otherwise
        """
        stmt = (
            select(BatchJob.download_directory, BatchJob.result_count)
            .where(BatchJob.job_id == job_id)
            .where(BatchJob.downloaded == True)
        )
        result = self.session.execute(stmt).first()
        return result if result else None


# Migration utilities for transitioning from the old schema

class DatabaseMigrator:
    """Utility class for migrating from the old complex schema to the simplified one."""
    
    def __init__(self, old_db_path: pathlib.Path, new_db_path: pathlib.Path):
        """Initialize migrator with old and new database paths."""
        self.old_db_path = old_db_path
        self.new_db_path = new_db_path
    
    def migrate_data(self) -> None:
        """Migrate data from old schema to new simplified schema."""
        # This would implement the actual migration logic
        # For now, we'll create the new database alongside the old one
        # and gradually transition the application to use it
        pass