"""Simplified batch management for Mistral OCR.

This combines batch submission and job management into a single simplified manager
that treats batch jobs as atomic units rather than tracking individual pages.
"""

import json
import pathlib
import uuid
from typing import TYPE_CHECKING, List, Optional

import structlog

from .async_utils import ConcurrentJobProcessor, run_async_in_sync_context
from .data_types import APIJobResponse, BatchFileEntry, JobDetails, JobInfo
from .database_simplified import SimplifiedDatabase
from .exceptions import (
    FileHandlingError,
    JobSubmissionError,
    RetryableError,
    UnsupportedFileTypeError,
)
from .files import FileCollector
from .paths import XDGPaths
from .progress import ProgressManager
from .utils.file_operations import FileEncodingUtils, FileSystemUtils, TempFileUtils
from .utils.retry_manager import with_retry

if TYPE_CHECKING:
    from mistralai import Mistral


class SimplifiedBatchManager:
    """Simplified manager that handles both batch submission and job tracking as atomic units."""

    # Mock state for testing
    _mock_batch_sequence = 0
    _mock_file_sequence = 0

    def __init__(
        self,
        database: SimplifiedDatabase,
        api_client: Optional["Mistral"],
        logger: structlog.BoundLogger,
        progress_manager: Optional[ProgressManager] = None,
        mock_mode: bool = False,
    ) -> None:
        """Initialize the simplified batch manager.

        Args:
            database: Simplified database instance
            api_client: Mistral API client instance
            logger: Logger instance
            progress_manager: Optional progress manager for UI updates
            mock_mode: Whether to use mock mode for testing
        """
        self.database = database
        self.client = api_client
        self.logger = logger
        self.progress_manager = progress_manager
        self.mock_mode = mock_mode
        self._concurrent_processor: Optional[ConcurrentJobProcessor] = None

    @property
    def concurrent_processor(self) -> ConcurrentJobProcessor:
        """Get or create the concurrent processor."""
        if self._concurrent_processor is None:
            self._concurrent_processor = ConcurrentJobProcessor(max_concurrent=5)
        return self._concurrent_processor

    def _is_transient_error(self, exception: Exception) -> bool:
        """Determine if an exception represents a transient error that should be retried."""
        error_msg = str(exception).lower()
        transient_patterns = [
            "connection",
            "timeout",
            "network",
            "temporary",
            "503",  # Service unavailable
            "502",  # Bad gateway
            "504",  # Gateway timeout
            "429",  # Rate limited
        ]
        return any(pattern in error_msg for pattern in transient_patterns)

    def submit_batch_job(
        self,
        file_paths: List[pathlib.Path],
        document_name: Optional[str] = None,
        model: str = "mistral-ocr-latest",
    ) -> str:
        """Submit a complete batch job as an atomic unit.

        Args:
            file_paths: List of file paths to process
            document_name: Optional document name for organization
            model: Model to use for OCR processing

        Returns:
            Job ID for the submitted batch

        Raises:
            JobSubmissionError: If submission fails
        """
        self.logger.info(f"Submitting batch job with {len(file_paths)} files")

        try:
            # Validate and collect files
            file_collector = FileCollector(logger=self.logger)
            valid_files = file_collector.gather_valid_files_for_processing(file_paths)

            if not valid_files:
                raise FileHandlingError("No valid files found for submission")

            # Create or get document
            document_uuid = self._get_or_create_document(document_name, valid_files)

            # Process files and create batch
            if self.mock_mode:
                job_id = self._submit_mock_batch(valid_files, document_uuid, model)
            else:
                job_id = self._submit_real_batch(valid_files, document_uuid, model)

            self.logger.info(f"Successfully submitted batch job {job_id}")
            return job_id

        except Exception as e:
            error_msg = f"Failed to submit batch job: {str(e)}"
            self.logger.error(error_msg)
            raise JobSubmissionError(error_msg)

    def _get_or_create_document(
        self, document_name: Optional[str], file_paths: List[pathlib.Path]
    ) -> str:
        """Get existing document UUID or create a new document.

        Args:
            document_name: Optional document name
            file_paths: List of file paths for generating a name if needed

        Returns:
            Document UUID
        """
        if document_name:
            # Try to find existing document by name
            existing_uuid = self.database.get_recent_document_by_name(document_name)
            if existing_uuid:
                return existing_uuid
        else:
            # Generate name from first file
            document_name = file_paths[0].stem if file_paths else "untitled"

        # Create new document
        document_uuid = str(uuid.uuid4())
        self.database.store_document(document_uuid, document_name)
        return document_uuid

    def _submit_mock_batch(
        self, file_paths: List[pathlib.Path], document_uuid: str, model: str
    ) -> str:
        """Submit a mock batch for testing."""
        SimplifiedBatchManager._mock_batch_sequence += 1
        job_id = f"batch_job_{SimplifiedBatchManager._mock_batch_sequence:04d}"

        # Generate mock file IDs
        file_ids = []
        for _ in file_paths:
            SimplifiedBatchManager._mock_file_sequence += 1
            file_ids.append(f"file_{SimplifiedBatchManager._mock_file_sequence:06d}")

        # Store batch job in database
        self.database.create_batch_job(
            job_id=job_id,
            document_uuid=document_uuid,
            input_files=[str(path) for path in file_paths],
            input_file_ids=file_ids,
            status="validating",
        )

        # Simulate status progression for mock
        self.database.update_batch_job_status(job_id, "completed")

        return job_id

    @with_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
    def _submit_real_batch(
        self, file_paths: List[pathlib.Path], document_uuid: str, model: str
    ) -> str:
        """Submit a real batch to the Mistral API."""
        try:
            # Upload files and create batch
            file_ids = []
            batch_entries = []

            # Upload all files first
            for file_path in file_paths:
                file_id = self._upload_file(file_path)
                file_ids.append(file_id)

                # Create batch entry
                batch_entry = self._create_batch_entry(file_path, file_id)
                batch_entries.append(batch_entry)

            # Create JSONL batch file
            batch_file_path = self._create_batch_file(batch_entries)

            # Submit batch to API
            batch_upload = self.client.files.upload(
                file=open(batch_file_path, "rb"),
                purpose="batch",
            )

            batch_job = self.client.batch.jobs.create(
                input_file_id=batch_upload.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={
                    "document_uuid": document_uuid,
                    "model": model,
                    "file_count": len(file_paths),
                },
            )

            # Store batch job in database
            self.database.create_batch_job(
                job_id=batch_job.id,
                document_uuid=document_uuid,
                input_files=[str(path) for path in file_paths],
                input_file_ids=file_ids,
                status=batch_job.status,
            )

            # Clean up temporary batch file
            TempFileUtils.cleanup_temp_file(batch_file_path, self.logger)

            return batch_job.id

        except Exception as e:
            if self._is_transient_error(e):
                raise RetryableError(f"Transient error submitting batch: {e}")
            raise

    @with_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
    def _upload_file(self, file_path: pathlib.Path) -> str:
        """Upload a single file to the API."""
        try:
            file_upload = self.client.files.upload(
                file=open(file_path, "rb"),
                purpose="batch",
            )
            return file_upload.id
        except Exception as e:
            if self._is_transient_error(e):
                raise RetryableError(f"Transient error uploading file {file_path}: {e}")
            raise

    def _create_batch_entry(self, file_path: pathlib.Path, file_id: str) -> BatchFileEntry:
        """Create a batch entry for a file."""
        data_url = FileEncodingUtils.encode_to_data_url(file_path)

        return BatchFileEntry(
            custom_id=file_path.name,
            body={
                "model": "mistral-ocr-latest",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this document and format it as markdown."
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url}
                            }
                        ]
                    }
                ]
            }
        )

    def _create_batch_file(self, batch_entries: List[BatchFileEntry]) -> pathlib.Path:
        """Create JSONL batch file for API submission."""
        batch_file = TempFileUtils.create_temp_file(suffix=".jsonl")

        with open(batch_file, "w", encoding="utf-8") as f:
            for entry in batch_entries:
                entry_dict = {
                    "custom_id": entry.custom_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": entry.body
                }
                f.write(json.dumps(entry_dict) + "\\n")

        return batch_file

    # Job management methods

    def refresh_batch_job_status(self, job_id: str) -> None:
        """Refresh the status of a single batch job.

        Args:
            job_id: Job ID to refresh
        """
        if self.mock_mode:
            # Mock mode - just mark as completed
            self.database.update_batch_job_status(job_id, "completed")
            return

        try:
            job_details = self.client.batch.jobs.get(job_id=job_id)
            
            # Update database with latest API data
            api_response = APIJobResponse(
                id=job_details.id,
                status=job_details.status,
                refresh_timestamp="",  # Will be set by database
                created_at=getattr(job_details, 'created_at', None),
                completed_at=getattr(job_details, 'completed_at', None),
                metadata=getattr(job_details, 'metadata', None),
                input_files=getattr(job_details, 'input_files', None),
                output_file=getattr(job_details, 'output_file', None),
                errors=getattr(job_details, 'errors', None),
                total_requests=getattr(job_details, 'total_requests', None),
            )
            
            self.database.update_batch_job_api_data(job_id, api_response)
            
        except Exception as e:
            self.logger.warning(f"Failed to refresh job {job_id}: {e}")

    def refresh_multiple_batch_jobs(self, job_ids: List[str]) -> None:
        """Refresh multiple batch job statuses concurrently.

        Args:
            job_ids: List of job IDs to refresh
        """
        if not job_ids:
            return

        self.logger.info(f"Refreshing {len(job_ids)} batch job statuses")

        async def refresh_job(job_id: str) -> None:
            self.refresh_batch_job_status(job_id)

        run_async_in_sync_context(
            self.concurrent_processor.run_concurrent_operations(
                [refresh_job(job_id) for job_id in job_ids]
            )
        )

    def get_all_batch_jobs(self) -> List[JobInfo]:
        """Get all batch jobs.

        Returns:
            List of JobInfo objects
        """
        return self.database.get_all_batch_jobs()

    def get_batch_job_details(self, job_id: str) -> Optional[JobDetails]:
        """Get detailed information for a specific batch job.

        Args:
            job_id: Job ID to get details for

        Returns:
            JobDetails object if found, None otherwise
        """
        return self.database.get_batch_job_details(job_id)

    def get_jobs_by_document_name(self, name: str) -> List[str]:
        """Get all job IDs for a document by name.

        Args:
            name: Document name to search for

        Returns:
            List of job IDs
        """
        return self.database.get_jobs_by_document_name(name)

    def get_jobs_by_document_identifier(self, identifier: str) -> List[str]:
        """Get jobs by document name or UUID.

        Args:
            identifier: Document name or UUID

        Returns:
            List of job IDs
        """
        return self.database.get_jobs_by_document_identifier(identifier)

    def cancel_batch_job(self, job_id: str) -> bool:
        """Cancel a batch job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancellation was successful, False otherwise
        """
        if self.mock_mode:
            self.database.update_batch_job_status(job_id, "cancelled")
            return True

        try:
            self.client.batch.jobs.cancel(job_id=job_id)
            self.database.update_batch_job_status(job_id, "cancelled")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    def close(self) -> None:
        """Clean up resources."""
        if self._concurrent_processor:
            self._concurrent_processor.close()
            self._concurrent_processor = None