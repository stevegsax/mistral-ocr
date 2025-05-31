"""Tests for SimpleMistralOCRClient functionality."""

import json
import pathlib
import sqlite3
import tempfile
from unittest.mock import Mock, patch

import pytest

from mistral_ocr import SimpleMistralOCRClient


class TestOCRDatabase:
    """Tests for the OCRDatabase component."""

    def test_database_initialization(self, tmp_path):
        """Test database initialization creates schema."""
        from mistral_ocr.simple_client import OCRDatabase
        
        db_path = str(tmp_path / "test.db")
        db = OCRDatabase(db_path)
        
        # Check tables exist
        cursor = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "documents" in tables
        assert "jobs" in tables
        assert "results" in tables
        
        db.close()

    def test_add_document(self, tmp_path):
        """Test adding a document."""
        from mistral_ocr.simple_client import OCRDatabase
        
        db_path = str(tmp_path / "test.db")
        db = OCRDatabase(db_path)
        
        doc_id = db.add_document("Test Document")
        assert isinstance(doc_id, int)
        assert doc_id > 0
        
        db.close()

    def test_add_job(self, tmp_path):
        """Test adding a job."""
        from mistral_ocr.simple_client import OCRDatabase
        
        db_path = str(tmp_path / "test.db")
        db = OCRDatabase(db_path)
        
        doc_id = db.add_document("Test Document")
        db.add_job("job-123", doc_id)
        
        job = db.get_job("job-123")
        assert job is not None
        assert job["job_id"] == "job-123"
        assert job["document_name"] == "Test Document"
        
        db.close()

    def test_add_result(self, tmp_path):
        """Test adding OCR results."""
        from mistral_ocr.simple_client import OCRDatabase
        
        db_path = str(tmp_path / "test.db")
        db = OCRDatabase(db_path)
        
        doc_id = db.add_document("Test Document")
        db.add_job("job-123", doc_id)
        db.add_result("job-123", "test.png", "Extracted text", "# OCR Result\n\nExtracted text")
        
        results = db.get_results("job-123")
        assert len(results) == 1
        assert results[0]["file_name"] == "test.png"
        assert results[0]["text_content"] == "Extracted text"
        assert results[0]["markdown_content"] == "# OCR Result\n\nExtracted text"
        
        db.close()

    def test_search_content(self, tmp_path):
        """Test searching OCR content."""
        from mistral_ocr.simple_client import OCRDatabase
        
        db_path = str(tmp_path / "test.db")
        db = OCRDatabase(db_path)
        
        doc_id = db.add_document("Test Document")
        db.add_job("job-123", doc_id)
        db.add_result("job-123", "test.png", "Invoice total: $100", "# Invoice\n\nTotal: $100")
        
        # Search for content
        results = db.search_content("invoice")
        assert len(results) == 1
        assert results[0]["file_name"] == "test.png"
        
        # Search for content not present
        results = db.search_content("receipt")
        assert len(results) == 0
        
        db.close()

    def test_list_jobs(self, tmp_path):
        """Test listing all jobs."""
        from mistral_ocr.simple_client import OCRDatabase
        
        db_path = str(tmp_path / "test.db")
        db = OCRDatabase(db_path)
        
        doc_id = db.add_document("Test Document")
        db.add_job("job-123", doc_id)
        db.add_job("job-456", doc_id)
        
        jobs = db.list_jobs()
        assert len(jobs) == 2
        job_ids = [job["job_id"] for job in jobs]
        assert "job-123" in job_ids
        assert "job-456" in job_ids
        
        db.close()


class TestSimpleMistralOCRClient:
    """Tests for SimpleMistralOCRClient functionality."""

    def test_client_initialization_with_api_key(self, tmp_path):
        """Test client initialization with API key."""
        db_path = str(tmp_path / "test.db")
        client = SimpleMistralOCRClient(api_key="test-key", db_path=db_path)
        
        assert client.api_key == "test-key"
        assert client.db is not None
        assert client.client is not None
        
        client.db.close()

    def test_client_initialization_without_api_key(self, tmp_path, monkeypatch):
        """Test client initialization without API key raises error."""
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        db_path = str(tmp_path / "test.db")
        
        with pytest.raises(ValueError, match="API key required"):
            SimpleMistralOCRClient(db_path=db_path)

    def test_client_initialization_with_env_api_key(self, tmp_path, monkeypatch):
        """Test client initialization using environment variable."""
        monkeypatch.setenv("MISTRAL_API_KEY", "env-key")
        db_path = str(tmp_path / "test.db")
        
        client = SimpleMistralOCRClient(db_path=db_path)
        assert client.api_key == "env-key"
        
        client.db.close()

    @patch('mistral_ocr.simple_client.Mistral')
    def test_submit_files_success(self, mock_mistral, tmp_path):
        """Test successful file submission."""
        # Setup mocks
        mock_client = Mock()
        mock_mistral.return_value = mock_client
        
        # Mock file upload
        upload_response = Mock()
        upload_response.id = "file-123"
        mock_client.files.upload.return_value = upload_response
        
        # Mock batch job creation
        batch_job = Mock()
        batch_job.id = "job-abc123"
        mock_client.batch.jobs.create.return_value = batch_job
        
        # Create test files
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake png content")
        
        db_path = str(tmp_path / "test.db")
        client = SimpleMistralOCRClient(api_key="test-key", db_path=db_path)
        
        # Submit files
        job_id = client.submit([test_file], "Test Document")
        
        assert job_id == "job-abc123"
        
        # Verify database entry
        job = client.db.get_job(job_id)
        assert job is not None
        assert job["document_name"] == "Test Document"
        
        client.db.close()

    @patch('mistral_ocr.simple_client.Mistral')
    def test_status_check(self, mock_mistral, tmp_path):
        """Test job status checking."""
        # Setup mocks
        mock_client = Mock()
        mock_mistral.return_value = mock_client
        
        batch_job = Mock()
        batch_job.status = "completed"
        mock_client.batch.jobs.get.return_value = batch_job
        
        db_path = str(tmp_path / "test.db")
        client = SimpleMistralOCRClient(api_key="test-key", db_path=db_path)
        
        # Add job to database first
        doc_id = client.db.add_document("Test Document")
        client.db.add_job("job-123", doc_id)
        
        status = client.status("job-123")
        assert status == "completed"
        
        client.db.close()

    @patch('mistral_ocr.simple_client.Mistral')
    def test_results_retrieval(self, mock_mistral, tmp_path):
        """Test retrieving job results."""
        # Setup mocks
        mock_client = Mock()
        mock_mistral.return_value = mock_client
        
        # Mock batch job
        batch_job = Mock()
        batch_job.status = "completed"
        batch_job.output_file = "output-123"
        mock_client.batch.jobs.get.return_value = batch_job
        
        # Mock file download
        output_content = json.dumps({
            "custom_id": "test.png",
            "response": {
                "body": {
                    "choices": [
                        {
                            "message": {
                                "content": "Extracted text from image"
                            }
                        }
                    ]
                }
            }
        })
        
        download_response = Mock()
        download_response.read.return_value = output_content.encode("utf-8")
        mock_client.files.download.return_value = download_response
        
        db_path = str(tmp_path / "test.db")
        client = SimpleMistralOCRClient(api_key="test-key", db_path=db_path)
        
        # Add job to database first
        doc_id = client.db.add_document("Test Document")
        client.db.add_job("job-123", doc_id)
        
        results = client.results("job-123")
        
        assert len(results) == 1
        assert results[0]["file_name"] == "test.png"
        assert results[0]["text_content"] == "Extracted text from image"
        
        # Verify results are stored in database
        db_results = client.db.get_results("job-123")
        assert len(db_results) == 1
        assert db_results[0]["text_content"] == "Extracted text from image"
        
        client.db.close()

    @patch('mistral_ocr.simple_client.Mistral')
    def test_results_cached_retrieval(self, mock_mistral, tmp_path):
        """Test that cached results are returned without API call."""
        # Setup mocks
        mock_client = Mock()
        mock_mistral.return_value = mock_client
        
        db_path = str(tmp_path / "test.db")
        client = SimpleMistralOCRClient(api_key="test-key", db_path=db_path)
        
        # Add job and results to database
        doc_id = client.db.add_document("Test Document")
        client.db.add_job("job-123", doc_id)
        client.db.add_result("job-123", "test.png", "Cached text", "# Cached\n\nCached text")
        
        results = client.results("job-123")
        
        assert len(results) == 1
        assert results[0]["text_content"] == "Cached text"
        
        # Verify no API call was made
        mock_client.batch.jobs.get.assert_not_called()
        
        client.db.close()

    def test_search_functionality(self, tmp_path):
        """Test search functionality."""
        db_path = str(tmp_path / "test.db")
        client = SimpleMistralOCRClient(api_key="test-key", db_path=db_path)
        
        # Add job and results to database
        doc_id = client.db.add_document("Invoice Document")
        client.db.add_job("job-123", doc_id)
        client.db.add_result("job-123", "invoice.png", "Invoice total: $100", "# Invoice\n\nTotal: $100")
        
        results = client.search("invoice")
        
        assert len(results) == 1
        assert results[0]["file_name"] == "invoice.png"
        assert results[0]["document_name"] == "Invoice Document"
        
        client.db.close()

    def test_list_jobs_functionality(self, tmp_path):
        """Test listing all jobs."""
        db_path = str(tmp_path / "test.db")
        client = SimpleMistralOCRClient(api_key="test-key", db_path=db_path)
        
        # Add multiple jobs
        doc_id1 = client.db.add_document("Document 1")
        doc_id2 = client.db.add_document("Document 2")
        client.db.add_job("job-123", doc_id1)
        client.db.add_job("job-456", doc_id2)
        
        jobs = client.list_jobs()
        
        assert len(jobs) == 2
        job_ids = [job["job_id"] for job in jobs]
        assert "job-123" in job_ids
        assert "job-456" in job_ids
        
        client.db.close()

    def test_file_not_found_error(self, tmp_path):
        """Test error handling for missing files."""
        db_path = str(tmp_path / "test.db")
        client = SimpleMistralOCRClient(api_key="test-key", db_path=db_path)
        
        non_existent_file = tmp_path / "does_not_exist.png"
        
        with pytest.raises(FileNotFoundError):
            client.submit([non_existent_file], "Test Document")
        
        client.db.close()

    def test_batch_file_creation(self, tmp_path):
        """Test batch file creation for API."""
        db_path = str(tmp_path / "test.db")
        client = SimpleMistralOCRClient(api_key="test-key", db_path=db_path)
        
        # Create test files
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\nfake content")
        
        jpg_file = tmp_path / "test.jpg"
        jpg_file.write_bytes(b"\xff\xd8\xff\xe0fake content")
        
        # Test batch file creation
        batch_file = client._create_batch_file([png_file, jpg_file])
        
        # Verify batch file content
        with open(batch_file, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 2  # Two files
        
        # Parse first line
        entry1 = json.loads(lines[0])
        assert entry1["custom_id"] == "test.png"
        assert entry1["method"] == "POST"
        assert "data:image/png;base64," in entry1["body"]["messages"][0]["content"][1]["image_url"]["url"]
        
        # Cleanup
        pathlib.Path(batch_file).unlink(missing_ok=True)
        client.db.close()