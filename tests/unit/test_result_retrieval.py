"""Result retrieval tests for Mistral OCR."""

import pathlib

import pytest

from mistral_ocr.client import MistralOCRClient
from mistral_ocr.exceptions import JobNotCompletedError


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


class TestResultRetrieval:
    """Tests for result download and retrieval."""

    def test_retrieve_results_for_completed_job(self, client: MistralOCRClient) -> None:
        results = client.get_results("job123")
        assert isinstance(results, list)

    def test_retrieve_before_completion(self, client: MistralOCRClient) -> None:
        # Reset mock counter to ensure predictable behavior
        from mistral_ocr.result_manager import ResultManager

        ResultManager._mock_get_results_call_count = 0

        # First call returns empty results, second call raises exception (mock behavior)
        client.get_results("job123")
        with pytest.raises(JobNotCompletedError):
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
