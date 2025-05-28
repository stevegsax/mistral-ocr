"""Mistral OCR client for API interactions."""

import os
import pathlib
from typing import List, Optional, Union

from mistralai import Mistral

from .batch_job_manager import BatchJobManager
from .batch_submission_manager import BatchSubmissionManager
from .document_manager import DocumentManager
from .files import FileCollector
from .models import OCRResult
from .parsing import OCRResultParser
from .paths import XDGPaths
from .result_manager import ResultManager
from .exceptions import MissingConfigurationError


class MistralOCRClient:
    """Client for submitting OCR jobs to the Mistral API.
    
    Acts as a facade coordinating specialized manager components.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the client with API key.

        Args:
            api_key: Mistral API key for authentication. If None, reads from MISTRAL_API_KEY.
        """
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        if not self.api_key:
            raise MissingConfigurationError(
                "API key must be provided either as parameter or "
                "MISTRAL_API_KEY environment variable"
            )

        # Use mock mode for testing
        self.mock_mode = self.api_key == "test"

        if not self.mock_mode:
            self.client = Mistral(api_key=self.api_key)
        else:
            self.client = None  # Mock client

        # Initialize logging, database, and utilities
        self._setup_logging()
        self._setup_database()
        self._setup_utilities()
        
        # Initialize specialized managers
        self._setup_managers()

    def _setup_logging(self) -> None:
        """Set up application logging."""
        from mistral_ocr.logging import get_logger, setup_logging

        log_directory = XDGPaths.get_state_dir()
        self.log_file = setup_logging(log_directory)
        self.logger = get_logger(__name__)

    def _setup_database(self) -> None:
        """Set up database connection."""
        from mistral_ocr.database import Database

        db_path = XDGPaths.get_database_path()
        self.db = Database(db_path)
        self.db.connect()
        self.db.initialize_schema()

    def _setup_utilities(self) -> None:
        """Set up utility classes."""
        self.file_collector = FileCollector(self.logger)
        self.result_parser = OCRResultParser(self.logger)
    
    def _setup_managers(self) -> None:
        """Set up specialized manager components."""
        # Document manager for UUID/name resolution
        self.document_manager = DocumentManager(self.db, self.logger)
        
        # Job management for status tracking and operations
        self.job_manager = BatchJobManager(self.db, self.client, self.logger, self.mock_mode)
        
        # Submission management for batch processing
        self.submission_manager = BatchSubmissionManager(
            self.db, self.client, self.document_manager, self.file_collector, 
            self.logger, self.mock_mode
        )
        
        # Result management for downloading and parsing
        self.result_manager = ResultManager(
            self.db, self.client, self.result_parser, self.logger, self.mock_mode
        )

    # Document management methods - delegate to DocumentManager
    def _resolve_document(
        self, document_name: Optional[str], document_uuid: Optional[str]
    ) -> tuple[str, str]:
        """Resolve document UUID and name for job association.

        Args:
            document_name: Optional document name
            document_uuid: Optional document UUID

        Returns:
            Tuple of (document_uuid, document_name)
        """
        return self.document_manager.resolve_document(document_name, document_uuid)

    # Submission management methods - delegate to BatchSubmissionManager  
    def submit_documents(
        self,
        files: List[pathlib.Path],
        recursive: bool = False,
        document_name: Optional[str] = None,
        document_uuid: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Union[str, List[str]]:
        """Submit documents for OCR processing.

        Args:
            files: List of file paths or directories to submit for OCR
            recursive: If True, process directories recursively
            document_name: Optional name to associate with the document
            document_uuid: Optional UUID to associate files with an existing document
            model: Optional custom model to use for OCR processing

        Returns:
            Job ID for tracking the submission, or list of job IDs if batch partitioning is needed

        Raises:
            FileNotFoundError: If any file or directory does not exist
            ValueError: If any file has an unsupported file type
        """
        return self.submission_manager.submit_documents(
            files, recursive, document_name, document_uuid, model
        )

    # Job management methods - delegate to BatchJobManager
    def check_job_status(self, job_id: str) -> str:
        """Check the status of a submitted job.

        Args:
            job_id: The job ID to check status for

        Returns:
            Job status (one of: pending, processing, completed, failed)

        Raises:
            ValueError: If the job ID is invalid
        """
        return self.job_manager.check_job_status(job_id)

    def query_document_status(self, document_name: str) -> List[str]:
        """Query the status of jobs associated with a document name.

        Args:
            document_name: The document name to query statuses for

        Returns:
            List of job statuses for the document
        """
        return self.job_manager.query_document_status(document_name)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a submitted job.

        Args:
            job_id: The job ID to cancel

        Returns:
            True if the job was successfully cancelled, False otherwise
        """
        return self.job_manager.cancel_job(job_id)
        
    def list_all_jobs(self) -> List[dict]:
        """List all jobs with their basic status information.

        In real mode, fetches all jobs from Mistral API, syncs missing jobs to database, 
        and updates existing jobs.
        In mock mode, uses database only.

        Filters out test jobs from the results.

        Returns:
            List of dictionaries containing job information with keys: id, status, submitted
        """
        return self.job_manager.list_all_jobs()
        
    def get_job_details(self, job_id: str) -> dict:
        """Get detailed status information for a specific job.

        In real mode, fetches live status from Mistral API and updates database.
        In mock mode, uses database only.

        Args:
            job_id: The job ID to get details for

        Returns:
            Dictionary containing detailed job information

        Raises:
            ValueError: If the job ID is not found
        """
        return self.job_manager.get_job_details(job_id)

    # Result management methods - delegate to ResultManager

    def get_results(self, job_id: str) -> List[OCRResult]:
        """Retrieve results for a completed job.

        Args:
            job_id: The job ID to retrieve results for

        Returns:
            List of OCR results for the job

        Raises:
            RuntimeError: If the job is not yet completed
        """
        return self.result_manager.get_results(job_id, self.job_manager)

    def download_results(self, job_id: str, destination: Optional[pathlib.Path] = None) -> None:
        """Download results for a completed job to a destination directory.

        Args:
            job_id: The job ID to download results for
            destination: The directory to download results to. If None, uses XDG_DATA_HOME
        """
        return self.result_manager.download_results(job_id, destination)

    def download_document_results(
        self, document_identifier: str, destination: Optional[pathlib.Path] = None
    ) -> None:
        """Download results for all jobs associated with a document.

        Args:
            document_identifier: Document name or UUID to download results for
            destination: The directory to download results to. If None, uses XDG_DATA_HOME
        """
        return self.result_manager.download_document_results(document_identifier, destination, self.job_manager)

