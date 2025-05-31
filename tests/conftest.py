"""Test configuration and fixtures for simplified Mistral OCR tests."""

import pathlib
import tempfile
from unittest.mock import Mock, patch

import pytest

from mistral_ocr import SimpleMistralOCRClient


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield pathlib.Path(tmp_dir)


@pytest.fixture
def mock_api_job():
    """Create a mock API job response."""
    job = Mock()
    job.id = "test-job-id-123"
    job.status = "completed"
    job.created_at = "2024-01-01T10:00:00Z"
    job.completed_at = "2024-01-01T10:05:00Z"
    job.output_file = "batch_results.jsonl"
    job.errors = None
    return job


@pytest.fixture
def mock_api_job_running():
    """Create a mock API job in running state."""
    job = Mock()
    job.id = "test-job-running-456"
    job.status = "running"
    job.created_at = "2024-01-01T10:00:00Z"
    job.completed_at = None
    job.output_file = None
    job.errors = None
    return job


@pytest.fixture
def mock_api_job_failed():
    """Create a mock API job in failed state."""
    job = Mock()
    job.id = "test-job-failed-789"
    job.status = "failed"
    job.created_at = "2024-01-01T10:00:00Z"
    job.completed_at = "2024-01-01T10:03:00Z"
    job.output_file = None
    job.errors = [{"code": "invalid_file", "message": "File format not supported"}]
    return job


@pytest.fixture
def mock_mistral_client():
    """Create a mock for the Mistral client."""
    with patch("mistral_ocr.simple_client.Mistral") as mock_mistral:
        mock_client_instance = Mock()
        mock_mistral.return_value = mock_client_instance

        # Setup basic operations
        mock_client_instance.files.upload.return_value = Mock(id="file-123")
        mock_client_instance.files.download.return_value = Mock()
        mock_client_instance.batch.jobs.create.return_value = Mock(id="job-123")
        mock_client_instance.batch.jobs.get.return_value = Mock(status="completed")

        yield mock_client_instance


@pytest.fixture
def test_client(temp_dir):
    """Create a test SimpleMistralOCRClient with isolated database."""
    db_path = str(temp_dir / "test.db")
    client = SimpleMistralOCRClient(api_key="test-api-key", db_path=db_path)
    yield client
    client.db.close()


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, temp_dir):
    """Automatically set up test environment for all tests."""
    monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir / "data"))
    monkeypatch.setenv("MISTRAL_API_KEY", "test-api-key")
