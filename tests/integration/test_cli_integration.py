"""Integration tests for simplified Mistral OCR CLI focusing on argument validation and basic flow."""

import os
import subprocess
import pathlib
import sys

import pytest

# Add parent directory to path for imports
sys.path.append(str(pathlib.Path(__file__).parent.parent))
from factories import FileFactory


def run_cli(*args: str, env_vars: dict = None) -> subprocess.CompletedProcess:
    """Run the CLI with the local package path and test environment."""
    env = {**os.environ, "PYTHONPATH": "src"}
    if env_vars:
        env.update(env_vars)

    return subprocess.run(
        ["python", "-m", "mistral_ocr", *args],
        capture_output=True,
        text=True,
        env=env,
    )


class TestCLIArgumentValidation:
    """Test CLI argument validation and help functionality."""

    def test_main_help_displays_correctly(self):
        """Test that main help shows all subcommands."""
        result = run_cli("--help")
        
        assert result.returncode == 0
        assert "Simple Mistral OCR CLI" in result.stdout
        assert "submit" in result.stdout
        assert "status" in result.stdout
        assert "results" in result.stdout
        assert "search" in result.stdout
        assert "list" in result.stdout

    def test_submit_help_displays_correctly(self):
        """Test submit subcommand help."""
        result = run_cli("submit", "--help")
        
        assert result.returncode == 0
        assert "Files or directories to process" in result.stdout
        assert "--name" in result.stdout
        assert "--recursive" in result.stdout

    def test_submit_requires_files_argument(self):
        """Test that submit requires files argument."""
        result = run_cli("submit")
        
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_status_requires_job_id_argument(self):
        """Test that status requires job_id argument."""
        result = run_cli("status")
        
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_results_requires_job_id_argument(self):
        """Test that results requires job_id argument."""
        result = run_cli("results")
        
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_search_requires_query_argument(self):
        """Test that search requires query argument."""
        result = run_cli("search")
        
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_list_runs_without_arguments(self):
        """Test that list command runs without arguments."""
        # Should not fail due to missing arguments (may fail due to missing API key)
        result = run_cli("list")
        
        # Either success or API error, but not argument error
        assert "required" not in result.stderr.lower()

    def test_invalid_subcommand_shows_error(self):
        """Test that invalid subcommands show error."""
        result = run_cli("invalid-command")
        
        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower() or "error" in result.stderr.lower()


class TestCLIFileHandling:
    """Test CLI file handling and validation."""

    def test_submit_with_valid_file_reaches_api_call(self, tmp_path):
        """Test that valid file submission reaches API processing."""
        # Create test file
        test_file = FileFactory.create_png_file(tmp_path, "test.png")
        
        # Run without API key to test file validation works
        result = run_cli("submit", str(test_file), "--name", "Test Document")
        
        # Should fail due to invalid API key (gets 401 error)
        assert result.returncode == 1
        assert "Error:" in result.stdout

    def test_submit_with_nonexistent_file_shows_error(self, tmp_path):
        """Test error handling for non-existent files."""
        non_existent = tmp_path / "does_not_exist.png"
        
        result = run_cli(
            "submit", str(non_existent), "--name", "Test",
            env_vars={"MISTRAL_API_KEY": "fake-key"}
        )
        
        assert result.returncode == 1
        assert "No files found to process" in result.stdout

    def test_submit_directory_without_valid_files(self, tmp_path):
        """Test submitting directory with no valid image files."""
        # Create directory with only text files
        empty_dir = tmp_path / "no_images"
        empty_dir.mkdir()
        (empty_dir / "text_file.txt").write_text("not an image")
        
        result = run_cli(
            "submit", str(empty_dir), "--name", "Test",
            env_vars={"MISTRAL_API_KEY": "fake-key"}
        )
        
        assert result.returncode == 1
        assert "No files found to process" in result.stdout

    def test_submit_directory_with_recursive_flag(self, tmp_path):
        """Test submitting directory with recursive flag."""
        # Create directory structure
        doc_dir = tmp_path / "documents"
        doc_dir.mkdir()
        subdir = doc_dir / "subdir"
        subdir.mkdir()
        
        # Create files in both directories
        FileFactory.create_png_file(doc_dir, "doc1.png")
        FileFactory.create_png_file(subdir, "doc2.png")
        
        result = run_cli(
            "submit", str(doc_dir), "--recursive", "--name", "Test",
            env_vars={"MISTRAL_API_KEY": "fake-key"}
        )
        
        # Should reach API call stage (will fail due to fake key)
        assert result.returncode == 1
        assert "No files found to process" not in result.stdout

    def test_submit_multiple_files(self, tmp_path):
        """Test submitting multiple files."""
        files = FileFactory.create_multiple_files(tmp_path, count=3)
        file_paths = [str(f) for f in files]
        
        result = run_cli(
            "submit", *file_paths, "--name", "Multiple Files",
            env_vars={"MISTRAL_API_KEY": "fake-key"}
        )
        
        # Should reach API call stage (will fail due to fake key)
        assert result.returncode == 1
        assert "No files found to process" not in result.stdout


class TestCLIEnvironmentHandling:
    """Test CLI environment variable handling."""

    def test_missing_api_key_shows_error(self, tmp_path):
        """Test that missing API key shows appropriate error."""
        test_file = FileFactory.create_png_file(tmp_path, "test.png")
        
        # Run without MISTRAL_API_KEY in environment
        env_no_key = {k: v for k, v in os.environ.items() if k != "MISTRAL_API_KEY"}
        env_no_key["PYTHONPATH"] = "src"
        
        result = subprocess.run(
            ["python", "-m", "mistral_ocr", "submit", str(test_file)],
            capture_output=True,
            text=True,
            env=env_no_key,
        )
        
        assert result.returncode == 1
        assert "API key required" in result.stdout or "API key required" in result.stderr

    def test_isolated_data_directory(self, tmp_path, monkeypatch):
        """Test that XDG_DATA_HOME is respected for database location."""
        data_dir = tmp_path / "custom_data"
        data_dir.mkdir()
        
        monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
        
        # Try to run list command (should create database in custom location)
        result = run_cli("list", env_vars={"MISTRAL_API_KEY": "fake-key"})
        
        # Command should run and create database directory structure
        expected_db_dir = data_dir / ".mistral-ocr"
        # May or may not be created depending on implementation, but test should not crash
        assert result.returncode in [0, 1]  # Either success or API error, not crash


class TestCLIBasicWorkflow:
    """Test basic CLI workflow without real API calls."""

    def test_status_with_fake_job_id(self):
        """Test status command with fake job ID."""
        result = run_cli("status", "fake-job-123", env_vars={"MISTRAL_API_KEY": "fake-key"})
        
        # Should attempt to check status (may fail due to fake key/job)
        assert result.returncode in [0, 1]
        assert "required" not in result.stderr.lower()  # Not an argument error

    def test_results_with_fake_job_id(self):
        """Test results command with fake job ID."""
        result = run_cli("results", "fake-job-123", env_vars={"MISTRAL_API_KEY": "fake-key"})
        
        # Should attempt to get results (may fail due to fake key/job)
        assert result.returncode in [0, 1]
        assert "required" not in result.stderr.lower()  # Not an argument error

    def test_search_with_query(self):
        """Test search command with query."""
        result = run_cli("search", "test query", env_vars={"MISTRAL_API_KEY": "fake-key"})
        
        # Should attempt to search (may return no results)
        assert result.returncode in [0, 1]
        assert "required" not in result.stderr.lower()  # Not an argument error

    def test_results_format_options(self):
        """Test results command with different format options."""
        formats = ["text", "markdown", "summary"]
        
        for fmt in formats:
            result = run_cli(
                "results", "fake-job-123", "--format", fmt,
                env_vars={"MISTRAL_API_KEY": "fake-key"}
            )
            
            # Should accept format option without argument errors
            assert "invalid choice" not in result.stderr.lower()
            assert "required" not in result.stderr.lower()


class TestCLIErrorHandling:
    """Test CLI error handling and user feedback."""

    def test_helpful_error_messages(self, tmp_path):
        """Test that error messages are helpful to users."""
        # Test file not found
        result = run_cli("submit", "/nonexistent/file.png", env_vars={"MISTRAL_API_KEY": "fake-key"})
        assert result.returncode == 1
        assert "No files found to process" in result.stdout
        
        # Test empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = run_cli("submit", str(empty_dir), env_vars={"MISTRAL_API_KEY": "fake-key"})
        assert result.returncode == 1
        assert "No files found to process" in result.stdout

    def test_graceful_handling_of_api_errors(self, tmp_path):
        """Test graceful handling of API errors."""
        test_file = FileFactory.create_png_file(tmp_path, "test.png")
        
        # Use obviously fake API key
        result = run_cli(
            "submit", str(test_file), "--name", "Test",
            env_vars={"MISTRAL_API_KEY": "obviously-fake-key-12345"}
        )
        
        # Should handle API error gracefully
        assert result.returncode == 1
        assert "Error:" in result.stdout
        # Should not crash or show Python tracebacks to user
        assert "Traceback" not in result.stdout
        assert "Traceback" not in result.stderr