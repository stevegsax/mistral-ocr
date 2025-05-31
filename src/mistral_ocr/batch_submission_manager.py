"""Batch submission management for Mistral OCR."""

import dataclasses
import json
import os
import pathlib
from typing import TYPE_CHECKING, Any, List, Optional, Union

import structlog

from .constants import (
    BATCH_FILE_PURPOSE,
    DEFAULT_OCR_MODEL,
    MAX_BATCH_SIZE,
    MOCK_FILE_ID_TEMPLATE,
    MOCK_JOB_ID_TEMPLATE,
    OCR_BATCH_ENDPOINT,
)
from .data_types import BatchFileBody, BatchFileEntry, DocumentContent
from .database import Database
from .document_manager import DocumentManager
from .exceptions import JobSubmissionError, RetryableError
from .files import FileCollector
from .progress import ProgressManager
from .utils.file_operations import FileEncodingUtils, TempFileUtils
from .utils.retry_manager import with_retry

if TYPE_CHECKING:
    from mistralai import Mistral


class BatchSubmissionManager:
    """Manages OCR batch submission operations."""

    # Mock state counters for testing
    _mock_job_sequence_number = 0
    _mock_file_sequence_number = 0

    def __init__(
        self,
        database: Database,
        api_client: Optional["Mistral"],
        document_manager: DocumentManager,
        file_collector: FileCollector,
        logger: structlog.BoundLogger,
        progress_manager: Optional[ProgressManager] = None,
        mock_mode: bool = False,
    ) -> None:
        """Initialize the batch submission manager.

        Args:
            database: Database instance for job storage
            api_client: Mistral API client instance
            document_manager: Document manager for UUID/name resolution
            file_collector: File collector for gathering files
            logger: Logger instance for logging operations
            progress_manager: Progress manager for UI updates
            mock_mode: Whether to use mock mode for testing
        """
        self.database = database
        self.client = api_client
        self.document_manager = document_manager
        self.file_collector = file_collector
        self.logger = logger
        self.progress_manager = progress_manager
        self.mock_mode = mock_mode

    def _create_file_batches(
        self, files: List[pathlib.Path], max_batch_size: int = MAX_BATCH_SIZE
    ) -> List[List[pathlib.Path]]:
        """Create batches of files for processing.

        Args:
            files: List of file paths to batch
            max_batch_size: Maximum number of files per batch

        Returns:
            List of file batches
        """
        return [files[i : i + max_batch_size] for i in range(0, len(files), max_batch_size)]

    def _submit_mock_batch(self, batch_files: List[pathlib.Path], document_uuid: str) -> str:
        """Submit a mock batch for testing.

        Args:
            batch_files: Files in the batch
            document_uuid: Document UUID for association

        Returns:
            Mock job ID
        """
        BatchSubmissionManager._mock_job_sequence_number += 1
        job_id = MOCK_JOB_ID_TEMPLATE.format(
            sequence=BatchSubmissionManager._mock_job_sequence_number
        )

        # Mock file uploads
        for file_path in batch_files:
            BatchSubmissionManager._mock_file_sequence_number += 1
            file_id = MOCK_FILE_ID_TEMPLATE.format(
                sequence=BatchSubmissionManager._mock_file_sequence_number
            )
            self.database.store_page(str(file_path), document_uuid, file_id)

        return job_id

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

    @with_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
    def _api_upload_file(self, file_path: pathlib.Path, purpose: str):
        """Upload file to API with retry logic.

        Args:
            file_path: Path to file to upload
            purpose: Purpose for the upload

        Returns:
            Upload response object from API

        Raises:
            RetryableError: For transient errors that should be retried
            Exception: For permanent errors that should not be retried
        """
        try:
            with open(file_path, "rb") as f:
                return self.client.files.upload(
                    file={"file_name": file_path.name, "content": f},
                    purpose=purpose,
                )
        except Exception as e:
            if self._is_transient_error(e):
                raise RetryableError(f"Transient error uploading file: {e}", original_error=e)
            else:
                raise

    @with_retry(max_retries=3, base_delay=1.0, max_delay=30.0)
    def _api_create_batch_job(
        self, input_file_ids: List[str], endpoint: str, model: str, metadata: dict
    ):
        """Create batch job via API with retry logic.

        Args:
            input_file_ids: List of uploaded file IDs
            endpoint: API endpoint for processing
            model: Model to use for processing
            metadata: Additional metadata for the job

        Returns:
            Batch job response object from API

        Raises:
            RetryableError: For transient errors that should be retried
            Exception: For permanent errors that should not be retried
        """
        try:
            return self.client.batch.jobs.create(
                input_files=input_file_ids,
                endpoint=endpoint,
                model=model,
                metadata=metadata,
            )
        except Exception as e:
            if self._is_transient_error(e):
                raise RetryableError(f"Transient error creating batch job: {e}", original_error=e)
            else:
                raise

    def _submit_real_batch(
        self,
        batch_files: List[pathlib.Path],
        document_uuid: str,
        model: str,
        progress_ctx: Optional[Any] = None,
    ) -> str:
        """Submit a real batch to the Mistral API.

        Args:
            batch_files: Files in the batch
            document_uuid: Document UUID for association
            model: OCR model to use
            progress_ctx: Optional progress context for tracking uploads

        Returns:
            Job ID from the API
        """
        # Create JSONL batch file
        self.logger.info(f"Creating batch file for {len(batch_files)} files")
        batch_file_path = self._create_batch_file(batch_files)

        try:
            # Upload the batch file with retry logic and progress tracking
            self.logger.info(f"Uploading batch file: {batch_file_path.name}")

            if progress_ctx:
                # Track upload progress for this batch file
                file_size = batch_file_path.stat().st_size
                progress_ctx.start_upload(batch_file_path.name, file_size)

            batch_upload = self._api_upload_file(batch_file_path, BATCH_FILE_PURPOSE)
            self.logger.info(f"Batch file uploaded with ID: {batch_upload.id}")

            if progress_ctx:
                # Complete upload tracking
                progress_ctx.complete_upload(batch_file_path.name)

            # Create batch job with retry logic
            self.logger.info(f"Creating batch job with model: {model}")
            batch_job = self._api_create_batch_job(
                input_file_ids=[batch_upload.id],
                endpoint=OCR_BATCH_ENDPOINT,
                model=model,
                metadata={"job_type": "ocr_batch"},
            )

            job_id = batch_job.id
            self.logger.info(f"Batch job created with ID: {job_id}")

            # Store page metadata
            for file_path in batch_files:
                self.database.store_page(str(file_path), document_uuid, batch_upload.id)

            return job_id

        finally:
            # Clean up temporary batch file
            TempFileUtils.cleanup_temp_file(batch_file_path, self.logger)

    def _process_single_batch(
        self,
        batch_idx: int,
        total_batches: int,
        batch_files: List[pathlib.Path],
        document_uuid: str,
        model: str,
        progress_ctx: Optional[Any] = None,
    ) -> str:
        """Process a single batch of files.

        Args:
            batch_idx: Current batch index (1-based)
            total_batches: Total number of batches
            batch_files: Files in this batch
            document_uuid: Document UUID for association
            model: OCR model to use
            progress_ctx: Optional progress context for tracking uploads

        Returns:
            Job ID for this batch

        Raises:
            RuntimeError: If batch submission fails
        """
        self.logger.info(
            f"Processing batch {batch_idx}/{total_batches} with {len(batch_files)} files"
        )

        try:
            if self.mock_mode:
                job_id = self._submit_mock_batch(batch_files, document_uuid)
            else:
                job_id = self._submit_real_batch(batch_files, document_uuid, model, progress_ctx)

            # Store job metadata
            self.database.store_job(job_id, document_uuid, "pending", len(batch_files))
            self.logger.info(f"Stored job metadata for job {job_id} with {len(batch_files)} files")

            self.logger.info(f"Created batch job {job_id} with {len(batch_files)} files")
            return job_id

        except Exception as e:
            error_msg = f"Failed to submit batch {batch_idx}/{total_batches}: {str(e)}"
            self.logger.error(error_msg)
            raise JobSubmissionError(error_msg)

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
        # Use progress tracking if available
        if self.progress_manager and self.progress_manager.enabled:
            return self._submit_documents_with_progress(
                files, recursive, document_name, document_uuid, model
            )
        else:
            return self._submit_documents_basic(
                files, recursive, document_name, document_uuid, model
            )

    def _submit_documents_basic(
        self,
        files: List[pathlib.Path],
        recursive: bool = False,
        document_name: Optional[str] = None,
        document_uuid: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Union[str, List[str]]:
        """Submit documents without progress tracking (original implementation)."""
        # Collect and validate files
        actual_files = self.file_collector.gather_valid_files_for_processing(files, recursive)

        # Handle document creation/association
        document_uuid, resolved_document_name = (
            self.document_manager.resolve_document_uuid_and_name(document_name, document_uuid)
        )

        # Create file batches
        batches = self._create_file_batches(actual_files)

        if len(batches) > 1:
            self.logger.info(f"Splitting into {len(batches)} batches (100 files max per batch)")

        ocr_model = model or DEFAULT_OCR_MODEL
        self.logger.info(f"Using OCR model: {ocr_model}")

        # Process each batch
        job_ids = []
        for batch_idx, batch_files in enumerate(batches, 1):
            job_id = self._process_single_batch(
                batch_idx, len(batches), batch_files, document_uuid, ocr_model
            )
            job_ids.append(job_id)

        # Log completion summary
        self._log_completion_summary(job_ids)

        # Return single job ID if only one batch, otherwise return list
        return job_ids[0] if len(job_ids) == 1 else job_ids

    def _submit_documents_with_progress(
        self,
        files: List[pathlib.Path],
        recursive: bool = False,
        document_name: Optional[str] = None,
        document_uuid: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Union[str, List[str]]:
        """Submit documents with progress tracking.

        This method provides real-time progress feedback through multiple phases:
        1. File collection and validation
        2. File encoding for API submission
        3. Upload progress for batch files
        4. Job creation and API response handling
        """
        # Create progress tracker with Rich UI components for terminal feedback
        tracker = self.progress_manager.create_submission_progress()

        # Collect and validate files with progress
        actual_files = self._collect_files_with_progress(files, recursive, tracker)

        # Handle document creation/association
        document_uuid, resolved_document_name = (
            self.document_manager.resolve_document_uuid_and_name(document_name, document_uuid)
        )

        # Create file batches
        batches = self._create_file_batches(actual_files)

        ocr_model = model or DEFAULT_OCR_MODEL

        # Process batches with progress tracking
        # Uses Rich context manager for automatic progress bar lifecycle management
        job_ids = []
        with tracker.track_submission(len(actual_files), len(batches)) as progress_ctx:
            # Mark file collection phase as complete (files already gathered)
            progress_ctx.complete_collection(len(actual_files))

            # Process each batch with progress updates
            # Each batch may contain up to 100 files (Mistral API limitation)
            for batch_idx, batch_files in enumerate(batches, 1):
                job_id = self._process_batch_with_progress(
                    batch_idx, len(batches), batch_files, document_uuid, ocr_model, progress_ctx
                )
                job_ids.append(job_id)
                # Update progress bar as each batch job is created
                progress_ctx.update_job_creation(batch_idx)

            # Mark all job creation as complete
            progress_ctx.complete_job_creation()

        # Log completion summary
        self._log_completion_summary(job_ids)

        # Return single job ID if only one batch, otherwise return list
        return job_ids[0] if len(job_ids) == 1 else job_ids

    def _collect_files_with_progress(
        self, files: List[pathlib.Path], recursive: bool, tracker: Any
    ) -> List[pathlib.Path]:
        """Collect files with progress feedback."""
        # For now, use the existing method - could be enhanced later
        # to provide real-time feedback during collection
        return self.file_collector.gather_valid_files_for_processing(files, recursive)

    def _process_batch_with_progress(
        self,
        batch_idx: int,
        total_batches: int,
        batch_files: List[pathlib.Path],
        document_uuid: str,
        model: str,
        progress_ctx: Any,
    ) -> str:
        """Process a single batch with progress tracking."""
        # Start encoding progress for this batch
        files_processed = 0
        for i, file_path in enumerate(batch_files, 1):
            # Update encoding progress
            progress_ctx.update_encoding(files_processed + i)

        # Mark encoding complete for this batch
        files_processed += len(batch_files)

        # Process the batch (upload + job creation)
        job_id = self._process_single_batch(
            batch_idx, total_batches, batch_files, document_uuid, model, progress_ctx
        )

        return job_id

    def _log_completion_summary(self, job_ids: List[str]) -> None:
        """Log completion summary for submitted jobs.

        Args:
            job_ids: List of job IDs that were created
        """
        if len(job_ids) == 1:
            self.logger.info(f"Document submission completed successfully. Job ID: {job_ids[0]}")
        else:
            job_list = ", ".join(job_ids)
            msg = (
                f"Document submission completed successfully. "
                f"Created {len(job_ids)} batch jobs: {job_list}"
            )
            self.logger.info(msg)

    def _create_batch_file(self, file_paths: List[pathlib.Path]) -> pathlib.Path:
        """Create a JSONL batch file for OCR processing.

        Args:
            file_paths: List of file paths to process

        Returns:
            Path to the created batch file
        """
        # Create temporary file for batch processing
        batch_file_path, temp_fd = TempFileUtils.create_temp_file(
            suffix=".jsonl", prefix="mistral_ocr_batch_"
        )
        self.logger.debug(f"Creating batch file: {batch_file_path.name}")

        try:
            successful_entries = 0
            with os.fdopen(temp_fd, "w") as f:
                for i, file_path in enumerate(file_paths):
                    self.logger.debug(f"Encoding file {i + 1}/{len(file_paths)}: {file_path.name}")
                    data_url = self._encode_file_to_data_url(file_path)
                    if data_url:
                        document_content = DocumentContent(
                            type="image_url",
                            image_url=data_url,
                        )
                        body = BatchFileBody(
                            document=document_content,
                            include_image_base64=True,
                        )
                        entry = BatchFileEntry(custom_id=file_path.name, body=body)
                        # Convert pydantic dataclass to dict for JSON serialization
                        entry_dict = dataclasses.asdict(entry)
                        f.write(json.dumps(entry_dict) + "\n")
                        successful_entries += 1
                    else:
                        self.logger.warning(f"Failed to encode file: {file_path}")

            self.logger.info(
                f"Created batch file with {successful_entries}/{len(file_paths)} entries"
            )
        except Exception as e:
            self.logger.error(f"Error creating batch file: {str(e)}")
            # Clean up on error
            TempFileUtils.cleanup_temp_file(batch_file_path, self.logger)
            raise

        return batch_file_path

    def _encode_file_to_data_url(self, file_path: pathlib.Path) -> Optional[str]:
        """Convert file to base64 data URL.

        Args:
            file_path: Path to the file to encode

        Returns:
            Base64 data URL string or None if encoding fails
        """
        try:
            return FileEncodingUtils.encode_to_data_url(file_path)
        except Exception as e:
            self.logger.error(f"Error encoding {file_path}: {e}")
            return None
