"""Tests for CLI subcommand functionality."""

import os
import subprocess

import pytest


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the CLI with the local package path and isolated test environment."""
    env = {**os.environ, "PYTHONPATH": "src", "MISTRAL_API_KEY": "test"}

    # Ensure CLI uses isolated test directories for both data and state
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
class TestCLISubcommands:
    """Tests for CLI subcommand structure and help functionality."""

    def test_main_help_shows_subcommands(self) -> None:
        """Test that main help shows available subcommands."""
        result = run_cli("--help")
        assert result.returncode == 0

        # Check for main subcommands
        assert "submit" in result.stdout
        assert "jobs" in result.stdout
        assert "results" in result.stdout
        assert "documents" in result.stdout
        assert "config" in result.stdout

    def test_submit_subcommand_help(self) -> None:
        """Test submit subcommand help."""
        result = run_cli("submit", "--help")
        assert result.returncode == 0

        # Check for submit-specific options
        assert "path" in result.stdout.lower()
        assert "--recursive" in result.stdout
        assert "--name" in result.stdout
        assert "--uuid" in result.stdout
        assert "--model" in result.stdout

    def test_jobs_subcommand_help(self) -> None:
        """Test jobs subcommand help."""
        result = run_cli("jobs", "--help")
        assert result.returncode == 0

        # Check for jobs sub-subcommands
        assert "list" in result.stdout
        assert "status" in result.stdout
        assert "cancel" in result.stdout

    def test_jobs_status_subcommand_help(self) -> None:
        """Test jobs status subcommand help."""
        result = run_cli("jobs", "status", "--help")
        assert result.returncode == 0

        # Check for job_id parameter
        assert "job_id" in result.stdout.lower()

    def test_results_subcommand_help(self) -> None:
        """Test results subcommand help."""
        result = run_cli("results", "--help")
        assert result.returncode == 0

        # Check for results sub-subcommands
        assert "get" in result.stdout
        assert "download" in result.stdout

    def test_results_download_subcommand_help(self) -> None:
        """Test results download subcommand help."""
        result = run_cli("results", "download", "--help")
        assert result.returncode == 0

        # Check for job_id parameter and output option
        assert "job_id" in result.stdout.lower()
        assert "--output" in result.stdout

    def test_documents_subcommand_help(self) -> None:
        """Test documents subcommand help."""
        result = run_cli("documents", "--help")
        assert result.returncode == 0

        # Check for documents sub-subcommands
        assert "query" in result.stdout
        assert "download" in result.stdout

    def test_config_subcommand_help(self) -> None:
        """Test config subcommand help."""
        result = run_cli("config", "--help")
        assert result.returncode == 0

        # Check for config sub-subcommands
        assert "show" in result.stdout
        assert "reset" in result.stdout
        assert "set" in result.stdout

    def test_config_set_subcommand_help(self) -> None:
        """Test config set subcommand help."""
        result = run_cli("config", "set", "--help")
        assert result.returncode == 0

        # Check for configuration keys
        assert "api-key" in result.stdout
        assert "model" in result.stdout
        assert "download-dir" in result.stdout

    def test_invalid_subcommand_shows_help(self) -> None:
        """Test that invalid subcommands show appropriate help."""
        result = run_cli("invalid-command")
        assert result.returncode != 0
        # Should show main help or error about invalid choice

    def test_subcommand_without_action_shows_help(self) -> None:
        """Test that subcommands without actions show their help."""
        # Test jobs without action
        result = run_cli("jobs")
        assert result.returncode != 0 or "usage" in result.stdout.lower()

        # Test results without action
        result = run_cli("results")
        assert result.returncode != 0 or "usage" in result.stdout.lower()

        # Test documents without action
        result = run_cli("documents")
        assert result.returncode != 0 or "usage" in result.stdout.lower()

        # Test config without action
        result = run_cli("config")
        assert result.returncode != 0 or "usage" in result.stdout.lower()


@pytest.mark.unit
class TestCLIArgumentValidation:
    """Tests for CLI argument validation with new subcommand structure."""

    def test_submit_requires_path(self) -> None:
        """Test that submit subcommand requires a path argument."""
        result = run_cli("submit")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_jobs_status_requires_job_id(self) -> None:
        """Test that jobs status requires job_id argument."""
        result = run_cli("jobs", "status")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_jobs_cancel_requires_job_id(self) -> None:
        """Test that jobs cancel requires job_id argument."""
        result = run_cli("jobs", "cancel")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_results_get_requires_job_id(self) -> None:
        """Test that results get requires job_id argument."""
        result = run_cli("results", "get")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_results_download_requires_job_id(self) -> None:
        """Test that results download requires job_id argument."""
        result = run_cli("results", "download")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_documents_query_requires_name_or_uuid(self) -> None:
        """Test that documents query requires name_or_uuid argument."""
        result = run_cli("documents", "query")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_documents_download_requires_name_or_uuid(self) -> None:
        """Test that documents download requires name_or_uuid argument."""
        result = run_cli("documents", "download")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_config_set_requires_key_and_value(self) -> None:
        """Test that config set requires both key and value arguments."""
        # Test missing both arguments
        result = run_cli("config", "set")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

        # Test missing value argument
        result = run_cli("config", "set", "api-key")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_config_set_validates_key_choices(self) -> None:
        """Test that config set validates key choices."""
        result = run_cli("config", "set", "invalid-key", "some-value")
        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower() or "usage" in result.stderr.lower()
