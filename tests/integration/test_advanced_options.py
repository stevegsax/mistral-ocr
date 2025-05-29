"""Advanced options and CLI integration tests for Mistral OCR."""

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
