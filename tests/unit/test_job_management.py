"""Job management tests for Mistral OCR."""

import pytest

from mistral_ocr.client import MistralOCRClient
from mistral_ocr.exceptions import InvalidJobIdError


@pytest.fixture
def client(xdg_data_home):
    """Provide a test MistralOCRClient instance with isolated database."""
    return MistralOCRClient(api_key="test")


@pytest.fixture
def xdg_data_home(tmp_path, monkeypatch):
    """Set XDG_DATA_HOME and XDG_STATE_HOME to tmp_path for testing.

    This ensures both data and state (including database) are isolated to test directories.
    """
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path


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
        with pytest.raises(InvalidJobIdError):
            client.check_job_status("invalid")
