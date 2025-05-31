"""Simplified result management for Mistral OCR.

This simplified result manager treats batch jobs as atomic units,
eliminating the complexity of tracking individual pages separately.
"""

import pathlib
from typing import TYPE_CHECKING, List, Optional

import structlog

from .async_utils import ConcurrentJobProcessor, run_async_in_sync_context
from .data_types import ProcessedOCRResult, ProcessedOCRFile, ProcessedOCRFileType
from .database_simplified import SimplifiedDatabase
from .exceptions import (
    JobNotCompletedError,
    ResultDownloadError,
    ResultNotAvailableError,
    RetryableError,
)
from .models import OCRResult
from .parsing import OCRResultParser
from .paths import XDGPaths
from .utils.file_operations import FileIOUtils, FileSystemUtils
from .utils.retry_manager import with_retry

if TYPE_CHECKING:
    from mistralai import Mistral


class SimplifiedResultManager:
    """Simplified result manager that handles batch jobs as atomic units."""

    # Mock state counters for testing
    _mock_download_count = 0

    def __init__(
        self,
        database: SimplifiedDatabase,
        api_client: Optional["Mistral"],
        result_parser: OCRResultParser,
        logger: structlog.BoundLogger,
        mock_mode: bool = False,
    ) -> None:
        """Initialize the simplified result manager.

        Args:
            database: Simplified database instance for job storage
            api_client: Mistral API client instance
            result_parser: OCR result parser instance
            logger: Logger instance for logging operations
            mock_mode: Whether to use mock mode for testing
        """
        self.database = database
        self.client = api_client
        self.result_parser = result_parser
        self.logger = logger
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

    @with_retry(max_retries=3, base_delay=1.0, max_delay=30.0)
    def _api_get_job_details(self, job_id: str):
        """Get job details from API with retry logic."""
        if self.mock_mode:
            return self._mock_job_details(job_id)
        
        try:
            return self.client.batch.jobs.get(job_id=job_id)
        except Exception as e:
            if self._is_transient_error(e):
                raise RetryableError(f"API error getting job details: {e}")
            raise

    @with_retry(max_retries=3, base_delay=1.0, max_delay=30.0)
    def _api_download_results(self, job_id: str) -> str:
        """Download job results from API with retry logic."""
        if self.mock_mode:
            return self._mock_download_results(job_id)
        
        try:
            response = self.client.files.download(file_id=job_id)
            return response.content.decode('utf-8')
        except Exception as e:
            if self._is_transient_error(e):
                raise RetryableError(f"API error downloading results: {e}")
            raise

    def _mock_job_details(self, job_id: str):
        """Mock job details for testing."""
        return type('MockJobDetails', (), {
            'id': job_id,
            'status': 'completed',
            'output_file': f"output_{job_id}.jsonl"
        })()

    def _mock_download_results(self, job_id: str) -> str:
        """Mock download results for testing."""
        SimplifiedResultManager._mock_download_count += 1
        
        # Generate mock JSONL content with multiple results
        mock_results = []
        for i in range(3):  # Mock 3 pages
            result = {
                "custom_id": f"file_{i:03d}",
                "response": {
                    "body": {
                        "pages": [{
                            "text": f"Mock text content for page {i+1}",
                            "markdown": f"# Page {i+1}\n\nMock **markdown** content for page {i+1}"
                        }]
                    },
                    "status_code": 200
                }
            }
            mock_results.append(result)
        
        return '\n'.join(f'{{"custom_id": "{r["custom_id"]}", "response": {r["response"]}}}' 
                        for r in mock_results)

    def get_batch_results(self, job_id: str) -> List[OCRResult]:
        """Get results for a completed batch job.

        Args:
            job_id: Job ID to get results for

        Returns:
            List of OCR results for the entire batch

        Raises:
            JobNotCompletedError: If job is not completed
            ResultNotAvailableError: If results cannot be retrieved
        """
        self.logger.info(f"Getting results for batch job {job_id}")

        # Check job status
        job_details = self._api_get_job_details(job_id)
        if job_details.status != "completed":
            raise JobNotCompletedError(f"Job {job_id} is not completed (status: {job_details.status})")

        if not job_details.output_file:
            raise ResultNotAvailableError(f"No output file available for job {job_id}")

        # Download and parse results
        try:
            output_content = self._api_download_results(job_details.output_file)
            results = self.result_parser.parse_batch_output(output_content, job_id)
            
            self.logger.info(f"Retrieved {len(results)} results for batch job {job_id}")
            return results
            
        except Exception as e:
            error_msg = f"Failed to get results for job {job_id}: {str(e)}"
            self.logger.error(error_msg)
            raise ResultNotAvailableError(error_msg)

    def download_batch_results(
        self,
        job_id: str,
        output_directory: Optional[pathlib.Path] = None,
    ) -> pathlib.Path:
        """Download and save all results for a batch job as a single unit.

        Args:
            job_id: Job ID to download results for
            output_directory: Optional custom output directory

        Returns:
            Path to the directory containing all downloaded files

        Raises:
            ResultDownloadError: If download fails
        """
        self.logger.info(f"Downloading batch results for job {job_id}")

        try:
            # Get results for the entire batch
            results = self.get_batch_results(job_id)

            # Determine output directory
            if output_directory is None:
                xdg_paths = XDGPaths()
                base_download_dir = xdg_paths.get_data_dir() / "downloads"
                
                # Get document info for better organization
                doc_info = self.database.get_document_by_job(job_id)
                if doc_info:
                    document_name = doc_info[1]
                    job_dir = base_download_dir / document_name / job_id
                else:
                    job_dir = base_download_dir / "unknown" / job_id
            else:
                job_dir = output_directory / job_id

            # Create output directory
            FileSystemUtils.ensure_directory_exists(job_dir)

            # Save all results in the batch
            saved_files = []
            for i, result in enumerate(results):
                # Convert to ProcessedOCRResult for new file structure support
                processed_result = self._create_processed_result(result, job_id, i)
                
                # Save each file type in the processed result
                for file_obj in processed_result.files:
                    if file_obj.file_type == ProcessedOCRFileType.TEXT:
                        text_file = job_dir / f"{processed_result.file_name}_{i:03d}.txt"
                        FileIOUtils.write_text_file(text_file, file_obj.content)
                        saved_files.append(text_file)
                        
                    elif file_obj.file_type == ProcessedOCRFileType.MARKDOWN:
                        markdown_file = job_dir / f"{processed_result.file_name}_{i:03d}.md"
                        FileIOUtils.write_text_file(markdown_file, file_obj.content)
                        saved_files.append(markdown_file)
                        
                    elif file_obj.file_type == ProcessedOCRFileType.IMAGE:
                        # Handle image files - save base64 content to file
                        import base64
                        extension = file_obj.file_extension or ".png"
                        image_file = job_dir / f"{processed_result.file_name}_{i:03d}_image{extension}"
                        try:
                            image_data = base64.b64decode(file_obj.content)
                            FileIOUtils.write_binary_file(image_file, image_data)
                            saved_files.append(image_file)
                        except Exception as e:
                            self.logger.warning(f"Failed to decode base64 image: {e}")

            # Mark the entire batch as downloaded in the database
            self.database.mark_batch_job_downloaded(
                job_id=job_id,
                download_directory=str(job_dir),
                result_count=len(saved_files),
            )

            self.logger.info(
                f"Downloaded batch job {job_id} with {len(results)} results "
                f"({len(saved_files)} files) to {job_dir}"
            )
            return job_dir

        except Exception as e:
            error_msg = f"Failed to download batch results for job {job_id}: {str(e)}"
            self.logger.error(error_msg)
            raise ResultDownloadError(error_msg)

    def _create_processed_result(
        self, ocr_result: OCRResult, job_id: str, order: int
    ) -> ProcessedOCRResult:
        """Convert OCRResult to ProcessedOCRResult for the new file structure.

        Args:
            ocr_result: Original OCR result
            job_id: Job ID for the result
            order: Order/index of the result

        Returns:
            Validated ProcessedOCRResult
        """
        # Create file objects for text and markdown content
        files = []
        
        if ocr_result.text:
            text_file = ProcessedOCRFile(
                file_type=ProcessedOCRFileType.TEXT,
                content=ocr_result.text,
                file_extension=".txt"
            )
            files.append(text_file)
        
        if ocr_result.markdown:
            markdown_file = ProcessedOCRFile(
                file_type=ProcessedOCRFileType.MARKDOWN,
                content=ocr_result.markdown,
                file_extension=".md"
            )
            files.append(markdown_file)
        
        return ProcessedOCRResult(
            file_name=ocr_result.file_name,
            job_id=job_id,
            custom_id=f"{ocr_result.file_name}_{order:03d}",
            files=files,
            # Backward compatibility
            text=ocr_result.text,
            markdown=ocr_result.markdown
        )

    def is_batch_downloaded(self, job_id: str) -> bool:
        """Check if a batch job has been downloaded.

        Args:
            job_id: Job ID to check

        Returns:
            True if the entire batch has been downloaded, False otherwise
        """
        return self.database.is_batch_job_downloaded(job_id)

    def get_batch_download_info(self, job_id: str) -> Optional[tuple[str, int]]:
        """Get download information for a batch job.

        Args:
            job_id: Job ID to get download info for

        Returns:
            Tuple of (download_directory, result_count) if downloaded, None otherwise
        """
        return self.database.get_batch_job_download_info(job_id)

    def download_multiple_batches(self, job_ids: List[str]) -> List[pathlib.Path]:
        """Download multiple batch jobs concurrently.

        Args:
            job_ids: List of job IDs to download

        Returns:
            List of download directories for each batch
        """
        self.logger.info(f"Downloading {len(job_ids)} batch jobs concurrently")

        # Filter out already downloaded jobs
        jobs_to_download = [
            job_id for job_id in job_ids 
            if not self.is_batch_downloaded(job_id)
        ]

        if not jobs_to_download:
            self.logger.info("All requested batch jobs are already downloaded")
            return []

        # Use concurrent processor for parallel downloads
        async def download_job(job_id: str) -> pathlib.Path:
            return self.download_batch_results(job_id)

        download_paths = run_async_in_sync_context(
            self.concurrent_processor.run_concurrent_operations(
                [download_job(job_id) for job_id in jobs_to_download]
            )
        )

        self.logger.info(f"Completed downloading {len(download_paths)} batch jobs")
        return download_paths

    def close(self) -> None:
        """Clean up resources."""
        if self._concurrent_processor:
            self._concurrent_processor.close()
            self._concurrent_processor = None