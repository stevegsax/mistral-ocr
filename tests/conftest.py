"""Test configuration and fixtures for Mistral OCR tests."""

import pathlib
import tempfile
from typing import Dict, Any
from unittest.mock import Mock, patch
import pytest
from mistral_ocr.client import MistralOCRClient


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
    job.total_requests = 5
    job.input_files = ["file1.png", "file2.jpg"]
    job.output_file = "batch_results.jsonl"
    job.errors = None
    job.metadata = {"model": "pixtral-12b-2409"}
    return job


@pytest.fixture
def mock_api_job_running():
    """Create a mock API job in running state."""
    job = Mock()
    job.id = "test-job-running-456"
    job.status = "running"
    job.created_at = "2024-01-01T10:00:00Z"
    job.completed_at = None
    job.total_requests = 3
    job.input_files = ["file1.png"]
    job.output_file = None
    job.errors = None
    job.metadata = {"model": "pixtral-12b-2409"}
    return job


@pytest.fixture
def mock_api_job_failed():
    """Create a mock API job in failed state."""
    job = Mock()
    job.id = "test-job-failed-789"
    job.status = "failed"
    job.created_at = "2024-01-01T10:00:00Z"
    job.completed_at = "2024-01-01T10:03:00Z"
    job.total_requests = 2
    job.input_files = ["file1.png"]
    job.output_file = None
    job.errors = [{"code": "invalid_file", "message": "File format not supported"}]
    job.metadata = {"model": "pixtral-12b-2409"}
    return job


@pytest.fixture
def mock_batch_jobs_list(mock_api_job, mock_api_job_running, mock_api_job_failed):
    """Create a mock batch jobs list response."""
    mock_response = Mock()
    mock_response.data = [mock_api_job, mock_api_job_running, mock_api_job_failed]
    return mock_response


@pytest.fixture
def mock_mistral_client(mock_api_job, mock_batch_jobs_list):
    """Create a comprehensive mock for the Mistral client."""
    with patch('mistral_ocr.client.Mistral') as mock_mistral:
        # Setup mock client
        mock_client_instance = Mock()
        mock_mistral.return_value = mock_client_instance
        
        # Setup batch operations
        mock_client_instance.batch.jobs.get.return_value = mock_api_job
        mock_client_instance.batch.jobs.list.return_value = mock_batch_jobs_list
        mock_client_instance.batch.jobs.cancel.return_value = Mock(status="cancelled")
        
        # Setup files operations
        mock_client_instance.files.upload.return_value = Mock(id="file-123")
        mock_client_instance.files.download.return_value = b"mock file content"
        
        yield mock_client_instance


@pytest.fixture
def test_client(temp_dir, mock_mistral_client):
    """Create a test MistralOCRClient with mocked dependencies."""
    # Set up temporary directories for testing
    data_dir = temp_dir / "data"
    data_dir.mkdir()
    
    # Create client with mock API key
    client = MistralOCRClient(api_key="test-api-key")
    
    # Override paths to use temp directory
    client.database.db_path = data_dir / "test.db"
    client.database.connect()
    client.database.initialize_schema()
    
    return client


@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "status": "running",
        "created_at": "2024-01-01T10:00:00Z",
        "submitted": "2024-01-01T10:00:00Z",
        "document_name": "Test Document",
        "file_count": 3
    }


@pytest.fixture
def mock_job_status_responses():
    """Mock different job status responses for testing state transitions."""
    return {
        "test-job-pending": "pending",
        "test-job-running": "running", 
        "test-job-completed": "completed",
        "test-job-failed": "failed",
        "test-job-cancelled": "cancelled",
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890": "completed"  # For specific test
    }


@pytest.fixture
def mock_job_status_transition(mock_job_status_responses):
    """Mock that simulates job status transitions."""
    def mock_check_status(job_id: str) -> str:
        return mock_job_status_responses.get(job_id, "running")
    return mock_check_status


@pytest.fixture
def httpx_mock_responses():
    """Predefined HTTP responses for httpx mocking."""
    return {
        "GET https://api.mistral.ai/v1/batch/jobs/test-job-id": {
            "json": {
                "id": "test-job-id",
                "status": "completed",
                "created_at": "2024-01-01T10:00:00Z",
                "completed_at": "2024-01-01T10:05:00Z"
            }
        },
        "GET https://api.mistral.ai/v1/batch/jobs": {
            "json": {
                "data": [
                    {
                        "id": "job-1",
                        "status": "completed",
                        "created_at": "2024-01-01T10:00:00Z"
                    },
                    {
                        "id": "job-2", 
                        "status": "running",
                        "created_at": "2024-01-01T10:05:00Z"
                    }
                ]
            }
        }
    }


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, temp_dir):
    """Automatically set up test environment for all tests."""
    # Set environment variables for testing
    monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(temp_dir / "state"))
    monkeypatch.setenv("MISTRAL_API_KEY", "test-api-key")