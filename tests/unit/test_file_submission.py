"""File submission tests for Mistral OCR."""

import pathlib

import pytest

from mistral_ocr.client import MistralOCRClient
from mistral_ocr.exceptions import UnsupportedFileTypeError


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


@pytest.mark.unit
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
        with pytest.raises(UnsupportedFileTypeError):
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
