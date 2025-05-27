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
