"""Shared test fixtures for Mistral OCR tests."""

import os
import pathlib
import subprocess

import pytest
from factories import ConfigFactory, FileFactory

from mistral_ocr.client import MistralOCRClient


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the CLI with the local package path and isolated test environment."""
    env = {**os.environ, **ConfigFactory.create_test_env_vars()}

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
def large_file_set(tmp_path):
    """Create a large set of files for batch testing."""
    return FileFactory.create_large_file_set(tmp_path, count=150)


@pytest.fixture
def xdg_data_home(tmp_path, monkeypatch):
    """Set XDG_DATA_HOME and XDG_STATE_HOME to tmp_path for testing.

    This ensures both data and state (including database) are isolated to test directories.
    """
    paths = ConfigFactory.create_isolated_paths(tmp_path)
    for key, value in paths.items():
        monkeypatch.setenv(key, value)
    return tmp_path
