"""Basic integrity tests for Mistral OCR."""

import os
import pathlib
import subprocess

import pytest

from mistral_ocr.config import ConfigurationManager
from mistral_ocr.database import Database
from mistral_ocr.logging import get_logger, setup_logging


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


@pytest.mark.unit
class TestBasicIntegrity:
    """Tests for basic system integrity and setup."""

    def test_display_help_message(self) -> None:
        result = run_cli("--help")
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()

    def test_version_command(self) -> None:
        result = run_cli("--version")
        assert result.returncode == 0
        assert "mistral-ocr" in result.stdout
        assert "0.2.0" in result.stdout

    def test_configuration_availability(self) -> None:
        config = ConfigurationManager()
        assert config is not None

    def test_log_file_creation(self, tmp_path: pathlib.Path) -> None:
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        log_file = setup_logging(log_dir)
        logger = get_logger("test")
        logger.error("test message")
        assert log_file.exists()
        assert "test message" in log_file.read_text()

    def test_database_connectivity(self, tmp_path: pathlib.Path) -> None:
        db = Database(tmp_path / "test.db")
        db.connect()
        db.execute("CREATE TABLE example (name TEXT)")
        db.execute("INSERT INTO example (name) VALUES ('abc')")
        result = db.execute("SELECT name FROM example LIMIT 1")
        assert result == "abc"
