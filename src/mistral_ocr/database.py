"""Database layer for Mistral OCR."""

import json
import pathlib
import sqlite3
from typing import Any, List, Optional, Tuple

from .constants import PRAGMA_FOREIGN_KEYS
from .exceptions import DatabaseConnectionError
from .types import APIJobResponse, JobDetails, JobInfo
from .validation import require_database_connection


class Database:
    """Database connection and operations for Mistral OCR."""

    def __init__(self, db_path: pathlib.Path) -> None:
        """Initialize database with path.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Connect to the database."""
        self.connection = sqlite3.connect(str(self.db_path))
        # Enable foreign key constraints
        self.connection.execute(PRAGMA_FOREIGN_KEYS)

    @require_database_connection
    def initialize_schema(self) -> None:
        """Initialize the database schema."""
        # Database connection check is now handled by the decorator

        # Create documents table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                uuid TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create jobs table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                document_uuid TEXT NOT NULL,
                status TEXT NOT NULL,
                file_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_api_refresh TIMESTAMP,
                api_response_json TEXT,
                api_created_at TEXT,
                api_completed_at TEXT,
                total_requests INTEGER,
                input_files_json TEXT,
                output_file TEXT,
                errors_json TEXT,
                metadata_json TEXT,
                FOREIGN KEY (document_uuid) REFERENCES documents (uuid)
            )
        """)

        # Create pages table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                document_uuid TEXT NOT NULL,
                file_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_uuid) REFERENCES documents (uuid)
            )
        """)

        self.connection.commit()
        
        # Handle schema migrations for existing databases
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Handle database schema migrations for existing databases."""
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()
        
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
            ("metadata_json", "TEXT")
        ]
        
        for column_name, column_type in new_columns:
            try:
                cursor.execute(f"SELECT {column_name} FROM jobs LIMIT 1")
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                cursor.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}")
                
        # Make file_count nullable for existing databases
        try:
            cursor.execute("SELECT sql FROM sqlite_master WHERE name='jobs' AND type='table'")
            result = cursor.fetchone()
            if result and "file_count INTEGER NOT NULL" in result[0]:
                # Need to recreate table to make file_count nullable
                # This is complex in SQLite, so we'll handle it in future migration if needed
                pass
        except sqlite3.OperationalError:
            pass
            
        self.connection.commit()

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
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Commit if it's a modification query
        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE")):
            self.connection.commit()

        result = cursor.fetchone()

        # For "SELECT 1", return the single value
        if result and len(result) == 1:
            return result[0]

        return result

    def store_document(self, uuid: str, name: str) -> None:
        """Store document metadata.

        Args:
            uuid: Document UUID
            name: Document name
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO documents (uuid, name) 
            VALUES (?, ?)
        """,
            (uuid, name),
        )
        self.connection.commit()

    def store_job(self, job_id: str, document_uuid: str, status: str, file_count: Optional[int] = None) -> None:
        """Store job metadata.

        Args:
            job_id: Job ID
            document_uuid: Associated document UUID
            status: Job status
            file_count: Number of files in the job
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO jobs (job_id, document_uuid, status, file_count) 
            VALUES (?, ?, ?, ?)
        """,
            (job_id, document_uuid, status, file_count),
        )
        self.connection.commit()

    def store_page(self, file_path: str, document_uuid: str, file_id: str) -> None:
        """Store page metadata.

        Args:
            file_path: Local file path
            document_uuid: Associated document UUID
            file_id: Uploaded file ID
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO pages (file_path, document_uuid, file_id) 
            VALUES (?, ?, ?)
        """,
            (file_path, document_uuid, file_id),
        )
        self.connection.commit()

    def update_job_status(self, job_id: str, status: str) -> None:
        """Update job status.

        Args:
            job_id: Job ID
            status: New status
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            """
            UPDATE jobs 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE job_id = ?
        """,
            (status, job_id),
        )
        self.connection.commit()

    def update_job_api_refresh(self, job_id: str, status: str, api_response_json: str) -> None:
        """Update job with API refresh information.

        Args:
            job_id: Job ID
            status: New status from API
            api_response_json: Full JSON response from API
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            """
            UPDATE jobs 
            SET status = ?, updated_at = CURRENT_TIMESTAMP, 
                last_api_refresh = CURRENT_TIMESTAMP, api_response_json = ?
            WHERE job_id = ?
        """,
            (status, api_response_json, job_id),
        )
        self.connection.commit()
        
    def store_job_full_api_data(self, job_id: str, document_uuid: str, api_data: APIJobResponse) -> None:
        """Store complete job information from API response.

        Args:
            job_id: Job ID
            document_uuid: Associated document UUID
            api_data: Complete API response data
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        # Serialize lists and dicts to JSON
        input_files_json = json.dumps(api_data.get('input_files')) if api_data.get('input_files') else None
        errors_json = json.dumps(api_data.get('errors')) if api_data.get('errors') else None
        metadata_json = json.dumps(api_data.get('metadata')) if api_data.get('metadata') else None
        api_response_json = json.dumps(api_data, default=str)

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO jobs (
                job_id, document_uuid, status, file_count,
                api_created_at, api_completed_at, total_requests,
                input_files_json, output_file, errors_json, metadata_json,
                last_api_refresh, api_response_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """,
            (
                job_id, document_uuid, api_data.get('status'), 
                api_data.get('total_requests'),
                api_data.get('created_at'), api_data.get('completed_at'),
                api_data.get('total_requests'), input_files_json,
                api_data.get('output_file'), errors_json, metadata_json,
                api_response_json
            ),
        )
        self.connection.commit()
        
    def update_job_full_api_data(self, job_id: str, api_data: APIJobResponse) -> None:
        """Update existing job with complete API information.

        Args:
            job_id: Job ID
            api_data: Complete API response data
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        # Serialize lists and dicts to JSON
        input_files_json = json.dumps(api_data.get('input_files')) if api_data.get('input_files') else None
        errors_json = json.dumps(api_data.get('errors')) if api_data.get('errors') else None
        metadata_json = json.dumps(api_data.get('metadata')) if api_data.get('metadata') else None
        api_response_json = json.dumps(api_data, default=str)

        cursor = self.connection.cursor()
        cursor.execute(
            """
            UPDATE jobs 
            SET status = ?, updated_at = CURRENT_TIMESTAMP, 
                api_created_at = ?, api_completed_at = ?, total_requests = ?,
                input_files_json = ?, output_file = ?, errors_json = ?, metadata_json = ?,
                last_api_refresh = CURRENT_TIMESTAMP, api_response_json = ?
            WHERE job_id = ?
        """,
            (
                api_data.get('status'), api_data.get('created_at'), api_data.get('completed_at'),
                api_data.get('total_requests'), input_files_json, api_data.get('output_file'),
                errors_json, metadata_json, api_response_json, job_id
            ),
        )
        self.connection.commit()

    def get_recent_document_by_name(self, name: str) -> Optional[str]:
        """Get the most recent document UUID by name.

        Args:
            name: Document name

        Returns:
            Document UUID if found, None otherwise
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT uuid FROM documents 
            WHERE name = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """,
            (name,),
        )

        result = cursor.fetchone()
        return result[0] if result else None

    def get_jobs_by_document_name(self, name: str) -> List[str]:
        """Get all job IDs for a document name.

        Args:
            name: Document name

        Returns:
            List of job IDs
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT j.job_id 
            FROM jobs j 
            JOIN documents d ON j.document_uuid = d.uuid 
            WHERE d.name = ?
        """,
            (name,),
        )

        return [row[0] for row in cursor.fetchall()]

    def get_document_by_job(self, job_id: str) -> Optional[Tuple[str, str]]:
        """Get document info by job ID.

        Args:
            job_id: Job ID

        Returns:
            Tuple of (uuid, name) if found, None otherwise
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT d.uuid, d.name 
            FROM documents d 
            JOIN jobs j ON d.uuid = j.document_uuid 
            WHERE j.job_id = ?
        """,
            (job_id,),
        )

        result = cursor.fetchone()
        return (result[0], result[1]) if result else None

    def get_jobs_by_document_identifier(self, identifier: str) -> List[str]:
        """Get all job IDs for a document by name or UUID.

        Args:
            identifier: Document name or UUID

        Returns:
            List of job IDs
        """
        if not self.connection:
            raise DatabaseConnectionError("Database not connected")

        cursor = self.connection.cursor()

        # First try to find by UUID
        cursor.execute(
            """
            SELECT j.job_id 
            FROM jobs j 
            WHERE j.document_uuid = ?
        """,
            (identifier,),
        )
        results = cursor.fetchall()

        # If no results by UUID, try by name
        if not results:
            cursor.execute(
                """
                SELECT j.job_id 
                FROM jobs j 
                JOIN documents d ON j.document_uuid = d.uuid 
                WHERE d.name = ?
            """,
                (identifier,),
            )
            results = cursor.fetchall()

        return [row[0] for row in results]

    @require_database_connection
    def get_all_jobs(self) -> List[JobInfo]:
        """Get all jobs with basic status information.

        Returns:
            List of dictionaries containing job information
        """
        # Database connection check is now handled by the decorator

        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT j.job_id, j.status, j.created_at, j.api_created_at, j.api_completed_at,
                   j.total_requests, j.input_files_json, j.output_file, j.errors_json, j.metadata_json,
                   j.last_api_refresh
            FROM jobs j
            ORDER BY j.created_at DESC
        """)

        jobs: List[JobInfo] = []
        for row in cursor.fetchall():
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
                submitted=row[2],
                created_at=row[3],
                completed_at=row[4],
                file_count=row[5],
                input_files=input_files,
                output_file=row[7],
                errors=errors,
                metadata=metadata,
                last_api_refresh=row[10]
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

        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT j.job_id, j.status, j.file_count, j.created_at, j.updated_at,
                   d.name as document_name, j.last_api_refresh, j.api_response_json,
                   j.api_created_at, j.api_completed_at, j.total_requests,
                   j.input_files_json, j.output_file, j.errors_json, j.metadata_json
            FROM jobs j
            JOIN documents d ON j.document_uuid = d.uuid
            WHERE j.job_id = ?
        """,
            (job_id,),
        )

        result = cursor.fetchone()
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
            submitted=result[3],
            updated=result[4],
            document_name=result[5],
            last_api_refresh=result[6],
            api_response_json=result[7],
            completed=result[9] if result[1] in ["completed", "success"] else None,
            error=None,  # Could be extended to store error messages
            # API fields
            created_at=result[8],
            completed_at=result[9],
            input_files=input_files,
            output_file=result[12],
            errors=errors,
            metadata=metadata
        )

        return job_details

    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
