"""Simplified Mistral OCR client with batch-centric architecture.

This simplified client eliminates the complexity of tracking individual pages
and treats batch jobs as atomic units.
"""

import pathlib
from typing import List, Optional

import structlog
from mistralai import Mistral

from .audit import get_audit_logger, AuditEventType
from .batch_manager_simplified import SimplifiedBatchManager
from .data_types import JobDetails, JobInfo
from .database_simplified import SimplifiedDatabase
from .exceptions import ConfigurationError
from .logging import get_logger
from .parsing import OCRResultParser
from .paths import XDGPaths
from .progress import ProgressManager
from .result_manager_simplified import SimplifiedResultManager
from .settings import Settings
from .validation import validate_api_key


class SimplifiedMistralOCRClient:
    """Simplified Mistral OCR client with batch-centric architecture.
    
    This client treats batch jobs as atomic units, eliminating the complexity
    of individual page tracking while maintaining all functionality.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        mock_mode: Optional[bool] = None,
        progress_enabled: Optional[bool] = None,
    ) -> None:
        """Initialize the simplified Mistral OCR client.

        Args:
            api_key: Mistral API key (if None, will try to load from settings)
            mock_mode: Enable mock mode for testing (if None, auto-detect from api_key)
            progress_enabled: Enable progress tracking (if None, use default)
        """
        # Initialize settings and paths
        self.settings = Settings()
        self.xdg_paths = XDGPaths()

        # Determine mock mode
        if mock_mode is None:
            # Auto-detect mock mode: use mock if api_key is "test" or None
            self.mock_mode = api_key == "test" or api_key is None
        else:
            self.mock_mode = mock_mode

        # Set up API key
        if not self.mock_mode:
            if api_key:
                self.api_key = api_key
            else:
                self.api_key = self.settings.get_api_key()
                if not self.api_key:
                    raise ConfigurationError(
                        "API key is required. Set it using 'config set api-key' or pass it to the constructor."
                    )
            validate_api_key(self.api_key)
        else:
            self.api_key = "test"

        # Initialize logging
        self.logger = get_logger(__name__)
        self.audit_logger = get_audit_logger("client")

        # Initialize progress manager
        if progress_enabled is None:
            progress_enabled = self.settings.get_progress_enabled()
        self.progress_manager = ProgressManager(enabled=progress_enabled)

        # Initialize API client
        if not self.mock_mode:
            self.api_client = Mistral(api_key=self.api_key)
        else:
            self.api_client = None

        # Initialize database
        db_path = self.xdg_paths.get_data_dir() / "mistral_ocr_simplified.db"
        self.database = SimplifiedDatabase(db_path)
        self.database.connect()
        self.database.initialize_schema()

        # Initialize managers
        self.result_parser = OCRResultParser(self.logger)
        
        self.batch_manager = SimplifiedBatchManager(
            database=self.database,
            api_client=self.api_client,
            logger=self.logger,
            progress_manager=self.progress_manager,
            mock_mode=self.mock_mode,
        )
        
        self.result_manager = SimplifiedResultManager(
            database=self.database,
            api_client=self.api_client,
            result_parser=self.result_parser,
            logger=self.logger,
            mock_mode=self.mock_mode,
        )

        self.audit_logger.audit(
            AuditEventType.APPLICATION_START,
            "Simplified Mistral OCR client initialized",
            mock_mode=self.mock_mode,
            progress_enabled=progress_enabled,
        )

    # Batch submission methods

    def submit_documents(
        self,
        file_paths: List[pathlib.Path],
        document_name: Optional[str] = None,
        model: str = "mistral-ocr-latest",
    ) -> str:
        """Submit documents for OCR processing as a single batch job.

        Args:
            file_paths: List of file paths to process
            document_name: Optional document name for organization
            model: Model to use for OCR processing

        Returns:
            Job ID for the submitted batch

        Example:
            client = SimplifiedMistralOCRClient()
            job_id = client.submit_documents([
                pathlib.Path("doc1.pdf"),
                pathlib.Path("doc2.png")
            ], document_name="My Documents")
        """
        self.audit_logger.audit(
            AuditEventType.FILE_SUBMISSION,
            f"Submitting batch with {len(file_paths)} files",
            document_name=document_name,
            file_count=len(file_paths),
        )

        return self.batch_manager.submit_batch_job(
            file_paths=file_paths,
            document_name=document_name,
            model=model,
        )

    # Job management methods

    def list_batch_jobs(self) -> List[JobInfo]:
        """List all batch jobs.

        Returns:
            List of JobInfo objects with batch job information
        """
        return self.batch_manager.get_all_batch_jobs()

    def get_batch_job_status(self, job_id: str) -> Optional[JobDetails]:
        """Get detailed status for a specific batch job.

        Args:
            job_id: Job ID to get status for

        Returns:
            JobDetails object if found, None otherwise
        """
        return self.batch_manager.get_batch_job_details(job_id)

    def refresh_batch_job_status(self, job_id: str) -> None:
        """Refresh the status of a batch job from the API.

        Args:
            job_id: Job ID to refresh
        """
        self.batch_manager.refresh_batch_job_status(job_id)

    def refresh_all_batch_jobs(self) -> None:
        """Refresh the status of all active batch jobs."""
        jobs = self.list_batch_jobs()
        active_jobs = [
            job.id for job in jobs 
            if job.status not in ["completed", "failed", "cancelled"]
        ]
        self.batch_manager.refresh_multiple_batch_jobs(active_jobs)

    def cancel_batch_job(self, job_id: str) -> bool:
        """Cancel a batch job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancellation was successful, False otherwise
        """
        success = self.batch_manager.cancel_batch_job(job_id)
        
        if success:
            self.audit_logger.audit(
                AuditEventType.JOB_OPERATION,
                f"Cancelled batch job {job_id}",
                job_id=job_id,
                operation="cancel",
            )
        
        return success

    # Result management methods

    def download_batch_results(
        self,
        job_id: str,
        output_directory: Optional[pathlib.Path] = None,
    ) -> pathlib.Path:
        """Download all results for a batch job.

        Args:
            job_id: Job ID to download results for
            output_directory: Optional custom output directory

        Returns:
            Path to the directory containing all downloaded files
        """
        self.audit_logger.audit(
            AuditEventType.FILE_DOWNLOAD,
            f"Downloading batch results for job {job_id}",
            job_id=job_id,
        )

        return self.result_manager.download_batch_results(job_id, output_directory)

    def is_batch_downloaded(self, job_id: str) -> bool:
        """Check if a batch job has been downloaded.

        Args:
            job_id: Job ID to check

        Returns:
            True if the batch has been downloaded, False otherwise
        """
        return self.result_manager.is_batch_downloaded(job_id)

    def get_batch_download_info(self, job_id: str) -> Optional[tuple[str, int]]:
        """Get download information for a batch job.

        Args:
            job_id: Job ID to get download info for

        Returns:
            Tuple of (download_directory, result_count) if downloaded, None otherwise
        """
        return self.result_manager.get_batch_download_info(job_id)

    def download_multiple_batches(self, job_ids: List[str]) -> List[pathlib.Path]:
        """Download multiple batch jobs concurrently.

        Args:
            job_ids: List of job IDs to download

        Returns:
            List of download directories for each batch
        """
        return self.result_manager.download_multiple_batches(job_ids)

    # Document organization methods

    def get_jobs_by_document_name(self, name: str) -> List[str]:
        """Get all job IDs for a document by name.

        Args:
            name: Document name to search for

        Returns:
            List of job IDs
        """
        return self.batch_manager.get_jobs_by_document_name(name)

    def get_jobs_by_document_identifier(self, identifier: str) -> List[str]:
        """Get jobs by document name or UUID.

        Args:
            identifier: Document name or UUID

        Returns:
            List of job IDs
        """
        return self.batch_manager.get_jobs_by_document_identifier(identifier)

    # Convenience methods for common workflows

    def submit_and_wait(
        self,
        file_paths: List[pathlib.Path],
        document_name: Optional[str] = None,
        model: str = "mistral-ocr-latest",
        download_results: bool = True,
    ) -> tuple[str, Optional[pathlib.Path]]:
        """Submit documents and wait for completion, optionally downloading results.

        Args:
            file_paths: List of file paths to process
            document_name: Optional document name for organization
            model: Model to use for OCR processing
            download_results: Whether to download results when completed

        Returns:
            Tuple of (job_id, download_path). download_path is None if download_results=False
        """
        # Submit batch
        job_id = self.submit_documents(file_paths, document_name, model)
        
        # Wait for completion (simplified - in a real implementation, 
        # this would poll the status periodically)
        self.refresh_batch_job_status(job_id)
        
        # Download results if requested
        download_path = None
        if download_results:
            job_details = self.get_batch_job_status(job_id)
            if job_details and job_details.status == "completed":
                download_path = self.download_batch_results(job_id)
        
        return job_id, download_path

    def process_directory(
        self,
        directory_path: pathlib.Path,
        document_name: Optional[str] = None,
        recursive: bool = False,
    ) -> str:
        """Process all supported files in a directory as a single batch.

        Args:
            directory_path: Directory containing files to process
            document_name: Optional document name (defaults to directory name)
            recursive: Whether to search recursively

        Returns:
            Job ID for the submitted batch
        """
        from .files import FileCollector
        
        file_collector = FileCollector(logger=self.logger)
        if recursive:
            file_paths = file_collector.gather_valid_files_for_processing([directory_path], True)
        else:
            file_paths = [
                f for f in directory_path.iterdir() 
                if f.is_file() and f.suffix.lower() in FileCollector.SUPPORTED_FILE_EXTENSIONS
            ]
        
        if not file_paths:
            raise ValueError(f"No supported files found in {directory_path}")
        
        if document_name is None:
            document_name = directory_path.name
        
        return self.submit_documents(file_paths, document_name)

    # Resource management

    def close(self) -> None:
        """Clean up resources and close connections."""
        self.batch_manager.close()
        self.result_manager.close()
        self.database.close()
        
        self.audit_logger.audit(
            AuditEventType.APPLICATION_END,
            "Simplified Mistral OCR client closed",
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    # Properties for backward compatibility

    @property
    def settings(self) -> Settings:
        """Get settings instance."""
        return self._settings

    @settings.setter
    def settings(self, value: Settings) -> None:
        """Set settings instance."""
        self._settings = value