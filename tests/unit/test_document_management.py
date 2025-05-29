"""Document management tests for Mistral OCR."""

import pathlib

import pytest

from mistral_ocr.client import MistralOCRClient


@pytest.fixture
def client(xdg_data_home):
    """Provide a test MistralOCRClient instance with isolated database."""
    return MistralOCRClient(api_key="test")


@pytest.fixture
def png_file(tmp_path):
    """Create a test PNG file."""
    file = tmp_path / "test.png"
    file.write_bytes(b"fakepng")
    return file


@pytest.fixture
def xdg_data_home(tmp_path, monkeypatch):
    """Set XDG_DATA_HOME and XDG_STATE_HOME to tmp_path for testing.

    This ensures both data and state (including database) are isolated to test directories.
    """
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path


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
