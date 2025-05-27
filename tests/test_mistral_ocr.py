import logging
import os
import pathlib
import subprocess

import pytest

from mistral_ocr.client import MistralOCRClient
from mistral_ocr.config import ConfigurationManager
from mistral_ocr.database import Database
from mistral_ocr.logging import setup_logging


# Helper function to run the CLI
def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the CLI with the local package path."""
    env = {**os.environ, "PYTHONPATH": "src", "MISTRAL_API_KEY": "test"}

    # Make sure CLI uses the same test directories if they're set
    if "XDG_DATA_HOME" in os.environ:
        env["XDG_STATE_HOME"] = os.environ["XDG_DATA_HOME"]  # Use same temp dir for database

    return subprocess.run(
        ["python", "-m", "mistral_ocr", *args],
        capture_output=True,
        text=True,
        env=env,
    )


# Helper function to create test files
def create_test_files(
    directory: pathlib.Path, count: int = 2, extension: str = ".png"
) -> list[pathlib.Path]:
    """Create test files in a directory."""
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    for i in range(count):
        file = directory / f"test_{i}{extension}"
        file.write_bytes(f"content_{i}".encode())
        files.append(file)
    return files


# Fixtures
@pytest.fixture
def client():
    """Provide a test MistralOCRClient instance."""
    return MistralOCRClient(api_key="test")


@pytest.fixture
def png_file(tmp_path):
    """Create a test PNG file."""
    file = tmp_path / "test.png"
    file.write_bytes(b"fakepng")
    return file


@pytest.fixture
def jpeg_file(tmp_path):
    """Create a test JPEG file."""
    file = tmp_path / "test.jpg"
    file.write_bytes(b"fakejpeg")
    return file


@pytest.fixture
def pdf_file(tmp_path):
    """Create a test PDF file."""
    file = tmp_path / "test.pdf"
    file.write_bytes(b"fakepdf")
    return file


@pytest.fixture
def xdg_data_home(tmp_path, monkeypatch):
    """Set XDG_DATA_HOME to tmp_path for testing."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    return tmp_path


# Basic Integrity Checks


# Basic Integrity Checks
class TestBasicIntegrity:
    """Tests for basic system integrity and setup."""

    def test_display_help_message(self) -> None:
        result = run_cli("--help")
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()

    def test_configuration_availability(self) -> None:
        config = ConfigurationManager()
        assert config is not None

    def test_log_file_creation(self, tmp_path: pathlib.Path) -> None:
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        log_file = setup_logging(log_dir)
        logging.getLogger("test").error("test message")
        assert log_file.exists()
        assert "test message" in log_file.read_text()

    def test_database_connectivity(self, tmp_path: pathlib.Path) -> None:
        db = Database(tmp_path / "test.db")
        db.connect()
        db.execute("CREATE TABLE example (name TEXT)")
        db.execute("INSERT INTO example (name) VALUES ('abc')")
        result = db.execute("SELECT name FROM example LIMIT 1")
        assert result == "abc"


# File Submission Tests
class TestFileSubmission:
    """Tests for file submission functionality."""

    @pytest.mark.parametrize(
        "extension,content", [(".png", b"fakepng"), (".jpg", b"fakejpeg"), (".pdf", b"fakepdf")]
    )
    def test_submit_single_file(
        self, tmp_path: pathlib.Path, client: MistralOCRClient, extension: str, content: bytes
    ) -> None:
        test_file = tmp_path / f"test{extension}"
        test_file.write_bytes(content)
        job_id = client.submit_documents([test_file])
        assert job_id is not None

    def test_unsupported_file_type(self, tmp_path: pathlib.Path, client: MistralOCRClient) -> None:
        invalid_file = tmp_path / "file.txt"
        invalid_file.write_text("text")
        with pytest.raises(ValueError):
            client.submit_documents([invalid_file])

    def test_file_not_found(self, client: MistralOCRClient) -> None:
        with pytest.raises(FileNotFoundError):
            client.submit_documents([pathlib.Path("missing.png")])

    def test_submit_directory_non_recursive(
        self, tmp_path: pathlib.Path, client: MistralOCRClient
    ) -> None:
        directory = tmp_path / "docs"
        create_test_files(directory, count=2)
        job_id = client.submit_documents([directory])
        assert job_id is not None

    def test_submit_directory_recursive(
        self, tmp_path: pathlib.Path, client: MistralOCRClient
    ) -> None:
        directory = tmp_path / "docs"
        sub = directory / "sub"
        create_test_files(sub, count=1)
        job_id = client.submit_documents([directory], recursive=True)  # type: ignore
        assert job_id is not None

    def test_automatic_batch_partitioning(
        self, tmp_path: pathlib.Path, client: MistralOCRClient
    ) -> None:
        files = create_test_files(tmp_path / "docs", count=105)
        job_ids = client.submit_documents(files)
        assert len(job_ids) > 1


# Document Management Tests
class TestDocumentManagement:
    """Tests for document naming and association."""

    def test_create_new_document_by_name(
        self, png_file: pathlib.Path, client: MistralOCRClient
    ) -> None:
        job_id = client.submit_documents([png_file], document_name="Doc")  # type: ignore
        assert job_id is not None

    def test_append_pages_to_recent_document(
        self, png_file: pathlib.Path, client: MistralOCRClient
    ) -> None:
        client.submit_documents([png_file], document_name="Doc")  # type: ignore
        job_id = client.submit_documents([png_file], document_name="Doc")  # type: ignore
        assert job_id is not None

    def test_append_pages_to_document_by_uuid(
        self, png_file: pathlib.Path, client: MistralOCRClient
    ) -> None:
        doc_id = "1234"
        job_id = client.submit_documents([png_file], document_uuid=doc_id)  # type: ignore
        assert job_id is not None


# Job Management Tests
class TestJobManagement:
    """Tests for job status and management."""

    def test_check_job_status_by_id(self, client: MistralOCRClient) -> None:
        status = client.check_job_status("job123")
        assert status in {"pending", "processing", "completed", "failed"}

    def test_query_status_by_document_name(self, client: MistralOCRClient) -> None:
        statuses = client.query_document_status("Doc")
        assert isinstance(statuses, list)

    def test_cancel_job(self, client: MistralOCRClient) -> None:
        result = client.cancel_job("job123")
        assert result is True

    def test_invalid_job_id(self, client: MistralOCRClient) -> None:
        with pytest.raises(ValueError):
            client.check_job_status("invalid")


# Result Retrieval Tests
class TestResultRetrieval:
    """Tests for result download and retrieval."""

    def test_retrieve_results_for_completed_job(self, client: MistralOCRClient) -> None:
        results = client.get_results("job123")
        assert isinstance(results, list)

    def test_retrieve_before_completion(self, client: MistralOCRClient) -> None:
        with pytest.raises(RuntimeError):
            client.get_results("job123")

    def test_automatic_download_results(
        self, tmp_path: pathlib.Path, client: MistralOCRClient
    ) -> None:
        client.download_results("job123", destination=tmp_path)  # type: ignore
        assert (tmp_path / "job123").exists()

    def test_unknown_document_storage(
        self, tmp_path: pathlib.Path, client: MistralOCRClient
    ) -> None:
        client.download_results("job123", destination=tmp_path)  # type: ignore
        assert (tmp_path / "unknown").exists()

    def test_redownload_results(self, tmp_path: pathlib.Path, client: MistralOCRClient) -> None:
        client.download_results("job123", destination=tmp_path)  # type: ignore
        client.download_results("job123", destination=tmp_path)  # type: ignore
        assert (tmp_path / "job123").exists()


# Job Status Listing Tests
class TestJobStatusListing:
    """Tests for job status listing functionality."""

    def test_list_all_jobs_command(self) -> None:
        """Test CLI command to list all jobs."""
        result = run_cli("--list-jobs")
        assert result.returncode == 0
        # Should handle empty list gracefully or show headers
        assert "No jobs found" in result.stdout or "Job ID" in result.stdout

    def test_list_jobs_shows_all_statuses(self) -> None:
        """Test that list jobs shows jobs of all statuses."""
        result = run_cli("--list-jobs")
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
        submit_result = run_cli("--submit", str(test_file))
        assert submit_result.returncode == 0

        # Extract job ID from the output (format: "Submitted job: job_001")
        output_lines = submit_result.stdout.strip().split("\n")
        job_line = [line for line in output_lines if "Submitted job:" in line][0]
        job_id = job_line.split("Submitted job: ")[1]

        # Now test the job status command
        result = run_cli("--job-status", job_id)
        assert result.returncode == 0
        assert f"Job ID: {job_id}" in result.stdout
        assert "Status:" in result.stdout
        assert "Document Name:" in result.stdout

    def test_job_detail_status_invalid_id(self) -> None:
        """Test job detail command with invalid job ID."""
        result = run_cli("--job-status", "invalid_job")
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_list_jobs_table_format(self) -> None:
        """Test that list jobs outputs in readable table format."""
        result = run_cli("--list-jobs")
        assert result.returncode == 0
        # Should have header and proper column alignment
        lines = result.stdout.split("\n")
        if len(lines) > 1:  # Has content beyond header
            # Basic table structure check
            assert any("Job ID" in line for line in lines)

    def test_list_jobs_refreshes_from_api(self, tmp_path: pathlib.Path, xdg_data_home: pathlib.Path) -> None:
        """Test that list jobs refreshes status from Mistral API in real mode."""
        # Create a client that uses the same temporary data directory as the CLI
        from mistral_ocr.client import MistralOCRClient
        
        # Create client in real mode (not test mode)
        client = MistralOCRClient(api_key="real-api-key")
        client.mock_mode = False  # Force real mode for this test
        
        # Create a realistic job with stale status in database
        test_doc_uuid = "real-doc-uuid-refresh"
        client.db.store_document(test_doc_uuid, "Real Document")
        client.db.store_job("abc123-real-job-id", test_doc_uuid, "running", 1)  # Use realistic job ID
        
        # Mock the check_job_status method to return updated status
        original_method = client.check_job_status
        def mock_check_status(job_id):
            if job_id == "abc123-real-job-id":
                return "completed"  # Simulate API returning updated status
            return original_method(job_id)
        
        client.check_job_status = mock_check_status
        
        # Call list_all_jobs - should refresh from API
        jobs = client.list_all_jobs()
        
        # Verify the job status was updated
        refresh_job = next((job for job in jobs if job['id'] == 'abc123-real-job-id'), None)
        assert refresh_job is not None
        assert refresh_job['status'] == 'completed'

    def test_list_jobs_skips_final_and_pending_jobs(self, tmp_path: pathlib.Path, xdg_data_home: pathlib.Path) -> None:
        """Test that list jobs skips API calls for SUCCESS and pending jobs."""
        # Create a client that uses the same temporary data directory as the CLI
        from mistral_ocr.client import MistralOCRClient
        
        # Create client in real mode (not test mode)
        client = MistralOCRClient(api_key="real-api-key")
        client.mock_mode = False  # Force real mode for this test
        
        # Create realistic jobs with different statuses
        real_doc_uuid = "real-doc-uuid-skip"
        client.db.store_document(real_doc_uuid, "Real Document")
        client.db.store_job("real-success-12345", real_doc_uuid, "SUCCESS", 1)
        client.db.store_job("real-pending-67890", real_doc_uuid, "pending", 1)  
        client.db.store_job("real-running-abcde", real_doc_uuid, "running", 1)
        
        # Mock the check_job_status method to track which jobs are checked
        api_calls = []
        original_method = client.check_job_status
        def mock_check_status(job_id):
            api_calls.append(job_id)
            return original_method(job_id)
        
        client.check_job_status = mock_check_status
        
        # Call list_all_jobs - should only refresh running job
        jobs = client.list_all_jobs()
        
        # Verify only the running job was checked via API
        assert "real-running-abcde" in api_calls
        assert "real-success-12345" not in api_calls  # Should be skipped
        assert "real-pending-67890" not in api_calls  # Should be skipped
        
        # Verify all jobs are still returned
        job_ids = {job['id'] for job in jobs}
        assert "real-success-12345" in job_ids
        assert "real-pending-67890" in job_ids
        assert "real-running-abcde" in job_ids

    def test_list_jobs_hides_test_jobs_in_real_mode(self, tmp_path: pathlib.Path, xdg_data_home: pathlib.Path) -> None:
        """Test that test jobs are hidden in real mode but shown in mock mode."""
        from mistral_ocr.client import MistralOCRClient
        
        # Create client in real mode
        client = MistralOCRClient(api_key="real-api-key")
        client.mock_mode = False
        
        # Create a mix of real and test jobs
        test_doc_uuid = "test-doc-uuid-filter"
        real_doc_uuid = "real-doc-uuid"
        client.db.store_document(test_doc_uuid, "Test Document")
        client.db.store_document(real_doc_uuid, "Real Document")
        
        # Add test jobs (should be filtered out)
        client.db.store_job("job_001", test_doc_uuid, "SUCCESS", 1)
        client.db.store_job("test_job_example", test_doc_uuid, "pending", 1)
        client.db.store_job("job123", test_doc_uuid, "completed", 1)
        
        # Add real job (should be shown)
        client.db.store_job("real-job-uuid-12345", real_doc_uuid, "SUCCESS", 1)
        
        # Mock check_job_status to avoid actual API calls
        def mock_check_status(job_id):
            return "SUCCESS"
        client.check_job_status = mock_check_status
        
        # Call list_all_jobs in real mode - should filter test jobs
        jobs = client.list_all_jobs()
        job_ids = {job['id'] for job in jobs}
        
        # Test jobs should be filtered out
        assert "job_001" not in job_ids
        assert "test_job_example" not in job_ids
        assert "job123" not in job_ids
        
        # Real job should be included
        assert "real-job-uuid-12345" in job_ids

    def test_list_jobs_shows_test_jobs_in_mock_mode(self, tmp_path: pathlib.Path, xdg_data_home: pathlib.Path) -> None:
        """Test that test jobs are shown in mock mode for testing purposes."""
        from mistral_ocr.client import MistralOCRClient
        
        # Create client in mock mode
        client = MistralOCRClient(api_key="test")
        assert client.mock_mode == True
        
        # Create test jobs
        test_doc_uuid = "test-doc-uuid-mock"
        client.db.store_document(test_doc_uuid, "Test Document")
        client.db.store_job("job_001", test_doc_uuid, "SUCCESS", 1)
        client.db.store_job("test_job_example", test_doc_uuid, "pending", 1)
        
        # Call list_all_jobs in mock mode - should show test jobs
        jobs = client.list_all_jobs()
        job_ids = {job['id'] for job in jobs}
        
        # Test jobs should be included in mock mode
        assert "job_001" in job_ids
        assert "test_job_example" in job_ids


# Advanced Options and CLI Tests
class TestAdvancedOptions:
    """Tests for advanced options and CLI functionality."""

    def test_specify_custom_model(self, png_file: pathlib.Path, client: MistralOCRClient) -> None:
        job_id = client.submit_documents([png_file], model="test-model")
        assert job_id is not None

    @pytest.mark.parametrize(
        "args,description",
        [
            (["--submit", "file.png"], "CLI submission"),
            (["--check-job", "job123"], "CLI status check"),
            (["--get-results", "job123"], "CLI result retrieval"),
        ],
    )
    def test_command_line_operations(
        self, tmp_path: pathlib.Path, args: list[str], description: str
    ) -> None:
        # Create a test file if needed for submission
        if args[0] == "--submit":
            test_file = tmp_path / "file.png"
            test_file.write_bytes(b"test")
            args[1] = str(test_file)

        result = run_cli(*args)
        assert result.returncode == 0
        assert "job" in result.stdout.lower() or "results" in result.stdout.lower()

    def test_logging_of_errors(self, xdg_data_home: pathlib.Path, client: MistralOCRClient) -> None:
        log_file = xdg_data_home / "mistral-ocr" / "mistral.log"
        with pytest.raises(FileNotFoundError):
            client.submit_documents([pathlib.Path("missing.png")])
        assert log_file.exists()
        assert "File not found" in log_file.read_text()

    def test_batch_processing_for_cost_management(
        self, tmp_path: pathlib.Path, client: MistralOCRClient
    ) -> None:
        files = create_test_files(tmp_path / "docs", count=105)
        job_ids = client.submit_documents(files)
        assert all(len(batch) <= 100 for batch in job_ids)  # type: ignore
