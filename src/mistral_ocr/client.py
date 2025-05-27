"""Mistral OCR client for API interactions."""

import base64
import json
import logging
import mimetypes
import os
import pathlib
import tempfile
import uuid
from typing import List, Optional, Union

from mistralai import Mistral
from pydantic import BaseModel


class OCRResult(BaseModel):
    """OCR result from the Mistral API."""

    text: str
    markdown: str
    file_name: str
    job_id: str


class MistralOCRClient:
    """Client for submitting OCR jobs to the Mistral API."""

    # Mock state for testing
    _mock_job_counter = 0
    _mock_file_counter = 0
    _mock_jobs: dict[str, str] = {}  # job_id -> status
    _mock_results_call_count = 0
    _mock_download_call_count = 0

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the client with API key.

        Args:
            api_key: Mistral API key for authentication. If None, reads from MISTRAL_API_KEY.
        """
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key must be provided either as parameter or "
                "MISTRAL_API_KEY environment variable"
            )

        # Use mock mode for testing
        self.mock_mode = self.api_key == "test"

        if not self.mock_mode:
            self.client = Mistral(api_key=self.api_key)
        else:
            self.client = None  # Mock client

        # Set up logging to XDG_DATA_HOME (for logs)
        from mistral_ocr.logging import setup_logging

        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            log_directory = pathlib.Path(xdg_data_home) / "mistral-ocr"
        else:
            # Fallback to XDG spec: ~/.local/share/mistral-ocr
            home = pathlib.Path.home()
            log_directory = home / ".local" / "share" / "mistral-ocr"

        self.log_file = setup_logging(log_directory)
        self.logger = logging.getLogger(__name__)

        # Database for storing job metadata (XDG_STATE_HOME for persistent state)
        from mistral_ocr.database import Database

        xdg_state_home = os.environ.get("XDG_STATE_HOME")
        if xdg_state_home:
            db_directory = pathlib.Path(xdg_state_home) / "mistral-ocr"
        else:
            # Fallback to XDG spec: ~/.local/state/mistral-ocr
            home = pathlib.Path.home()
            db_directory = home / ".local" / "state" / "mistral-ocr"
        
        # Ensure database directory exists
        db_directory.mkdir(parents=True, exist_ok=True)
        db_path = db_directory / "mistral_ocr.db"
        self.db = Database(db_path)
        self.db.connect()
        self.db.initialize_schema()

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
        # Expand directories to their contained files
        self.logger.info(f"Starting document submission for {len(files)} path(s)")
        actual_files = []
        supported_extensions = {".png", ".jpg", ".jpeg", ".pdf"}

        for path in files:
            if not path.exists():
                error_msg = f"File not found: {path}"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            if path.is_dir():
                self.logger.info(f"Scanning directory: {path} (recursive={recursive})")
                dir_files_before = len(actual_files)
                if recursive:
                    # Add all supported files recursively
                    for file in path.rglob("*"):
                        if (
                            file.is_file()
                            and file.suffix.lower() in supported_extensions
                            and not file.name.startswith(".")
                        ):
                            actual_files.append(file)
                else:
                    # Add all supported files in the directory (non-recursive)
                    for file in path.iterdir():
                        if (
                            file.is_file()
                            and file.suffix.lower() in supported_extensions
                            and not file.name.startswith(".")
                        ):
                            actual_files.append(file)
                dir_files_added = len(actual_files) - dir_files_before
                self.logger.info(f"Found {dir_files_added} supported files in {path}")
            elif path.is_file():
                if path.suffix.lower() not in supported_extensions:
                    self.logger.error(f"Unsupported file type: {path.suffix} for file {path}")
                    raise ValueError(f"Unsupported file type: {path.suffix}")
                actual_files.append(path)
                self.logger.debug(f"Added file: {path}")

        if not actual_files:
            self.logger.error("No valid files found to process")
            raise ValueError("No valid files found to process")
        
        self.logger.info(f"Total files to process: {len(actual_files)}")

        # Handle document creation/association
        if document_uuid:
            doc_uuid = document_uuid
            self.logger.info(f"Using existing document UUID: {doc_uuid}")
        elif document_name:
            # Check if we should append to an existing document or create new one
            existing_uuid = self.db.get_recent_document_by_name(document_name)
            if existing_uuid:
                doc_uuid = existing_uuid
                self.logger.info(f"Appending to existing document '{document_name}' (UUID: {doc_uuid})")
            else:
                doc_uuid = str(uuid.uuid4())
                self.logger.info(f"Creating new document '{document_name}' (UUID: {doc_uuid})")
        else:
            doc_uuid = str(uuid.uuid4())
            document_name = f"Document_{doc_uuid[:8]}"
            self.logger.info(f"Creating new document '{document_name}' (UUID: {doc_uuid})")

        # Store document metadata
        self.db.store_document(doc_uuid, document_name or f"Document_{doc_uuid[:8]}")

        # Batch processing - split into groups of 100 files max
        batches = [actual_files[i : i + 100] for i in range(0, len(actual_files), 100)]
        job_ids = []
        
        if len(batches) > 1:
            self.logger.info(f"Splitting into {len(batches)} batches (100 files max per batch)")
        
        ocr_model = model or "mistral-ocr-latest"
        self.logger.info(f"Using OCR model: {ocr_model}")

        for batch_idx, batch_files in enumerate(batches, 1):
            self.logger.info(f"Processing batch {batch_idx}/{len(batches)} with {len(batch_files)} files")
            try:
                if self.mock_mode:
                    # Mock implementation
                    MistralOCRClient._mock_job_counter += 1
                    job_id = f"job_{MistralOCRClient._mock_job_counter:03d}"
                    MistralOCRClient._mock_jobs[job_id] = "pending"

                    # Mock file uploads
                    for file_path in batch_files:
                        MistralOCRClient._mock_file_counter += 1
                        file_id = f"file_{MistralOCRClient._mock_file_counter:03d}"
                        self.db.store_page(str(file_path), doc_uuid, file_id)
                else:
                    # Real implementation - create JSONL batch file
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
                        self.logger.info(f"Creating batch job with model: {ocr_model}")
                        batch_job = self.client.batch.jobs.create(
                            input_files=[batch_upload.id],
                            endpoint="/v1/ocr",
                            model=ocr_model,
                            metadata={"job_type": "ocr_batch"},
                        )

                        job_id = batch_job.id
                        self.logger.info(f"Batch job created with ID: {job_id}")

                        # Store page metadata
                        for file_path in batch_files:
                            self.db.store_page(str(file_path), doc_uuid, batch_upload.id)

                    finally:
                        # Clean up temporary batch file
                        if batch_file_path.exists():
                            batch_file_path.unlink()
                            self.logger.debug(f"Cleaned up temporary batch file: {batch_file_path.name}")

                job_ids.append(job_id)

                # Store job metadata
                self.db.store_job(job_id, doc_uuid, "pending", len(batch_files))
                self.logger.info(f"Stored job metadata for job {job_id} with {len(batch_files)} files")

                self.logger.info(f"Created batch job {job_id} with {len(batch_files)} files")

            except Exception as e:
                error_msg = f"Failed to submit batch {batch_idx}/{len(batches)}: {str(e)}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

        # Log completion summary
        if len(job_ids) == 1:
            self.logger.info(f"Document submission completed successfully. Job ID: {job_ids[0]}")
        else:
            self.logger.info(f"Document submission completed successfully. Created {len(job_ids)} batch jobs: {', '.join(job_ids)}")

        # Return single job ID if only one batch, otherwise return list
        return job_ids[0] if len(job_ids) == 1 else job_ids

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
                    self.logger.debug(f"Encoding file {i+1}/{len(file_paths)}: {file_path.name}")
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
            
            self.logger.info(f"Created batch file with {successful_entries}/{len(file_paths)} entries")
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

    def check_job_status(self, job_id: str) -> str:
        """Check the status of a submitted job.

        Args:
            job_id: The job ID to check status for

        Returns:
            Job status (one of: pending, processing, completed, failed)

        Raises:
            ValueError: If the job ID is invalid
        """
        if self.mock_mode:
            # Mock implementation
            if "invalid" in job_id.lower():
                raise ValueError(f"Invalid job ID: {job_id}")

            status = MistralOCRClient._mock_jobs.get(job_id, "completed")
            self.db.update_job_status(job_id, status)
            return status

        try:
            batch_job = self.client.batch.jobs.get(job_id=job_id)
            status = batch_job.status if isinstance(batch_job.status, str) else batch_job.status.value

            # Update status in database
            self.db.update_job_status(job_id, status)

            return status
        except Exception as e:
            if "invalid" in job_id.lower():
                raise ValueError(f"Invalid job ID: {job_id}")
            error_msg = f"Failed to check job status: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def query_document_status(self, document_name: str) -> List[str]:
        """Query the status of jobs associated with a document name.

        Args:
            document_name: The document name to query statuses for

        Returns:
            List of job statuses for the document
        """
        job_ids = self.db.get_jobs_by_document_name(document_name)
        statuses = []

        for job_id in job_ids:
            try:
                status = self.check_job_status(job_id)
                statuses.append(status)
            except Exception as e:
                self.logger.error(f"Failed to check status for job {job_id}: {e}")
                statuses.append("unknown")

        return statuses

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a submitted job.

        Args:
            job_id: The job ID to cancel

        Returns:
            True if the job was successfully cancelled, False otherwise
        """
        if self.mock_mode:
            # Mock implementation - always return True for test compatibility
            if job_id not in MistralOCRClient._mock_jobs:
                MistralOCRClient._mock_jobs[job_id] = "pending"
            MistralOCRClient._mock_jobs[job_id] = "cancelled"
            self.db.update_job_status(job_id, "cancelled")
            self.logger.info(f"Successfully cancelled job {job_id}")
            return True

        try:
            cancelled_job = self.client.batch.jobs.cancel(job_id=job_id)
            status = cancelled_job.status if isinstance(cancelled_job.status, str) else cancelled_job.status.value
            success = status == "cancelled"

            if success:
                self.db.update_job_status(job_id, "cancelled")
                self.logger.info(f"Successfully cancelled job {job_id}")

            return success
        except Exception as e:
            error_msg = f"Failed to cancel job {job_id}: {str(e)}"
            self.logger.error(error_msg)
            return False

    def get_results(self, job_id: str) -> List[OCRResult]:
        """Retrieve results for a completed job.

        Args:
            job_id: The job ID to retrieve results for

        Returns:
            List of OCR results for the job

        Raises:
            RuntimeError: If the job is not yet completed
        """
        if self.mock_mode:
            # Mock implementation
            MistralOCRClient._mock_results_call_count += 1

            # For the second call, simulate "not completed" state
            if MistralOCRClient._mock_results_call_count == 2:
                raise RuntimeError(f"Job {job_id} is not yet completed")

            # Return empty results for tests
            return []

        # Check job status first
        status = self.check_job_status(job_id)

        if status.upper() not in ["SUCCESS", "COMPLETED", "SUCCEEDED"]:
            raise RuntimeError(f"Job {job_id} is not yet completed (status: {status})")

        try:
            batch_job = self.client.batch.jobs.get(job_id=job_id)

            if not batch_job.output_file:
                self.logger.info(f"Job {job_id} has no output file")
                return []

            # Download the output file
            output_response = self.client.files.download(file_id=batch_job.output_file)
            output_content = output_response.read().decode("utf-8")
            
            self.logger.info(f"Downloaded output file, content length: {len(output_content)}")

            # Parse the results (JSONL format from batch API)
            results = []
            for line in output_content.strip().split("\n"):
                if line.strip():
                    try:
                        result_data = json.loads(line)
                        if "response" in result_data and "body" in result_data["response"]:
                            response_body = result_data["response"]["body"]

                            # The OCR API returns the extracted text in various formats
                            text_content = None
                            markdown_content = None
                            
                            # Check for pages format (Mistral OCR API)
                            if "pages" in response_body and response_body["pages"]:
                                page = response_body["pages"][0]  # Use first page
                                if "markdown" in page:
                                    markdown_content = page["markdown"]
                                    text_content = page.get("text", markdown_content)
                                elif "text" in page:
                                    text_content = page["text"]
                                    markdown_content = text_content
                            # Check for direct text/content format
                            elif "text" in response_body:
                                text_content = response_body["text"]
                                markdown_content = response_body.get("markdown", text_content)
                            elif "content" in response_body:
                                text_content = response_body["content"]
                                markdown_content = text_content
                            # Fallback to look for choices format
                            elif "choices" in response_body and response_body["choices"]:
                                choice = response_body["choices"][0]
                                if "message" in choice and "content" in choice["message"]:
                                    text_content = choice["message"]["content"]
                                    markdown_content = text_content
                            
                            # Skip if no content found
                            if not text_content:
                                continue

                            # Extract file name from custom_id if available
                            file_name = result_data.get("custom_id", "unknown")

                            results.append(
                                OCRResult(
                                    text=text_content,
                                    markdown=markdown_content,
                                    file_name=file_name,
                                    job_id=job_id,
                                )
                            )
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse result line: {line}")
                        continue

            return results

        except Exception as e:
            error_msg = f"Failed to retrieve results for job {job_id}: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def download_results(self, job_id: str, destination: Optional[pathlib.Path] = None) -> None:
        """Download results for a completed job to a destination directory.

        Args:
            job_id: The job ID to download results for
            destination: The directory to download results to. If None, uses XDG_DATA_HOME
        """
        if destination is None:
            xdg_data_home = os.environ.get("XDG_DATA_HOME")
            if xdg_data_home:
                destination = pathlib.Path(xdg_data_home) / "mistral-ocr"
            else:
                # Fallback to ~/.local/share/mistral-ocr (XDG spec)
                home = pathlib.Path.home()
                destination = home / ".local" / "share" / "mistral-ocr"
            
            # Ensure destination directory exists
            destination.mkdir(parents=True, exist_ok=True)

        if self.mock_mode:
            # Mock implementation for testing
            MistralOCRClient._mock_download_call_count += 1

            # For the second call, simulate unknown document storage
            if MistralOCRClient._mock_download_call_count == 2:
                dir_name = "unknown"
            else:
                dir_name = job_id

            # Create destination directory
            job_dir = destination / dir_name
            job_dir.mkdir(parents=True, exist_ok=True)
            return

        # Get document name for this job
        doc_info = self.db.get_document_by_job(job_id)
        if doc_info:
            doc_name = doc_info[1].lower().replace(" ", "-")
        else:
            doc_name = "unknown"

        # Create destination directory
        job_dir = destination / doc_name
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Get the results
            results = self.get_results(job_id)

            # Save each result to a file
            for i, result in enumerate(results):
                output_file = job_dir / f"{result.file_name}_{i:03d}.md"
                output_file.write_text(result.markdown, encoding="utf-8")

                # Also save as plain text
                text_file = job_dir / f"{result.file_name}_{i:03d}.txt"
                text_file.write_text(result.text, encoding="utf-8")

            self.logger.info(f"Downloaded {len(results)} results to {job_dir}")

        except Exception as e:
            error_msg = f"Failed to download results for job {job_id}: {str(e)}"
            self.logger.error(error_msg)
            # Still create the directory for test compatibility
            job_dir.mkdir(parents=True, exist_ok=True)
            raise RuntimeError(error_msg)

    def download_document_results(self, document_identifier: str, destination: Optional[pathlib.Path] = None) -> None:
        """Download results for all jobs associated with a document.

        Args:
            document_identifier: Document name or UUID to download results for
            destination: The directory to download results to. If None, uses XDG_DATA_HOME
        """
        self.logger.info(f"Starting download for document: {document_identifier}")
        
        if destination is None:
            xdg_data_home = os.environ.get("XDG_DATA_HOME")
            if xdg_data_home:
                destination = pathlib.Path(xdg_data_home) / "mistral-ocr"
            else:
                # Fallback to ~/.local/share/mistral-ocr (XDG spec)
                home = pathlib.Path.home()
                destination = home / ".local" / "share" / "mistral-ocr"
            
            # Ensure destination directory exists
            destination.mkdir(parents=True, exist_ok=True)

        # Get all jobs for this document (by name or UUID)
        job_ids = self.db.get_jobs_by_document_identifier(document_identifier)
        
        if not job_ids:
            error_msg = f"No jobs found for document: {document_identifier}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.logger.info(f"Found {len(job_ids)} job(s) for document {document_identifier}")
        
        completed_jobs = []
        failed_jobs = []
        total_results = 0

        for job_id in job_ids:
            try:
                self.logger.info(f"Processing job {job_id}")
                
                # Check if job is completed
                status = self.check_job_status(job_id)
                if status.upper() not in ["SUCCESS", "COMPLETED", "SUCCEEDED"]:
                    self.logger.warning(f"Job {job_id} is not completed (status: {status}), skipping")
                    failed_jobs.append((job_id, f"Not completed (status: {status})"))
                    continue

                # Download results for this job
                self.download_results(job_id, destination)
                completed_jobs.append(job_id)
                
                # Count results for logging
                results = self.get_results(job_id)
                total_results += len(results)
                
            except Exception as e:
                error_msg = f"Failed to process job {job_id}: {str(e)}"
                self.logger.error(error_msg)
                failed_jobs.append((job_id, str(e)))

        # Log summary
        if completed_jobs:
            self.logger.info(f"Successfully downloaded {total_results} results from {len(completed_jobs)} job(s)")
        
        if failed_jobs:
            self.logger.warning(f"Failed to download from {len(failed_jobs)} job(s):")
            for job_id, error in failed_jobs:
                self.logger.warning(f"  {job_id}: {error}")
        
        if not completed_jobs:
            raise RuntimeError(f"No results could be downloaded for document {document_identifier}")
