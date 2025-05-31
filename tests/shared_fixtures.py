"""Shared test fixtures for simplified Mistral OCR tests."""

import os
import pathlib
import subprocess

import pytest
from factories import ConfigFactory, FileFactory

from mistral_ocr import SimpleMistralOCRClient


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the CLI with the local package path and isolated test environment."""
    env = {**os.environ, **ConfigFactory.create_test_env_vars()}

    # Ensure CLI uses isolated test directories for both data and state
    if "XDG_DATA_HOME" in os.environ:
        env["XDG_DATA_HOME"] = os.environ["XDG_DATA_HOME"]

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
def client(tmp_path):
    """Provide a test SimpleMistralOCRClient instance with isolated database."""
    db_path = str(tmp_path / "test.db")
    return SimpleMistralOCRClient(api_key="test-api-key", db_path=db_path)


@pytest.fixture
def png_file(tmp_path):
    """Create a test PNG file."""
    return FileFactory.create_png_file(tmp_path)


@pytest.fixture
def jpeg_file(tmp_path):
    """Create a test JPEG file."""
    return FileFactory.create_jpg_file(tmp_path)


@pytest.fixture
def pdf_file(tmp_path):
    """Create a test PDF file."""
    return FileFactory.create_pdf_file(tmp_path)


@pytest.fixture
def multiple_test_files(tmp_path):
    """Create multiple test files of different types."""
    return FileFactory.create_multiple_files(tmp_path, count=3)


@pytest.fixture
def isolated_environment(tmp_path, monkeypatch):
    """Set up isolated test environment with temp directories."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
    monkeypatch.setenv("MISTRAL_API_KEY", "test-api-key")
    
    return tmp_path
