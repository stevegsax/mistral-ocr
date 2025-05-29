"""Mistral OCR client for API interactions."""

import pathlib
from typing import List, Optional, Union

from mistralai import Mistral

from .batch_job_manager import BatchJobManager
from .batch_submission_manager import BatchSubmissionManager
from .constants import MOCK_API_KEY
from .document_manager import DocumentManager
from .files import FileCollector
from .models import OCRResult
from .parsing import OCRResultParser
from .progress import ProgressManager
from .result_manager import ResultManager
from .settings import Settings, get_settings
from .types import JobDetails, JobInfo


class MistralOCRClient:
    """Client for submitting OCR jobs to the Mistral API.

    Acts as a facade coordinating specialized manager components.
    """

    def __init__(self, api_key: Optional[str] = None, settings: Optional[Settings] = None) -> None:
        """Initialize the client with API key and settings.

        Args:
            api_key: Mistral API key for authentication. If None, reads from settings/environment.
            settings: Settings instance to use. If None, uses global settings.
        """
        self.settings = settings or get_settings()

        # Initialize logging first for audit trails
        self._initialize_logging()

        # Get API key from parameter, settings, or environment
        if api_key:
            self.api_key = api_key
            self.security_logger.authentication_event(
                "API key provided via parameter", outcome="success"
            )
        else:
            self.api_key = self.settings.get_api_key()
            if self.api_key:
                self.security_logger.authentication_event(
                    "API key loaded from configuration/environment", outcome="success"
                )
            else:
                self.security_logger.authentication_event("No API key found", outcome="failure")

        # Use mock mode for testing
        self.mock_mode = self.api_key == MOCK_API_KEY or self.settings.is_mock_mode()

        if self.mock_mode:
            self.client = None  # Mock client
            self.security_logger.authentication_event(
                "Mock mode enabled for testing", outcome="success"
            )
        else:
            try:
                self.client = Mistral(api_key=self.api_key)
                self.security_logger.authentication_event(
                    "Mistral client initialized successfully", outcome="success"
                )
            except Exception as e:
                self.security_logger.authentication_event(
                    f"Mistral client initialization failed: {str(e)}",
                    outcome="failure",
                    validation_details={"error": str(e)},
                )
                raise

        # Initialize database and utilities
        self._initialize_database()
        self._initialize_utilities()

        # Initialize specialized managers
        self._initialize_managers()

    def _initialize_logging(self) -> None:
        """Initialize application logging."""
        from mistral_ocr.audit import get_audit_logger, get_security_logger
        from mistral_ocr.logging import get_logger, setup_logging

        log_directory = self.settings.state_directory
        self.log_file = setup_logging(log_directory, enable_console=False)
        self.logger = get_logger(__name__)
        self.audit_logger = get_audit_logger("client")
        self.security_logger = get_security_logger("client")

    def _initialize_database(self) -> None:
        """Initialize database connection."""
        from mistral_ocr.database import Database

        db_path = self.settings.database_path
        self.database = Database(db_path)
        self.database.connect()
        self.database.initialize_schema()

    def _initialize_utilities(self) -> None:
        """Initialize utility classes."""
        self.file_collector = FileCollector(self.logger)
        self.result_parser = OCRResultParser(self.logger)

    def _initialize_managers(self) -> None:
        """Initialize specialized manager components."""
        # Document manager for UUID/name resolution
        self.document_manager = DocumentManager(self.database, self.logger)

        # Progress manager for UI updates (get from settings)
        progress_enabled = self.settings.get_progress_enabled()
        self.progress_manager = ProgressManager(enabled=progress_enabled)

        # Job management for status tracking and operations
        self.job_manager = BatchJobManager(self.database, self.client, self.logger, self.mock_mode)

        # Submission management for batch processing
        self.submission_manager = BatchSubmissionManager(
            self.database,
            self.client,
            self.document_manager,
            self.file_collector,
            self.logger,
            self.progress_manager,
            self.mock_mode,
        )

        # Result management for downloading and parsing
        self.result_manager = ResultManager(
            self.database, self.client, self.result_parser, self.logger, self.mock_mode
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
        return self.document_manager.resolve_document_uuid_and_name(document_name, document_uuid)

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

    def list_all_jobs(self) -> List[JobInfo]:
        """List all jobs with their basic status information.

        In real mode, fetches all jobs from Mistral API, syncs missing jobs to database,
        and updates existing jobs.
        In mock mode, uses database only.

        Filters out test jobs from the results.

        Returns:
            List of dictionaries containing job information with keys: id, status, submitted
        """
        return self.job_manager.list_all_jobs()

    def get_job_details(self, job_id: str) -> JobDetails:
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
        return self.result_manager.download_document_results(
            document_identifier, destination, self.job_manager
        )
