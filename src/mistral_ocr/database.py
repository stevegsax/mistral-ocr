"""Database layer for Mistral OCR."""

import pathlib
import sqlite3
from typing import Any, List, Optional, Tuple


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
        self.connection.execute("PRAGMA foreign_keys = ON")

    def initialize_schema(self) -> None:
        """Initialize the database schema."""
        if not self.connection:
            raise RuntimeError("Database not connected")

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
                file_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

    def execute(self, query: str, params: Optional[Tuple] = None) -> Any:
        """Execute a SQL query and return the result.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Query result
        """
        if not self.connection:
            raise RuntimeError("Database not connected")

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
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO documents (uuid, name) 
            VALUES (?, ?)
        """,
            (uuid, name),
        )
        self.connection.commit()

    def store_job(self, job_id: str, document_uuid: str, status: str, file_count: int) -> None:
        """Store job metadata.

        Args:
            job_id: Job ID
            document_uuid: Associated document UUID
            status: Job status
            file_count: Number of files in the job
        """
        if not self.connection:
            raise RuntimeError("Database not connected")

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
            raise RuntimeError("Database not connected")

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
            raise RuntimeError("Database not connected")

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

    def get_recent_document_by_name(self, name: str) -> Optional[str]:
        """Get the most recent document UUID by name.

        Args:
            name: Document name

        Returns:
            Document UUID if found, None otherwise
        """
        if not self.connection:
            raise RuntimeError("Database not connected")

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
            raise RuntimeError("Database not connected")

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
            raise RuntimeError("Database not connected")

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

    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

