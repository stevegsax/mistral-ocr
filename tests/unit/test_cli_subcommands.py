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
class TestSimplifiedCLISubcommands:
    """Tests for simplified CLI subcommand structure and help functionality."""

    def test_main_help_shows_subcommands(self) -> None:
        """Test that main help shows available subcommands."""
        result = run_cli("--help")
        assert result.returncode == 0

        # Check for simplified subcommands
        assert "submit" in result.stdout
        assert "status" in result.stdout
        assert "results" in result.stdout
        assert "search" in result.stdout
        assert "list" in result.stdout

    def test_submit_subcommand_help(self) -> None:
        """Test submit subcommand help."""
        result = run_cli("submit", "--help")
        assert result.returncode == 0

        # Check for submit-specific options
        assert "files" in result.stdout.lower()
        assert "--name" in result.stdout
        assert "--recursive" in result.stdout

    def test_status_subcommand_help(self) -> None:
        """Test status subcommand help."""
        result = run_cli("status", "--help")
        assert result.returncode == 0

        # Check for job_id parameter
        assert "job_id" in result.stdout.lower()

    def test_results_subcommand_help(self) -> None:
        """Test results subcommand help."""
        result = run_cli("results", "--help")
        assert result.returncode == 0

        # Check for job_id parameter and format option
        assert "job_id" in result.stdout.lower()
        assert "--format" in result.stdout

    def test_search_subcommand_help(self) -> None:
        """Test search subcommand help."""
        result = run_cli("search", "--help")
        assert result.returncode == 0

        # Check for query parameter
        assert "query" in result.stdout.lower()

    def test_list_subcommand_help(self) -> None:
        """Test list subcommand help."""
        result = run_cli("list", "--help")
        assert result.returncode == 0

        # Should show help for listing jobs
        assert "List all jobs" in result.stdout or "list" in result.stdout.lower()

    def test_invalid_subcommand_shows_help(self) -> None:
        """Test that invalid subcommands show appropriate help."""
        result = run_cli("invalid-command")
        assert result.returncode != 0
        # Should show error about invalid choice


@pytest.mark.unit
class TestSimplifiedCLIArgumentValidation:
    """Tests for simplified CLI argument validation."""

    def test_submit_requires_files(self) -> None:
        """Test that submit subcommand requires files argument."""
        result = run_cli("submit")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_status_requires_job_id(self) -> None:
        """Test that status requires job_id argument."""
        result = run_cli("status")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_results_requires_job_id(self) -> None:
        """Test that results requires job_id argument."""
        result = run_cli("results")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_search_requires_query(self) -> None:
        """Test that search requires query argument."""
        result = run_cli("search")
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_list_runs_without_arguments(self) -> None:
        """Test that list command runs without arguments."""
        result = run_cli("list")
        # This should work (though may fail due to no API key, but shouldn't be argument error)
        # Either success or error about API/database, not argument error
        assert "required" not in result.stderr.lower() or result.returncode == 0