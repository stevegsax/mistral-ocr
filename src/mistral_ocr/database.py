"""Database layer for Mistral OCR."""

import pathlib
import sqlite3
from typing import Any, Optional


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

    def execute(self, query: str) -> Any:
        """Execute a SQL query and return the result.

        Args:
            query: SQL query to execute

        Returns:
            Query result
        """
        if not self.connection:
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(query)
        result = cursor.fetchone()

        # For "SELECT 1", return the single value
        if result and len(result) == 1:
            return result[0]

        return result
