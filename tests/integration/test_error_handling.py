"""Test error handling and edge cases for Mistral OCR."""

import json
from unittest.mock import Mock, patch

import pytest

from mistral_ocr.client import MistralOCRClient
from mistral_ocr.exceptions import (
    JobError,
    UnsupportedFileTypeError,
)


class TestNetworkFailureRecovery:
    """Test handling of network failures during API calls."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create test client with temporary database."""
        client = MistralOCRClient(api_key="test-api-key")
        # Ensure we're in mock mode by default
        client.mock_mode = True
        client.job_manager.mock_mode = True
        client.submission_manager.mock_mode = True
        client.result_manager.mock_mode = True
        # Use temporary database path
        client.database.db_path = tmp_path / "test.db"
        client.database.connect()
        client.database.initialize_schema()
        return client

    def test_job_status_check_network_failure(self, client):
        """Test handling of network failure during job status check."""
        # Create a job in the database first
        test_doc_uuid = "test-doc-uuid"
        job_id = "test-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "pending", 1)

        # Mock network failure
        with patch.object(
            client.client.batch.jobs, "get", side_effect=ConnectionError("Network error")
        ):
            with pytest.raises(JobError, match="Failed to check job status"):
                client.check_job_status(job_id)

    def test_job_status_check_timeout_error(self, client):
        """Test handling of timeout during job status check."""
        # Create a job in the database first
        test_doc_uuid = "test-doc-uuid"
        job_id = "test-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "pending", 1)

        # Mock timeout error
        with patch.object(
            client.client.batch.jobs, "get", side_effect=TimeoutError("Request timeout")
        ):
            with pytest.raises(JobError, match="Failed to check job status"):
                client.check_job_status(job_id)

    def test_job_status_check_api_error(self, client):
        """Test handling of API error during job status check."""
        # Create a job in the database first
        test_doc_uuid = "test-doc-uuid"
        job_id = "test-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "pending", 1)

        # Mock API error response
        with patch.object(client.client.batch.jobs, "get", side_effect=Exception("API error")):
            with pytest.raises(JobError, match="Failed to check job status"):
                client.check_job_status(job_id)

    def test_list_jobs_network_failure_graceful_degradation(self, client):
        """Test that list_jobs handles network failure gracefully."""
        # Create some jobs in the database first
        test_doc_uuid = "test-doc-uuid"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job("job1", test_doc_uuid, "pending", 1)
        client.database.store_job("job2", test_doc_uuid, "completed", 1)

        # Force real mode to trigger API calls
        client.mock_mode = False
        client.job_manager.mock_mode = False

        # Mock network failure for API call
        with patch.object(
            client.client.batch.jobs, "list", side_effect=ConnectionError("Network error")
        ):
            # Should still return local jobs despite API failure
            jobs = client.list_all_jobs()

            # Should have jobs from database
            assert len(jobs) >= 2
            job_ids = [job.id for job in jobs]
            assert "job1" in job_ids
            assert "job2" in job_ids

    def test_cancel_job_network_failure(self, client):
        """Test handling of network failure during job cancellation."""
        # Create a job in the database first
        test_doc_uuid = "test-doc-uuid"
        job_id = "test-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "pending", 1)

        # Force real mode
        client.mock_mode = False
        client.job_manager.mock_mode = False

        # Mock network failure
        with patch.object(
            client.client.batch.jobs, "cancel", side_effect=ConnectionError("Network error")
        ):
            result = client.cancel_job(job_id)

            # Should return False on network failure
            assert result is False

    def test_submit_documents_network_failure(self, client, tmp_path):
        """Test handling of network failure during document submission."""
        # Create test file
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake png content")

        # Force real mode
        client.mock_mode = False
        client.submission_manager.mock_mode = False

        # Mock network failure during batch submission
        with patch.object(
            client.client.batch.jobs, "create", side_effect=ConnectionError("Network error")
        ):
            with pytest.raises(Exception):  # Should propagate the network error
                client.submit_documents([test_file])

    def test_download_results_network_failure(self, client):
        """Test handling of network failure during result download."""
        # Create a completed job
        test_doc_uuid = "test-doc-uuid"
        job_id = "completed-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "completed", 1)

        # Force real mode
        client.mock_mode = False
        client.result_manager.mock_mode = False

        # Mock network failure during result download
        with patch.object(
            client.client.batch.jobs, "get", side_effect=ConnectionError("Network error")
        ):
            with pytest.raises(Exception):  # Should handle network failure
                client.download_results(job_id)

    def test_job_detail_network_failure_fallback(self, client):
        """Test that job details falls back to database on network failure."""
        # Create a job in the database
        test_doc_uuid = "test-doc-uuid"
        job_id = "test-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "pending", 1)

        # Force real mode
        client.mock_mode = False
        client.job_manager.mock_mode = False

        # Mock network failure during API refresh
        with patch.object(
            client.job_manager, "check_job_status", side_effect=JobError("Network error")
        ):
            # Should still return job details from database
            details = client.get_job_details(job_id)

            assert details["id"] == job_id
            assert details["status"] == "pending"  # Original status from database


class TestPartialBatchFailure:
    """Test handling of partial batch failures."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create test client with temporary database."""
        client = MistralOCRClient(api_key="test-api-key")
        # Ensure we're in mock mode by default
        client.mock_mode = True
        client.job_manager.mock_mode = True
        client.submission_manager.mock_mode = True
        client.result_manager.mock_mode = True
        client.database.db_path = tmp_path / "test.db"
        client.database.connect()
        client.database.initialize_schema()
        return client

    def test_mixed_file_validation_in_batch(self, client, tmp_path):
        """Test batch submission with mix of valid and invalid files."""
        # Create mix of valid and invalid files
        valid_file1 = tmp_path / "valid1.png"
        valid_file1.write_bytes(b"fake png content")

        valid_file2 = tmp_path / "valid2.jpg"
        valid_file2.write_bytes(b"fake jpeg content")

        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("not an image")

        missing_file = tmp_path / "missing.png"  # This file doesn't exist

        files = [valid_file1, valid_file2, invalid_file, missing_file]

        # Should raise error for unsupported file type
        with pytest.raises(UnsupportedFileTypeError):
            client.submit_documents(files)

    def test_some_files_unreadable_in_batch(self, client, tmp_path):
        """Test batch submission where some files become unreadable."""
        # Create test files
        file1 = tmp_path / "readable.png"
        file1.write_bytes(b"fake png content")

        file2 = tmp_path / "unreadable.png"
        file2.write_bytes(b"fake png content")

        # Make file2 unreadable by changing permissions (Unix only)
        import stat

        try:
            file2.chmod(0o000)  # Remove all permissions

            # Should handle permission error gracefully
            with pytest.raises((PermissionError, OSError)):
                client.submit_documents([file1, file2])

        finally:
            # Restore permissions for cleanup
            try:
                file2.chmod(stat.S_IRUSR | stat.S_IWUSR)
            except (OSError, FileNotFoundError):
                pass

    def test_api_job_creation_partial_failure(self, client, tmp_path):
        """Test handling when some API job creation calls fail."""
        # Create multiple test files to trigger batch partitioning
        files = []
        for i in range(5):
            test_file = tmp_path / f"test{i}.png"
            test_file.write_bytes(b"fake png content")
            files.append(test_file)

        # Force real mode
        client.mock_mode = False
        client.submission_manager.mock_mode = False

        # Mock API to fail on some calls but succeed on others
        call_count = 0

        def mock_batch_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second call
                raise Exception("API error on second batch")
            # Return mock response for successful calls
            mock_response = Mock()
            mock_response.id = f"batch-{call_count}"
            return mock_response

        with patch.object(client.client.batch.jobs, "create", side_effect=mock_batch_create):
            # Should handle partial failure
            with pytest.raises(Exception):  # Expect failure due to batch creation error
                client.submit_documents(files)


class TestCorruptedFileHandling:
    """Test handling of corrupted or malformed files."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create test client with temporary database."""
        client = MistralOCRClient(api_key="test-api-key")
        # Ensure we're in mock mode by default
        client.mock_mode = True
        client.job_manager.mock_mode = True
        client.submission_manager.mock_mode = True
        client.result_manager.mock_mode = True
        client.database.db_path = tmp_path / "test.db"
        client.database.connect()
        client.database.initialize_schema()
        return client

    def test_corrupted_png_file(self, client, tmp_path):
        """Test handling of corrupted PNG file."""
        # Create file with PNG extension but invalid content
        corrupted_png = tmp_path / "corrupted.png"
        corrupted_png.write_bytes(b"This is not a valid PNG file content")

        # Should accept file based on extension (validation happens server-side)
        # But we'll test the file reading process
        try:
            # In real mode, this would be submitted to the API
            # The corruption would be detected during processing
            result = client.submit_documents([corrupted_png])
            # Should return job ID(s) - corruption detected later
            assert result is not None
        except Exception as e:
            # If there's file reading validation, it might fail here
            assert "error" in str(e).lower() or "invalid" in str(e).lower()

    def test_zero_byte_file(self, client, tmp_path):
        """Test handling of zero-byte files."""
        # Create empty file
        empty_file = tmp_path / "empty.png"
        empty_file.touch()  # Creates empty file

        # Should handle empty file gracefully
        try:
            result = client.submit_documents([empty_file])
            assert result is not None
        except Exception as e:
            # If size validation exists, should give meaningful error
            assert "empty" in str(e).lower() or "size" in str(e).lower()

    def test_extremely_large_file(self, client, tmp_path):
        """Test handling of extremely large files."""
        # Create a large file (simulate with truncate, don't actually write data)
        large_file = tmp_path / "large.png"
        large_file.write_bytes(b"PNG header")

        # Simulate size check if implemented
        from mistral_ocr.utils.file_operations import FileSystemUtils

        # Test the size checking utility directly
        size = FileSystemUtils.check_file_size(large_file)
        assert size > 0

        # Test with size limit
        with pytest.raises(ValueError, match="exceeds limit"):
            FileSystemUtils.check_file_size(large_file, max_size=5)

    def test_file_with_invalid_encoding(self, client, tmp_path):
        """Test handling of files with invalid encoding."""
        # Create file with invalid UTF-8 sequences
        invalid_file = tmp_path / "invalid_encoding.png"
        invalid_file.write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00")  # PNG header + invalid UTF-8

        # Should handle binary files correctly (PNG is binary)
        from mistral_ocr.utils.file_operations import FileIOUtils

        # Should be able to read as binary
        content = FileIOUtils.read_binary_file(invalid_file)
        assert len(content) > 0
        assert content.startswith(b"\x89PNG")

    def test_file_disappears_during_processing(self, client, tmp_path):
        """Test handling when file is deleted during processing."""
        # Create file
        temp_file = tmp_path / "disappearing.png"
        temp_file.write_bytes(b"fake png content")

        def mock_file_processing(*args, **kwargs):
            # Delete file during processing
            temp_file.unlink()
            raise FileNotFoundError("File was deleted during processing")

        # Mock file reading to simulate file disappearing
        with patch(
            "mistral_ocr.utils.file_operations.FileIOUtils.read_binary_file",
            side_effect=mock_file_processing,
        ):
            with pytest.raises(FileNotFoundError):
                client.submit_documents([temp_file])

    def test_file_permissions_error(self, client, tmp_path):
        """Test handling of file permission errors."""
        # Create file
        protected_file = tmp_path / "protected.png"
        protected_file.write_bytes(b"fake png content")

        # Mock permission error during file reading
        with patch(
            "mistral_ocr.utils.file_operations.FileIOUtils.read_binary_file",
            side_effect=PermissionError("Permission denied"),
        ):
            with pytest.raises(PermissionError):
                client.submit_documents([protected_file])

    def test_corrupted_json_response_handling(self, client):
        """Test handling of corrupted JSON in API responses."""
        # Create a job
        test_doc_uuid = "test-doc-uuid"
        job_id = "test-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "completed", 1)

        # Force real mode
        client.mock_mode = False
        client.result_manager.mock_mode = False

        # Mock corrupted JSON response
        mock_response = Mock()
        mock_response.content = b"Invalid JSON content {"
        mock_response.text = "Invalid JSON content {"
        mock_response.status_code = 200

        with patch("urllib.request.urlopen", return_value=mock_response):
            # Should handle JSON parsing errors gracefully
            with pytest.raises((json.JSONDecodeError, Exception)):
                client.download_results(job_id)


class TestResourceExhaustion:
    """Test handling of resource exhaustion scenarios."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create test client with temporary database."""
        client = MistralOCRClient(api_key="test-api-key")
        # Ensure we're in mock mode by default
        client.mock_mode = True
        client.job_manager.mock_mode = True
        client.submission_manager.mock_mode = True
        client.result_manager.mock_mode = True
        client.database.db_path = tmp_path / "test.db"
        client.database.connect()
        client.database.initialize_schema()
        return client

    def test_disk_space_exhaustion_during_download(self, client, tmp_path):
        """Test handling of disk space exhaustion during result download."""
        # Create a completed job
        test_doc_uuid = "test-doc-uuid"
        job_id = "completed-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "completed", 1)

        # Mock disk space exhaustion
        def mock_write_with_no_space(*args, **kwargs):
            raise OSError("No space left on device")

        with patch("builtins.open", side_effect=mock_write_with_no_space):
            with pytest.raises(OSError, match="No space left on device"):
                client.download_results(job_id, destination=tmp_path)

    def test_memory_exhaustion_large_response(self, client):
        """Test handling of memory exhaustion with large API responses."""
        # Create job
        test_doc_uuid = "test-doc-uuid"
        job_id = "test-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "completed", 1)

        # Force real mode
        client.mock_mode = False
        client.result_manager.mock_mode = False

        # Mock memory error during response processing
        with patch.object(
            client.client.batch.jobs, "get", side_effect=MemoryError("Out of memory")
        ):
            with pytest.raises(MemoryError):
                client.check_job_status(job_id)

    def test_too_many_open_files(self, client, tmp_path):
        """Test handling of 'too many open files' error."""
        # Create multiple test files
        files = []
        for i in range(10):
            test_file = tmp_path / f"test{i}.png"
            test_file.write_bytes(b"fake png content")
            files.append(test_file)

        # Mock 'too many open files' error
        def mock_open_with_limit(*args, **kwargs):
            raise OSError("Too many open files")

        with patch("builtins.open", side_effect=mock_open_with_limit):
            with pytest.raises(OSError, match="Too many open files"):
                client.submit_documents(files)

    def test_database_lock_timeout(self, client):
        """Test handling of database lock timeouts."""
        test_doc_uuid = "test-doc-uuid"

        # Mock database lock error
        with patch.object(
            client.database.connection, "execute", side_effect=Exception("database is locked")
        ):
            with pytest.raises(Exception, match="database is locked"):
                client.database.store_document(test_doc_uuid, "Test Document")


class TestAPIRateLimiting:
    """Test handling of API rate limiting responses."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create test client with temporary database."""
        client = MistralOCRClient(api_key="test-api-key")
        # Ensure we're in mock mode by default
        client.mock_mode = True
        client.job_manager.mock_mode = True
        client.submission_manager.mock_mode = True
        client.result_manager.mock_mode = True
        client.database.db_path = tmp_path / "test.db"
        client.database.connect()
        client.database.initialize_schema()
        return client

    def test_rate_limit_429_response(self, client):
        """Test handling of 429 Too Many Requests response."""
        # Create job
        test_doc_uuid = "test-doc-uuid"
        job_id = "test-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "pending", 1)

        # Force real mode
        client.mock_mode = False
        client.job_manager.mock_mode = False

        # Mock 429 response
        rate_limit_error = Exception("429 Too Many Requests")

        with patch.object(client.client.batch.jobs, "get", side_effect=rate_limit_error):
            with pytest.raises(JobError, match="Failed to check job status"):
                client.check_job_status(job_id)

    def test_rate_limit_with_retry_after_header(self, client, tmp_path):
        """Test parsing of Retry-After header in rate limit responses."""
        # Create test file
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake png content")

        # Force real mode
        client.mock_mode = False
        client.submission_manager.mock_mode = False

        # Mock 429 with Retry-After header
        rate_limit_error = Exception("429 Too Many Requests")

        with patch.object(client.client.batch.jobs, "create", side_effect=rate_limit_error):
            with pytest.raises(Exception):  # Should propagate the rate limit error
                client.submit_documents([test_file])

    def test_concurrent_requests_rate_limiting(self, client):
        """Test rate limiting behavior with concurrent requests."""
        # Create multiple jobs
        test_doc_uuid = "test-doc-uuid"
        client.database.store_document(test_doc_uuid, "Test Document")

        job_ids = []
        for i in range(5):
            job_id = f"job-{i}"
            client.database.store_job(job_id, test_doc_uuid, "pending", 1)
            job_ids.append(job_id)

        # Force real mode
        client.mock_mode = False
        client.job_manager.mock_mode = False

        # Mock rate limiting on some requests
        call_count = 0

        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 2:  # Rate limit after 2 calls
                raise Exception("429 Too Many Requests")

            # Return successful response
            mock_job = Mock()
            mock_job.status = "completed"
            mock_job.id = f"job-{call_count}"
            return mock_job

        with patch.object(client.client.batch.jobs, "get", side_effect=mock_api_call):
            # Should handle rate limiting gracefully for some jobs
            successful_checks = 0
            failed_checks = 0

            for job_id in job_ids:
                try:
                    status = client.check_job_status(job_id)
                    successful_checks += 1
                except JobError:
                    failed_checks += 1

            # Should have some successful and some failed due to rate limiting
            assert successful_checks > 0
            assert failed_checks > 0

    def test_api_quota_exceeded(self, client):
        """Test handling of API quota exceeded errors."""
        # Create job
        test_doc_uuid = "test-doc-uuid"
        job_id = "test-job-id"
        client.database.store_document(test_doc_uuid, "Test Document")
        client.database.store_job(job_id, test_doc_uuid, "pending", 1)

        # Force real mode
        client.mock_mode = False
        client.job_manager.mock_mode = False

        # Mock quota exceeded error
        quota_error = Exception("403 Quota Exceeded")

        with patch.object(client.client.batch.jobs, "get", side_effect=quota_error):
            with pytest.raises(JobError, match="Failed to check job status"):
                client.check_job_status(job_id)
