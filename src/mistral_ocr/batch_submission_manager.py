"""Batch submission management for Mistral OCR."""

import base64
import json
import mimetypes
import os
import pathlib
import tempfile
from typing import List, Optional, Union

from .database import Database
from .document_manager import DocumentManager
from .files import FileCollector
from .exceptions import JobSubmissionError


class BatchSubmissionManager:
    """Manages OCR batch submission operations."""
    
    # Mock state counters for testing
    _mock_job_sequence_number = 0
    _mock_file_sequence_number = 0
    
    def __init__(self, database: Database, api_client, document_manager: DocumentManager,
                 file_collector: FileCollector, logger, mock_mode: bool = False) -> None:
        """Initialize the batch submission manager.
        
        Args:
            database: Database instance for job storage
            api_client: Mistral API client instance
            document_manager: Document manager for UUID/name resolution
            file_collector: File collector for gathering files
            logger: Logger instance for logging operations
            mock_mode: Whether to use mock mode for testing
        """
        self.database = database
        self.client = api_client
        self.document_manager = document_manager
        self.file_collector = file_collector
        self.logger = logger
        self.mock_mode = mock_mode
    
    def _create_file_batches(self, files: List[pathlib.Path], max_batch_size: int = 100) -> List[List[pathlib.Path]]:
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
        job_id = f"job_{BatchSubmissionManager._mock_job_sequence_number:03d}"

        # Mock file uploads
        for file_path in batch_files:
            BatchSubmissionManager._mock_file_sequence_number += 1
            file_id = f"file_{BatchSubmissionManager._mock_file_sequence_number:03d}"
            self.database.store_page(str(file_path), document_uuid, file_id)
            
        return job_id
    
    def _submit_real_batch(self, batch_files: List[pathlib.Path], document_uuid: str, model: str) -> str:
        """Submit a real batch to the Mistral API.
        
        Args:
            batch_files: Files in the batch
            document_uuid: Document UUID for association
            model: OCR model to use
            
        Returns:
            Job ID from the API
        """
        # Create JSONL batch file
        self.logger.info(f"Creating batch file for {len(batch_files)} files")
        batch_file_path = self._create_batch_file(batch_files)

        try:
            # Upload the batch file
            self.logger.info(f"Uploading batch file: {batch_file_path.name}")
            with open(batch_file_path, "rb") as f:
                batch_upload = self.client.files.upload(
                    file={"file_name": batch_file_path.name, "content": f},
                    purpose="batch",
                )
            self.logger.info(f"Batch file uploaded with ID: {batch_upload.id}")

            # Create batch job
            self.logger.info(f"Creating batch job with model: {model}")
            batch_job = self.client.batch.jobs.create(
                input_files=[batch_upload.id],
                endpoint="/v1/ocr",
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
            if batch_file_path.exists():
                batch_file_path.unlink()
                self.logger.debug(
                    f"Cleaned up temporary batch file: {batch_file_path.name}"
                )
    
    def _process_single_batch(self, batch_idx: int, total_batches: int, 
                            batch_files: List[pathlib.Path], document_uuid: str, model: str) -> str:
        """Process a single batch of files.
        
        Args:
            batch_idx: Current batch index (1-based)
            total_batches: Total number of batches
            batch_files: Files in this batch
            document_uuid: Document UUID for association
            model: OCR model to use
            
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
                job_id = self._submit_real_batch(batch_files, document_uuid, model)

            # Store job metadata
            self.database.store_job(job_id, document_uuid, "pending", len(batch_files))
            self.logger.info(
                f"Stored job metadata for job {job_id} with {len(batch_files)} files"
            )

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
        # Collect and validate files
        actual_files = self.file_collector.gather_valid_files_for_processing(files, recursive)

        # Handle document creation/association
        document_uuid, resolved_document_name = self.document_manager.resolve_document_uuid_and_name(
            document_name, document_uuid
        )

        # Create file batches
        batches = self._create_file_batches(actual_files)
        
        if len(batches) > 1:
            self.logger.info(f"Splitting into {len(batches)} batches (100 files max per batch)")

        ocr_model = model or "mistral-ocr-latest"
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
        temp_fd, temp_path = tempfile.mkstemp(suffix=".jsonl", prefix="mistral_ocr_batch_")
        batch_file_path = pathlib.Path(temp_path)
        self.logger.debug(f"Creating batch file: {batch_file_path.name}")

        try:
            successful_entries = 0
            with os.fdopen(temp_fd, "w") as f:
                for i, file_path in enumerate(file_paths):
                    self.logger.debug(f"Encoding file {i + 1}/{len(file_paths)}: {file_path.name}")
                    data_url = self._encode_file_to_data_url(file_path)
                    if data_url:
                        entry = {
                            "custom_id": file_path.name,
                            "body": {
                                "document": {"type": "image_url", "image_url": data_url},
                                "include_image_base64": True,
                            },
                        }
                        f.write(json.dumps(entry) + "\n")
                        successful_entries += 1
                    else:
                        self.logger.warning(f"Failed to encode file: {file_path}")

            self.logger.info(
                f"Created batch file with {successful_entries}/{len(file_paths)} entries"
            )
        except Exception as e:
            self.logger.error(f"Error creating batch file: {str(e)}")
            # Clean up on error
            if batch_file_path.exists():
                batch_file_path.unlink()
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
            with open(file_path, "rb") as f:
                file_data = f.read()

            encoded = base64.b64encode(file_data).decode("utf-8")

            # Determine MIME type based on file extension
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                # Default MIME types for supported extensions
                ext = file_path.suffix.lower()
                if ext in {".png"}:
                    mime_type = "image/png"
                elif ext in {".jpg", ".jpeg"}:
                    mime_type = "image/jpeg"
                elif ext == ".pdf":
                    mime_type = "application/pdf"
                else:
                    mime_type = "application/octet-stream"

            return f"data:{mime_type};base64,{encoded}"

        except Exception as e:
            self.logger.error(f"Error encoding {file_path}: {e}")
            return None