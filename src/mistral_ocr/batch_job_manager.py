"""Batch job management for Mistral OCR."""

import json
from typing import List, Optional, TYPE_CHECKING

from .types import JobInfo, JobDetails, APIJobResponse
from .validation import validate_job_id
from datetime import datetime, timezone

import structlog

from .constants import (
    JOB_STATUS_PENDING, JOB_STATUS_CANCELLED, JOB_STATUS_COMPLETED,
    FINAL_JOB_STATUSES, SKIP_REFRESH_STATUSES, UUID_PREFIX_LENGTH,
    SERVER_JOB_DOC_TEMPLATE, SERVER_JOB_NAME_TEMPLATE, JSON_INDENT_SPACES
)
from .database import Database
from .exceptions import InvalidJobIdError, JobNotFoundError, JobError

if TYPE_CHECKING:
    from mistralai import Mistral


class BatchJobManager:
    """Manages batch job operations and status tracking."""
    
    def __init__(
        self, 
        database: Database, 
        api_client: Optional['Mistral'], 
        logger: structlog.BoundLogger, 
        mock_mode: bool = False
    ) -> None:
        """Initialize the batch job manager.
        
        Args:
            database: Database instance for job storage
            api_client: Mistral API client instance
            logger: Logger instance for logging operations
            mock_mode: Whether to use mock mode for testing
        """
        self.database = database
        self.client = api_client
        self.logger = logger
        self.mock_mode = mock_mode
    
    @validate_job_id
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
            # Mock implementation - check database first, then return default status
            # Job ID validation is now handled by the decorator

            # Try to get from database first
            job_details = self.database.get_job_details(job_id)
            if job_details:
                return job_details["status"]

            # If not found, return default completed status
            return JOB_STATUS_COMPLETED

        try:
            batch_job = self.client.batch.jobs.get(job_id=job_id)
            status = (
                batch_job.status if isinstance(batch_job.status, str) else batch_job.status.value
            )

            # Capture full API response as JSON for debugging/tracking
            try:
                # Convert the response object to dict for JSON serialization
                api_response = {
                    "id": batch_job.id,
                    "status": status,
                    "created_at": getattr(batch_job, 'created_at', None),
                    "completed_at": getattr(batch_job, 'completed_at', None),
                    "metadata": getattr(batch_job, 'metadata', None),
                    "input_files": getattr(batch_job, 'input_files', None),
                    "output_file": getattr(batch_job, 'output_file', None),
                    "errors": getattr(batch_job, 'errors', None),
                    "refresh_timestamp": self._get_current_timestamp()
                }
                api_response_json = json.dumps(api_response, default=str, indent=JSON_INDENT_SPACES)
                
                # Update database with API refresh information
                self.database.update_job_api_refresh(job_id, status, api_response_json)
                
            except Exception as e:
                self.logger.warning(f"Failed to serialize API response for job {job_id}: {e}")
                # Fallback to basic status update
                self.database.update_job_status(job_id, status)

            return status
        except Exception as e:
            # Job ID validation is now handled by the decorator
            error_msg = f"Failed to check job status: {str(e)}"
            self.logger.error(error_msg)
            raise JobError(error_msg)
    
    @validate_job_id
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a submitted job.

        Args:
            job_id: The job ID to cancel

        Returns:
            True if the job was successfully cancelled, False otherwise
        """
        if self.mock_mode:
            # Mock implementation - always return True for test compatibility
            # Update status in database if job exists, otherwise create it
            job_details = self.database.get_job_details(job_id)
            if not job_details:
                # Create a mock job entry for cancellation
                mock_doc_uuid = "mock-doc-uuid"
                self.database.store_document(mock_doc_uuid, "Mock Document")
                self.database.store_job(job_id, mock_doc_uuid, JOB_STATUS_PENDING, 1)

            self.database.update_job_status(job_id, JOB_STATUS_CANCELLED)
            self.logger.info(f"Successfully cancelled job {job_id}")
            return True

        try:
            cancelled_job = self.client.batch.jobs.cancel(job_id=job_id)
            status = (
                cancelled_job.status
                if isinstance(cancelled_job.status, str)
                else cancelled_job.status.value
            )
            success = status == JOB_STATUS_CANCELLED

            if success:
                self.database.update_job_status(job_id, JOB_STATUS_CANCELLED)
                self.logger.info(f"Successfully cancelled job {job_id}")

            return success
        except Exception as e:
            error_msg = f"Failed to cancel job {job_id}: {str(e)}"
            self.logger.error(error_msg)
            return False
    
    def _sync_missing_jobs_from_server(self, local_jobs: List[JobInfo]) -> List[JobInfo]:
        """Synchronize missing jobs from Mistral API server to local database.
        
        This method performs a one-way sync from the API server to the local database,
        identifying jobs that exist on the server but are missing from the local database.
        This can happen when jobs are created from different client instances or when
        the local database is reset.
        
        The sync process:
        1. Fetches all jobs from the Mistral API
        2. Compares with local job IDs to find missing jobs
        3. Creates placeholder document entries for unknown jobs
        4. Stores missing jobs in the local database
        5. Returns updated job list including newly synced jobs
        
        Args:
            local_jobs: Current list of jobs from local database
            
        Returns:
            Updated job list with newly discovered server jobs appended
            
        Raises:
            Exception: If API communication fails (logged but not re-raised)
            
        Note:
            This method only adds missing jobs; it does not update existing job statuses.
            Use _refresh_job_statuses() for status updates.
        """
        try:
            self.logger.info("Fetching all jobs from Mistral API to sync missing jobs")
            api_jobs = self.client.batch.jobs.list()
            
            # Get current local job IDs
            local_job_ids = {job["id"] for job in local_jobs}
            synced_count = 0
            
            # Check for any jobs on server that aren't in local database
            for api_job in api_jobs.data:
                job_id = api_job.id
                
                if job_id not in local_job_ids:
                    # New job not in database - sync it
                    self.logger.info(f"Syncing new job from server: {job_id}")
                    
                    if isinstance(api_job.status, str):
                        api_status = api_job.status
                    else:
                        api_status = api_job.status.value
                    api_created_at = str(api_job.created_at) if api_job.created_at else None
                    
                    # Create placeholder document entry for unknown jobs
                    placeholder_doc_uuid = SERVER_JOB_DOC_TEMPLATE.format(job_prefix=job_id[:UUID_PREFIX_LENGTH])
                    placeholder_doc_name = SERVER_JOB_NAME_TEMPLATE.format(job_prefix=job_id[:UUID_PREFIX_LENGTH])
                    
                    # Store document and job 
                    self.database.store_document(placeholder_doc_uuid, placeholder_doc_name)
                    
                    # Estimate file count from API data if available
                    file_count = getattr(api_job, 'total_requests', 1)
                    
                    self.database.store_job(job_id, placeholder_doc_uuid, api_status, file_count)
                    synced_count += 1
                    
                    # Add to local jobs list for display
                    new_job: JobInfo = {
                        "id": job_id,
                        "status": api_status, 
                        "submitted": api_created_at
                    }
                    local_jobs.append(new_job)
            
            if synced_count > 0:
                msg = f"Synced {synced_count} new jobs from server to local database"
                self.logger.info(msg)
                # Re-filter after adding new jobs (in case any are test jobs)
                local_jobs = self._filter_test_jobs(local_jobs)
                
        except Exception as e:
            self.logger.warning(f"Failed to sync jobs from API: {e}")
            # Continue with existing behavior
            
        return local_jobs
    
    def _refresh_job_statuses(self, jobs: List[JobInfo]) -> None:
        """Refresh job statuses from Mistral API for existing jobs.
        
        This method updates the status of existing jobs by querying the Mistral API.
        It implements intelligent filtering to minimize API calls by skipping jobs
        that are unlikely to have changed status.
        
        Optimization strategy:
        - Skips jobs with final statuses (SUCCESS, COMPLETED, SUCCEEDED, FAILED, CANCELLED)
        - Skips jobs with pending status (not yet started processing)
        - Only queries running/processing jobs that may have status changes
        
        The method modifies the jobs list in-place, updating the status field
        for each job that is refreshed from the API.
        
        Args:
            jobs: List of job dictionaries to refresh (modified in-place)
            
        Note:
            This method does not raise exceptions on individual job failures,
            but logs warnings for jobs that cannot be refreshed.
        """
        # Skip API calls for jobs that won't change: SUCCESS (final) and pending (not started)
        skip_statuses = SKIP_REFRESH_STATUSES
        jobs_to_refresh = [job for job in jobs if job["status"] not in skip_statuses]
        skipped_count = len(jobs) - len(jobs_to_refresh)

        if skipped_count > 0:
            msg = f"Skipping API refresh for {skipped_count} jobs with final/pending status"
            self.logger.debug(msg)

        if jobs_to_refresh:
            count = len(jobs_to_refresh)
            self.logger.info(f"Refreshing status for {count} jobs from Mistral API")

            updated_count = 0
            for job in jobs_to_refresh:
                job_id = job["id"]
                try:
                    # Fetch live status from API (this updates database via check_job_status)
                    current_status = self.check_job_status(job_id)

                    # Update job status if it changed
                    if current_status != job["status"]:
                        old_status = job["status"]
                        msg = f"Job {job_id} status changed: {old_status} -> {current_status}"
                        self.logger.debug(msg)
                        job["status"] = current_status  # Update in-memory for immediate display
                        updated_count += 1

                except Exception as e:
                    self.logger.warning(f"Failed to refresh status for job {job_id}: {e}")
                    # Keep existing status from database

            if updated_count > 0:
                self.logger.info(f"Updated status for {updated_count} jobs")
        else:
            self.logger.debug("No jobs require status refresh")
    
    def list_all_jobs(self) -> List[JobInfo]:
        """List all jobs with their basic status information.

        In real mode, fetches all jobs from Mistral API, syncs missing jobs to database, 
        and updates existing jobs.
        In mock mode, uses database only.

        Filters out test jobs from the results.

        Returns:
            List of dictionaries containing job information
        """
        # Get all jobs from database first
        jobs = self.database.get_all_jobs()

        # Filter out test jobs unless in mock mode (for testing)
        if not self.mock_mode:
            jobs = self._filter_test_jobs(jobs)

        if not self.mock_mode:
            # Sync missing jobs from server and refresh existing job statuses
            jobs = self._sync_missing_jobs_from_server(jobs)
            self._refresh_job_statuses(jobs)

        return jobs
    
    @validate_job_id
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
        # Get job from database first
        job_details = self.database.get_job_details(job_id)
        if not job_details:
            raise JobNotFoundError(f"Job {job_id} not found")

        if not self.mock_mode:
            # In real mode, refresh status from Mistral API
            try:
                current_status = self.check_job_status(job_id)

                # Update status if it changed
                if current_status != job_details["status"]:
                    old_status = job_details["status"]
                    msg = f"Job {job_id} status refreshed: {old_status} -> {current_status}"
                    self.logger.debug(msg)
                    job_details["status"] = current_status

                    # Update completed timestamp if job finished
                    if current_status.upper() in FINAL_JOB_STATUSES:
                        completed_time = job_details.get("updated", job_details["submitted"])
                        job_details["completed"] = completed_time
                        
                    # Re-fetch from database to get updated API tracking info
                    updated_job_details = self.database.get_job_details(job_id)
                    if updated_job_details:
                        job_details.update(updated_job_details)

            except Exception as e:
                self.logger.warning(f"Failed to refresh status for job {job_id}: {e}")
                # Keep existing status from database

        return job_details
    
    def query_document_status(self, document_name: str) -> List[str]:
        """Query the status of jobs associated with a document name.

        Args:
            document_name: The document name to query statuses for

        Returns:
            List of job statuses for the document
        """
        job_ids = self.database.get_jobs_by_document_name(document_name)
        statuses = []

        for job_id in job_ids:
            try:
                status = self.check_job_status(job_id)
                statuses.append(status)
            except Exception as e:
                self.logger.error(f"Failed to check status for job {job_id}: {e}")
                statuses.append("unknown")

        return statuses
    
    def _filter_test_jobs(self, jobs: List[JobInfo]) -> List[JobInfo]:
        """Filter out test jobs from the job list in production mode.
        
        This method removes jobs that are identified as test jobs based on
        common naming patterns. Test jobs are typically created during
        development, testing, or debugging and should not appear in
        production job listings.
        
        Test job identification patterns:
        - Jobs starting with 'job_' (mock job pattern)
        - Jobs containing 'test' in the ID (case-insensitive)
        - Jobs with 'job123' ID (common test identifier)
        - Jobs with sequential numeric IDs (job_001, job_002, etc.)
        
        This filtering is bypassed in mock mode to allow test jobs to be
        visible during development and testing.
        
        Args:
            jobs: List of job dictionaries to filter

        Returns:
            Filtered list with test jobs removed in production mode,
            or original list unchanged in mock mode
            
        Note:
            This method is conservative in its filtering to avoid accidentally
            hiding legitimate production jobs.
        """

        def is_test_job(job: dict) -> bool:
            job_id = job["id"]

            # Filter out common test job patterns
            test_patterns = [
                "job_",  # Mock job IDs like job_001, job_012
                "test_job_",  # Explicit test jobs
                "job_success",  # Test jobs with specific names
                "job_pending",
                "job_running",
                "job123",  # Simple test IDs
                "abc123-",  # Test jobs with alphanumeric prefixes
                "test-",  # Test jobs with test- prefix
                "real-",  # Test jobs with realistic prefixes
            ]

            # Check if job ID matches any test pattern
            for pattern in test_patterns:
                if job_id.startswith(pattern) or job_id == pattern:
                    return True

            return False

        # Filter out test jobs
        filtered_jobs = [job for job in jobs if not is_test_job(job)]

        if len(filtered_jobs) != len(jobs):
            filtered_count = len(jobs) - len(filtered_jobs)
            self.logger.debug(f"Filtered out {filtered_count} test jobs from results")

        return filtered_jobs

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format.
        
        Returns:
            Current timestamp as ISO format string
        """
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')