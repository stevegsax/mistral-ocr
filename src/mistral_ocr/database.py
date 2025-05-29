"""Database layer for Mistral OCR."""

import json
import pathlib
from typing import Any, List, Optional, Tuple

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from .db_models import Base, Document, Job, Page, Download
from .exceptions import DatabaseConnectionError
from .data_types import APIJobResponse, JobDetails, JobInfo
from .validation import require_database_connection


class Database:
    """Database connection and operations for Mistral OCR."""

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
        """Initialize the database schema."""
        # Create all tables using SQLAlchemy
        Base.metadata.create_all(self.engine)

        # Handle schema migrations for existing databases
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Handle database schema migrations for existing databases."""
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        # List of new columns to add with their SQL types
        new_columns = [
            ("last_api_refresh", "TIMESTAMP"),
            ("api_response_json", "TEXT"),
            ("api_created_at", "TEXT"),
            ("api_completed_at", "TEXT"),
            ("total_requests", "INTEGER"),
            ("input_files_json", "TEXT"),
            ("output_file", "TEXT"),
            ("errors_json", "TEXT"),
            ("metadata_json", "TEXT"),
        ]

        for column_name, column_type in new_columns:
            try:
                self.session.execute(text(f"SELECT {column_name} FROM jobs LIMIT 1"))
            except Exception:
                # Column doesn't exist, add it
                self.session.execute(
                    text(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}")
                )

        # Add downloaded column to documents table if it doesn't exist
        try:
            self.session.execute(text("SELECT downloaded FROM documents LIMIT 1"))
        except Exception:
            # Column doesn't exist, add it
            self.session.execute(
                text("ALTER TABLE documents ADD COLUMN downloaded BOOLEAN DEFAULT FALSE")
            )

        self.session.commit()

    def execute(self, query: str, params: Optional[Tuple] = None) -> Any:
        """Execute a SQL query and return the result.

        Args:
            query: SQL query to execute
            params: Optional query parameters for parameterized queries

        Returns:
            Query result (cursor for SELECT queries, None for other operations)

        Raises:
            DatabaseConnectionError: If database connection is not established
            DatabaseOperationError: If SQL execution fails
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        if params:
            result = self.session.execute(text(query), params)
        else:
            result = self.session.execute(text(query))

        # Commit if it's a modification query
        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE")):
            self.session.commit()
            return None

        # Only try to fetch results for SELECT queries
        if query.strip().upper().startswith("SELECT"):
            row = result.fetchone()
            # For "SELECT 1", return the single value
            if row and len(row) == 1:
                return row[0]
            return row

        return None

    def store_document(self, uuid: str, name: str) -> None:
        """Store document metadata.

        Args:
            uuid: Document UUID
            name: Document name
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        # Check if document already exists
        existing_doc = self.session.get(Document, uuid)

        if existing_doc:
            # Update name if document already exists (but preserve downloaded status)
            existing_doc.name = name
        else:
            # Create new document
            new_doc = Document(uuid=uuid, name=name, downloaded=False)
            self.session.add(new_doc)

        self.session.commit()

    @require_database_connection
    def mark_document_downloaded(self, document_uuid: str) -> None:
        """Mark a document as downloaded.

        Args:
            document_uuid: Document UUID to mark as downloaded
        """
        document = self.session.get(Document, document_uuid)
        if document:
            document.downloaded = True
            self.session.commit()

    def store_job(
        self, job_id: str, document_uuid: str, status: str, file_count: Optional[int] = None
    ) -> None:
        """Store job metadata.

        Args:
            job_id: Job ID
            document_uuid: Associated document UUID
            status: Job status
            file_count: Number of files in the job
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        # Check if job already exists
        existing_job = self.session.get(Job, job_id)

        if existing_job:
            # Update existing job
            existing_job.status = status
            existing_job.file_count = file_count
        else:
            # Create new job
            new_job = Job(
                job_id=job_id, document_uuid=document_uuid, status=status, file_count=file_count
            )
            self.session.add(new_job)

        self.session.commit()

    def store_page(self, file_path: str, document_uuid: str, file_id: str) -> None:
        """Store page metadata.

        Args:
            file_path: Local file path
            document_uuid: Associated document UUID
            file_id: Uploaded file ID
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        new_page = Page(file_path=file_path, document_uuid=document_uuid, file_id=file_id)
        self.session.add(new_page)
        self.session.commit()

    def store_download(
        self,
        text_path: str,
        markdown_path: str,
        document_uuid: str,
        job_id: str,
        document_order: int,
    ) -> None:
        """Store downloaded file paths."""
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        download = Download(
            text_path=text_path,
            markdown_path=markdown_path,
            document_uuid=document_uuid,
            job_id=job_id,
            document_order=document_order,
        )
        self.session.add(download)
        self.session.commit()

    def update_job_status(self, job_id: str, status: str) -> None:
        """Update job status.

        Args:
            job_id: Job ID
            status: New status
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        job = self.session.get(Job, job_id)
        if job:
            job.status = status
            from datetime import datetime

            job.updated_at = datetime.now()
            self.session.commit()

    def update_job_api_refresh(self, job_id: str, status: str, api_response_json: str) -> None:
        """Update job with API refresh information.

        Args:
            job_id: Job ID
            status: New status from API
            api_response_json: Full JSON response from API
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        job = self.session.get(Job, job_id)
        if job:
            job.status = status
            from datetime import datetime

            job.updated_at = datetime.now()
            job.last_api_refresh = datetime.now()
            job.api_response_json = api_response_json
            self.session.commit()

    def store_job_full_api_data(
        self, job_id: str, document_uuid: str, api_data: APIJobResponse
    ) -> None:
        """Store complete job information from API response.

        Args:
            job_id: Job ID
            document_uuid: Associated document UUID
            api_data: Complete API response data
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        # Serialize lists and dicts to JSON
        input_files_json = (
            json.dumps(api_data.get("input_files")) if api_data.get("input_files") else None
        )
        errors_json = json.dumps(api_data.get("errors")) if api_data.get("errors") else None
        metadata_json = json.dumps(api_data.get("metadata")) if api_data.get("metadata") else None
        api_response_json = json.dumps(api_data, default=str)

        # Check if job already exists
        existing_job = self.session.get(Job, job_id)

        if existing_job:
            # Update existing job
            existing_job.document_uuid = document_uuid
            existing_job.status = api_data.get("status")
            existing_job.file_count = api_data.get("total_requests")
            existing_job.api_created_at = api_data.get("created_at")
            existing_job.api_completed_at = api_data.get("completed_at")
            existing_job.total_requests = api_data.get("total_requests")
            existing_job.input_files_json = input_files_json
            existing_job.output_file = api_data.get("output_file")
            existing_job.errors_json = errors_json
            existing_job.metadata_json = metadata_json
            existing_job.api_response_json = api_response_json
            from datetime import datetime

            existing_job.last_api_refresh = datetime.now()
        else:
            # Create new job
            new_job = Job(
                job_id=job_id,
                document_uuid=document_uuid,
                status=api_data.get("status"),
                file_count=api_data.get("total_requests"),
                api_created_at=api_data.get("created_at"),
                api_completed_at=api_data.get("completed_at"),
                total_requests=api_data.get("total_requests"),
                input_files_json=input_files_json,
                output_file=api_data.get("output_file"),
                errors_json=errors_json,
                metadata_json=metadata_json,
                api_response_json=api_response_json,
            )
            from datetime import datetime

            new_job.last_api_refresh = datetime.now()
            self.session.add(new_job)

        self.session.commit()

    def update_job_full_api_data(self, job_id: str, api_data: APIJobResponse) -> None:
        """Update existing job with complete API information.

        Args:
            job_id: Job ID
            api_data: Complete API response data
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        # Serialize lists and dicts to JSON
        input_files_json = (
            json.dumps(api_data.get("input_files")) if api_data.get("input_files") else None
        )
        errors_json = json.dumps(api_data.get("errors")) if api_data.get("errors") else None
        metadata_json = json.dumps(api_data.get("metadata")) if api_data.get("metadata") else None
        api_response_json = json.dumps(api_data, default=str)

        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        job = self.session.get(Job, job_id)
        if job:
            job.status = api_data.get("status")
            from datetime import datetime

            job.updated_at = datetime.now()
            job.api_created_at = api_data.get("created_at")
            job.api_completed_at = api_data.get("completed_at")
            job.total_requests = api_data.get("total_requests")
            job.input_files_json = input_files_json
            job.output_file = api_data.get("output_file")
            job.errors_json = errors_json
            job.metadata_json = metadata_json
            job.last_api_refresh = datetime.now()
            job.api_response_json = api_response_json
            self.session.commit()

    def get_recent_document_by_name(self, name: str) -> Optional[str]:
        """Get the most recent document UUID by name.

        Args:
            name: Document name

        Returns:
            Document UUID if found, None otherwise
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        stmt = (
            select(Document.uuid)
            .where(Document.name == name)
            .order_by(Document.created_at.desc())
            .limit(1)
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return result

    def get_jobs_by_document_name(self, name: str) -> List[str]:
        """Get all job IDs for a document name.

        Args:
            name: Document name

        Returns:
            List of job IDs
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        stmt = select(Job.job_id).join(Document).where(Document.name == name)
        result = self.session.execute(stmt)
        return [row[0] for row in result.fetchall()]

    def get_document_by_job(self, job_id: str) -> Optional[Tuple[str, str]]:
        """Get document info by job ID.

        Args:
            job_id: Job ID

        Returns:
            Tuple of (uuid, name) if found, None otherwise
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        stmt = select(Document.uuid, Document.name).join(Job).where(Job.job_id == job_id)
        result = self.session.execute(stmt).first()
        return (result[0], result[1]) if result else None

    def get_jobs_by_document_identifier(self, identifier: str) -> List[str]:
        """Get all job IDs for a document by name or UUID.

        Args:
            identifier: Document name or UUID

        Returns:
            List of job IDs
        """
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        # First try to find by UUID
        stmt = select(Job.job_id).where(Job.document_uuid == identifier)
        result = self.session.execute(stmt)
        results = [row[0] for row in result.fetchall()]

        # If no results by UUID, try by name
        if not results:
            stmt = select(Job.job_id).join(Document).where(Document.name == identifier)
            result = self.session.execute(stmt)
            results = [row[0] for row in result.fetchall()]

        return results

    @require_database_connection
    def get_all_jobs(self) -> List[JobInfo]:
        """Get all jobs with basic status information.

        Returns:
            List of dictionaries containing job information
        """
        # Database connection check is now handled by the decorator
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        stmt = select(
            Job.job_id,
            Job.status,
            Job.created_at,
            Job.api_created_at,
            Job.api_completed_at,
            Job.total_requests,
            Job.input_files_json,
            Job.output_file,
            Job.errors_json,
            Job.metadata_json,
            Job.last_api_refresh,
        ).order_by(Job.created_at.desc())
        result = self.session.execute(stmt)

        jobs: List[JobInfo] = []
        for row in result.fetchall():
            # Parse JSON fields safely
            try:
                input_files = json.loads(row[6]) if row[6] else None
            except (json.JSONDecodeError, TypeError):
                input_files = None

            try:
                errors = json.loads(row[8]) if row[8] else None
            except (json.JSONDecodeError, TypeError):
                errors = None

            try:
                metadata = json.loads(row[9]) if row[9] else None
            except (json.JSONDecodeError, TypeError):
                metadata = None

            job_info = JobInfo(
                id=row[0],
                status=row[1],
                submitted=row[2].isoformat() if row[2] else None,
                created_at=row[3],
                completed_at=row[4],
                file_count=row[5],
                input_files=input_files,
                output_file=row[7],
                errors=errors,
                metadata=metadata,
                last_api_refresh=row[10].isoformat() if row[10] else None,
            )
            jobs.append(job_info)

        return jobs

    @require_database_connection
    def get_job_details(self, job_id: str) -> Optional[JobDetails]:
        """Get detailed information for a specific job.

        Args:
            job_id: Job_ID to get details for

        Returns:
            Dictionary containing detailed job information, or None if not found
        """
        # Database connection check is now handled by the decorator
        if not self.session:
            raise DatabaseConnectionError("Database not connected")

        stmt = (
            select(
                Job.job_id,
                Job.status,
                Job.file_count,
                Job.created_at,
                Job.updated_at,
                Document.name.label("document_name"),
                Job.last_api_refresh,
                Job.api_response_json,
                Job.api_created_at,
                Job.api_completed_at,
                Job.total_requests,
                Job.input_files_json,
                Job.output_file,
                Job.errors_json,
                Job.metadata_json,
            )
            .join(Document)
            .where(Job.job_id == job_id)
        )
        result = self.session.execute(stmt).first()

        if not result:
            return None

        # Parse JSON fields safely
        try:
            input_files = json.loads(result[11]) if result[11] else None
        except (json.JSONDecodeError, TypeError):
            input_files = None

        try:
            errors = json.loads(result[13]) if result[13] else None
        except (json.JSONDecodeError, TypeError):
            errors = None

        try:
            metadata = json.loads(result[14]) if result[14] else None
        except (json.JSONDecodeError, TypeError):
            metadata = None

        job_details = JobDetails(
            id=result[0],
            status=result[1],
            file_count=result[2] or result[10],  # Use total_requests if file_count is None
            submitted=result[3].isoformat() if result[3] else None,
            updated=result[4].isoformat() if result[4] else None,
            document_name=result[5],
            last_api_refresh=result[6].isoformat() if result[6] else None,
            api_response_json=result[7],
            completed=result[9] if result[1] in ["completed", "success"] else None,
            error=None,  # Could be extended to store error messages
            # API fields
            created_at=result[8],
            completed_at=result[9],
            input_files=input_files,
            output_file=result[12],
            errors=errors,
            metadata=metadata,
        )

        return job_details

    def close(self) -> None:
        """Close the database connection."""
        if self.session:
            self.session.close()
            self.session = None
