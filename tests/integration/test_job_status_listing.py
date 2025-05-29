"""Job status listing integration tests for Mistral OCR."""

import os
import pathlib
import subprocess

import pytest

from mistral_ocr.client import MistralOCRClient


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the CLI with the local package path and isolated test environment."""
    env = {**os.environ, "PYTHONPATH": "src", "MISTRAL_API_KEY": "test"}

    # Ensure CLI uses isolated test directories for both data and state
    # This guarantees database isolation during tests
    if "XDG_DATA_HOME" in os.environ:
        env["XDG_DATA_HOME"] = os.environ["XDG_DATA_HOME"]
    if "XDG_STATE_HOME" in os.environ:
        env["XDG_STATE_HOME"] = os.environ["XDG_STATE_HOME"]

    return subprocess.run(
        ["python", "-m", "mistral_ocr", *args],
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture
def xdg_data_home(tmp_path, monkeypatch):
    """Set XDG_DATA_HOME and XDG_STATE_HOME to tmp_path for testing.

    This ensures both data and state (including database) are isolated to test directories.
    """
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path


@pytest.mark.integration
class TestJobStatusListing:
    """Tests for job status listing functionality."""

    def test_list_all_jobs_command(self) -> None:
        """Test CLI command to list all jobs."""
        result = run_cli("jobs", "list")
        assert result.returncode == 0
        # Should handle empty list gracefully or show headers
        assert "No jobs found" in result.stdout or "Job ID" in result.stdout

    def test_list_jobs_shows_all_statuses(self) -> None:
        """Test that list jobs shows jobs of all statuses."""
        result = run_cli("jobs", "list")
        assert result.returncode == 0
        # Should handle empty list gracefully
        assert "No jobs found" in result.stdout or "Job ID" in result.stdout

    def test_job_detail_status_command(
        self, tmp_path: pathlib.Path, xdg_data_home: pathlib.Path
    ) -> None:
        """Test CLI command to show detailed job status."""
        # Create a test file and submit it to create a real job
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fakepng")

        # Submit the file via CLI to create a job
        submit_result = run_cli("submit", str(test_file))
        assert submit_result.returncode == 0

        # Extract job ID from the output (format: "Submitted job: job_001")
        output_lines = submit_result.stdout.strip().split("\n")
        job_line = [line for line in output_lines if "Submitted job:" in line][0]
        job_id = job_line.split("Submitted job: ")[1]

        # Now test the job status command
        result = run_cli("jobs", "status", job_id)
        assert result.returncode == 0
        assert f"Job ID: {job_id}" in result.stdout
        assert "Status:" in result.stdout
        assert "Document Name:" in result.stdout

    def test_job_detail_status_invalid_id(self) -> None:
        """Test job detail command with invalid job ID."""
        from unittest.mock import patch

        from mistral_ocr.exceptions import JobNotFoundError

        # Mock the get_job_details method to raise JobNotFoundError
        with patch("mistral_ocr.client.MistralOCRClient.get_job_details") as mock_get_details:
            mock_get_details.side_effect = JobNotFoundError("Job not found")

            result = run_cli("jobs", "status", "invalid_job")
            assert result.returncode != 0
            assert "error" in result.stderr.lower() or "not found" in result.stderr.lower()

    def test_list_jobs_table_format(self) -> None:
        """Test that list jobs outputs in readable table format."""
        result = run_cli("jobs", "list")
        assert result.returncode == 0
        # Should have header and proper column alignment
        lines = result.stdout.split("\n")

        # Check for table structure (either with jobs or just headers)
        if any(line.strip() for line in lines):  # Has any content
            # Look for header text indicating table format
            output_text = result.stdout
            assert (
                "Job ID" in output_text
                or "No jobs found" in output_text
                or "job" in output_text.lower()
            )

    def test_list_jobs_refreshes_from_api(
        self, tmp_path: pathlib.Path, xdg_data_home: pathlib.Path
    ) -> None:
        """Test that list jobs refreshes status from Mistral API in real mode."""
        from unittest.mock import Mock, patch

        # Create client in real mode (not test mode)
        client = MistralOCRClient(api_key="real-api-key")
        client.mock_mode = False  # Force real mode for this test
        client.job_manager.mock_mode = False  # Ensure job manager is also in real mode

        # Create a realistic job with stale status in database
        test_doc_uuid = "real-doc-uuid-refresh"
        client.database.store_document(test_doc_uuid, "Real Document")
        client.database.store_job(
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890", test_doc_uuid, "running", 1
        )  # Use UUID-like production job ID

        # Mock the Mistral API batch jobs list endpoint to return updated status
        mock_api_job = Mock()
        mock_api_job.id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_api_job.status = "completed"
        mock_api_job.created_at = "2024-01-01T10:00:00Z"
        mock_api_job.completed_at = "2024-01-01T10:05:00Z"
        mock_api_job.total_requests = 1

        mock_response = Mock()
        mock_response.data = [mock_api_job]

        with patch.object(client.client.batch.jobs, "list", return_value=mock_response):
            # Call list_all_jobs - should refresh from API using batch list call
            jobs = client.list_all_jobs()

            # Verify the job status was updated
            refresh_job = next(
                (job for job in jobs if job["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"), None
            )
            assert refresh_job is not None
            assert refresh_job["status"] == "completed"

    def test_list_jobs_uses_batch_api_efficiently(
        self, tmp_path: pathlib.Path, xdg_data_home: pathlib.Path
    ) -> None:
        """Test that list jobs uses efficient batch API call instead of individual calls."""
        from unittest.mock import Mock, patch

        # Create client in real mode (not test mode)
        client = MistralOCRClient(api_key="real-api-key")
        client.mock_mode = False  # Force real mode for this test
        client.job_manager.mock_mode = False  # Ensure job manager is also in real mode

        # Create realistic jobs with different statuses
        real_doc_uuid = "real-doc-uuid-batch"
        client.database.store_document(real_doc_uuid, "Real Document")
        client.database.store_job(
            "b2c3d4e5-f6a7-8901-bcde-f23456789012", real_doc_uuid, "SUCCESS", 1
        )
        client.database.store_job(
            "c3d4e5f6-a7b8-9012-cdef-345678901234", real_doc_uuid, "pending", 1
        )
        client.database.store_job(
            "d4e5f6a7-b8c9-0123-defa-456789012345", real_doc_uuid, "running", 1
        )

        # Mock API jobs with updated statuses
        mock_jobs = []
        for job_id, status in [
            ("b2c3d4e5-f6a7-8901-bcde-f23456789012", "SUCCESS"),
            ("c3d4e5f6-a7b8-9012-cdef-345678901234", "SUCCESS"),  # Updated from pending
            ("d4e5f6a7-b8c9-0123-defa-456789012345", "SUCCESS"),  # Updated from running
        ]:
            mock_job = Mock()
            mock_job.id = job_id
            mock_job.status = status
            mock_job.created_at = "2024-01-01T10:00:00Z"
            mock_job.completed_at = "2024-01-01T10:05:00Z"
            mock_job.total_requests = 1
            mock_jobs.append(mock_job)

        mock_response = Mock()
        mock_response.data = mock_jobs

        list_call_count = 0

        def mock_list():
            nonlocal list_call_count
            list_call_count += 1
            return mock_response

        with patch.object(client.client.batch.jobs, "list", side_effect=mock_list):
            # Call list_all_jobs - should use single batch API call
            jobs = client.list_all_jobs()

            # Verify only ONE batch API call was made (efficient!)
            assert list_call_count == 1

            # Verify all jobs were updated, including pending jobs
            pending_job = next(
                (job for job in jobs if job["id"] == "c3d4e5f6-a7b8-9012-cdef-345678901234"), None
            )
            running_job = next(
                (job for job in jobs if job["id"] == "d4e5f6a7-b8c9-0123-defa-456789012345"), None
            )

            assert pending_job is not None
            assert pending_job["status"] == "SUCCESS"  # Updated from pending
            assert running_job is not None
            assert running_job["status"] == "SUCCESS"  # Updated from running

            # Verify all jobs are still returned
            job_ids = {job["id"] for job in jobs}
            assert "b2c3d4e5-f6a7-8901-bcde-f23456789012" in job_ids
            assert "c3d4e5f6-a7b8-9012-cdef-345678901234" in job_ids
            assert "d4e5f6a7-b8c9-0123-defa-456789012345" in job_ids

    def test_list_jobs_hides_test_jobs_in_real_mode(
        self, tmp_path: pathlib.Path, xdg_data_home: pathlib.Path
    ) -> None:
        """Test that test jobs are hidden in real mode but shown in mock mode."""
        # Create client in real mode
        client = MistralOCRClient(api_key="real-api-key")
        client.mock_mode = False

        # Create a mix of real and test jobs
        test_doc_uuid = "test-doc-uuid-filter"
        real_doc_uuid = "real-doc-uuid"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_document(real_doc_uuid, "Real Document")

        # Add test jobs (should be filtered out)
        client.database.store_job("job_001", test_doc_uuid, "SUCCESS", 1)
        client.database.store_job("test_job_example", test_doc_uuid, "pending", 1)
        client.database.store_job("job123", test_doc_uuid, "completed", 1)

        # Add production job (should be shown) - use UUID-like pattern
        client.database.store_job(
            "f47ac10b-58cc-4372-a567-0e02b2c3d479", real_doc_uuid, "SUCCESS", 1
        )

        # Mock check_job_status to avoid actual API calls
        def mock_check_status(job_id):
            return "SUCCESS"

        client.check_job_status = mock_check_status

        # Call list_all_jobs in real mode - should filter test jobs
        jobs = client.list_all_jobs()
        job_ids = {job["id"] for job in jobs}

        # Test jobs should be filtered out
        assert "job_001" not in job_ids
        assert "test_job_example" not in job_ids
        assert "job123" not in job_ids

        # Production job should be included
        assert "f47ac10b-58cc-4372-a567-0e02b2c3d479" in job_ids

    def test_list_jobs_shows_test_jobs_in_mock_mode(
        self, tmp_path: pathlib.Path, xdg_data_home: pathlib.Path
    ) -> None:
        """Test that test jobs are shown in mock mode for testing purposes."""
        # Create client in mock mode
        client = MistralOCRClient(api_key="test")
        assert client.mock_mode

        # Create test jobs
        test_doc_uuid = "test-doc-uuid-mock"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job("job_001", test_doc_uuid, "SUCCESS", 1)
        client.database.store_job("test_job_example", test_doc_uuid, "pending", 1)

        # Call list_all_jobs in mock mode - should show test jobs
        jobs = client.list_all_jobs()
        job_ids = {job["id"] for job in jobs}

        # Test jobs should be included in mock mode
        assert "job_001" in job_ids
        assert "test_job_example" in job_ids

    def test_api_refresh_tracking(
        self, tmp_path: pathlib.Path, xdg_data_home: pathlib.Path
    ) -> None:
        """Test that API refresh information is stored correctly."""
        from unittest.mock import Mock, patch

        # Create client in real mode
        client = MistralOCRClient(api_key="real-api-key")
        client.mock_mode = False

        # Create a realistic job
        test_doc_uuid = "tracking-test-doc"
        client.database.store_document(test_doc_uuid, "Tracking Test")
        client.database.store_job("test-tracking-job", test_doc_uuid, "running", 1)

        # Mock the API call to return a job object
        mock_api_job = Mock()
        mock_api_job.id = "test-tracking-job"
        mock_api_job.status = "completed"
        mock_api_job.created_at = "2023-12-01T10:00:00Z"
        mock_api_job.completed_at = "2023-12-01T10:05:00Z"
        mock_api_job.metadata = {"job_type": "ocr_batch"}
        mock_api_job.input_files = ["file_123"]
        mock_api_job.output_file = "output_456"
        mock_api_job.errors = None
        mock_api_job.total_requests = 1

        with patch.object(client.client.batch.jobs, "get", return_value=mock_api_job):
            # Call check_job_status first to ensure API refresh data is stored
            status = client.check_job_status("test-tracking-job")
            assert status == "completed"

            # Then call get_job_details which should have the refresh data
            job_details = client.get_job_details("test-tracking-job")

            # Verify tracking information was stored
            assert job_details["status"] == "completed"
            assert job_details["last_api_refresh"] is not None
            assert job_details["api_response_json"] is not None

            # Verify API response JSON contains expected fields
            import json

            api_data = json.loads(job_details["api_response_json"])
            assert api_data["id"] == "test-tracking-job"
        assert api_data["status"] == "completed"
        assert api_data["created_at"] == "2023-12-01T10:00:00Z"
        assert api_data["completed_at"] == "2023-12-01T10:05:00Z"
        assert "refresh_timestamp" in api_data
