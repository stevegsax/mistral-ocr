"""Test database content storage functionality."""

import pytest
from mistral_ocr.database import Database
from mistral_ocr.db_models import Base


class TestDatabaseContentStorage:
    """Test storing and retrieving OCR content in database."""

    @pytest.fixture
    def database(self, tmp_path):
        """Create test database with content storage schema."""
        db_path = tmp_path / "test_content.db"
        db = Database(db_path)
        db.connect()
        db.initialize_schema()
        return db

    def test_store_download_with_content(self, database):
        """Test storing download record with actual OCR content."""
        # Store a document first
        doc_uuid = "test-doc-uuid"
        database.store_document(doc_uuid, "Test Document")
        
        # Store a job
        job_id = "test-job-id"
        database.store_job(job_id, doc_uuid, "completed", 1)
        
        # Store download with content
        text_content = "This is the OCR text content from the document."
        markdown_content = "# OCR Result\n\nThis is **markdown** content."
        image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAGAw=" # Minimal base64 PNG
        
        database.store_download(
            text_path="/path/to/text.txt",
            markdown_path="/path/to/markdown.md",
            document_uuid=doc_uuid,
            job_id=job_id,
            document_order=0,
            text_content=text_content,
            markdown_content=markdown_content,
            image_data_base64=image_data
        )
        
        # Verify content can be retrieved
        content = database.get_download_content(job_id, 0)
        assert content is not None
        assert content["text_content"] == text_content
        assert content["markdown_content"] == markdown_content
        assert content["image_data_base64"] == image_data

    def test_search_downloads_by_text(self, database):
        """Test searching OCR content by text."""
        # Store a document and job
        doc_uuid = "search-doc-uuid"
        database.store_document(doc_uuid, "Search Test Document")
        
        job_id = "search-job-id"
        database.store_job(job_id, doc_uuid, "completed", 1)
        
        # Store download with searchable content
        text_content = "The quick brown fox jumps over the lazy dog."
        markdown_content = "# Animal Story\n\nThe **fox** was very clever."
        
        database.store_download(
            text_path="/path/to/search.txt",
            markdown_path="/path/to/search.md",
            document_uuid=doc_uuid,
            job_id=job_id,
            document_order=0,
            text_content=text_content,
            markdown_content=markdown_content
        )
        
        # Search for "fox"
        results = database.search_downloads_by_text("fox")
        assert len(results) == 1
        assert results[0]["job_id"] == job_id
        assert results[0]["document_name"] == "Search Test Document"
        assert "fox" in results[0]["text_content"].lower()
        
        # Search for non-existent text
        results = database.search_downloads_by_text("elephant")
        assert len(results) == 0

    def test_get_all_downloads_for_document(self, database):
        """Test retrieving all content for a document."""
        # Store a document
        doc_uuid = "multi-download-uuid"
        doc_name = "Multi Download Document"
        database.store_document(doc_uuid, doc_name)
        
        # Store multiple jobs and downloads
        for i in range(3):
            job_id = f"job-{i}"
            database.store_job(job_id, doc_uuid, "completed", 1)
            
            database.store_download(
                text_path=f"/path/to/text_{i}.txt",
                markdown_path=f"/path/to/markdown_{i}.md",
                document_uuid=doc_uuid,
                job_id=job_id,
                document_order=i,
                text_content=f"Text content for page {i}",
                markdown_content=f"# Page {i}\n\nMarkdown content"
            )
        
        # Get all downloads by document name
        downloads = database.get_all_downloads_for_document(doc_name)
        assert len(downloads) == 3
        
        # Check they're ordered by document_order
        for i, download in enumerate(downloads):
            assert download["document_order"] == i
            assert f"page {i}" in download["text_content"].lower()
            assert f"Page {i}" in download["markdown_content"]
        
        # Get all downloads by document UUID
        downloads_by_uuid = database.get_all_downloads_for_document(doc_uuid)
        assert len(downloads_by_uuid) == 3
        assert downloads_by_uuid == downloads

    def test_content_storage_backward_compatibility(self, database):
        """Test that content storage works with existing code paths."""
        # Store document and job
        doc_uuid = "compat-doc-uuid"
        database.store_document(doc_uuid, "Compatibility Test")
        
        job_id = "compat-job-id"
        database.store_job(job_id, doc_uuid, "completed", 1)
        
        # Store download without content (old way)
        database.store_download(
            text_path="/path/to/old_text.txt",
            markdown_path="/path/to/old_markdown.md",
            document_uuid=doc_uuid,
            job_id=job_id,
            document_order=0
        )
        
        # Should be able to retrieve (but content will be None)
        content = database.get_download_content(job_id, 0)
        assert content is not None
        assert content["text_content"] is None
        assert content["markdown_content"] is None
        assert content["image_data_base64"] is None
        
        # Can still find in document downloads
        downloads = database.get_all_downloads_for_document(doc_uuid)
        assert len(downloads) == 1
        assert downloads[0]["job_id"] == job_id

    def test_large_content_storage(self, database):
        """Test storing large text content."""
        # Store document and job
        doc_uuid = "large-doc-uuid"
        database.store_document(doc_uuid, "Large Content Test")
        
        job_id = "large-job-id"
        database.store_job(job_id, doc_uuid, "completed", 1)
        
        # Create large content (simulate OCR of a long document)
        large_text = "This is a very long OCR result. " * 1000  # ~33KB
        large_markdown = "# Long Document\n\n" + "* Item\n" * 500  # ~4KB
        
        database.store_download(
            text_path="/path/to/large.txt",
            markdown_path="/path/to/large.md",
            document_uuid=doc_uuid,
            job_id=job_id,
            document_order=0,
            text_content=large_text,
            markdown_content=large_markdown
        )
        
        # Verify large content can be retrieved correctly
        content = database.get_download_content(job_id, 0)
        assert content is not None
        assert len(content["text_content"]) > 30000
        assert content["text_content"] == large_text
        assert content["markdown_content"] == large_markdown