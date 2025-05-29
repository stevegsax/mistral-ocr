"""Test data factories for creating consistent test objects."""

import pathlib
import uuid
from dataclasses import dataclass
from typing import Dict, List
from unittest.mock import Mock


@dataclass
class TestJobData:
    """Test job data factory."""

    id: str
    status: str
    document_uuid: str
    document_name: str
    file_count: int
    created_at: str = "2024-01-01T10:00:00Z"
    completed_at: str = None
    last_api_refresh: str = None
    api_response_json: str = None


@dataclass
class TestDocumentData:
    """Test document data factory."""

    uuid: str
    name: str
    downloaded: bool = False


class JobFactory:
    """Factory for creating test job objects."""

    @staticmethod
    def create_pending_job(job_id: str = None, doc_name: str = "Test Document") -> TestJobData:
        """Create a pending job."""
        return TestJobData(
            id=job_id or f"job_{uuid.uuid4().hex[:8]}",
            status="pending",
            document_uuid=str(uuid.uuid4()),
            document_name=doc_name,
            file_count=1,
        )

    @staticmethod
    def create_completed_job(job_id: str = None, doc_name: str = "Test Document") -> TestJobData:
        """Create a completed job."""
        return TestJobData(
            id=job_id or f"job_{uuid.uuid4().hex[:8]}",
            status="completed",
            document_uuid=str(uuid.uuid4()),
            document_name=doc_name,
            file_count=1,
            completed_at="2024-01-01T10:05:00Z",
        )

    @staticmethod
    def create_failed_job(job_id: str = None, doc_name: str = "Test Document") -> TestJobData:
        """Create a failed job."""
        return TestJobData(
            id=job_id or f"job_{uuid.uuid4().hex[:8]}",
            status="failed",
            document_uuid=str(uuid.uuid4()),
            document_name=doc_name,
            file_count=1,
            completed_at="2024-01-01T10:03:00Z",
        )

    @staticmethod
    def create_production_job(
        job_id: str = None, doc_name: str = "Production Document"
    ) -> TestJobData:
        """Create a realistic production job with UUID-like ID."""
        return TestJobData(
            id=job_id or str(uuid.uuid4()),
            status="completed",
            document_uuid=str(uuid.uuid4()),
            document_name=doc_name,
            file_count=3,
            completed_at="2024-01-01T10:05:00Z",
        )


class DocumentFactory:
    """Factory for creating test document objects."""

    @staticmethod
    def create_document(name: str = "Test Document", downloaded: bool = False) -> TestDocumentData:
        """Create a test document."""
        return TestDocumentData(uuid=str(uuid.uuid4()), name=name, downloaded=downloaded)


class MockAPIFactory:
    """Factory for creating mock API responses."""

    @staticmethod
    def create_mock_job(
        job_id: str = "test-job-id",
        status: str = "completed",
        total_requests: int = 1,
        input_files: List[str] = None,
        output_file: str = "output.jsonl",
        errors: List[Dict] = None,
    ) -> Mock:
        """Create a mock API job response."""
        job = Mock()
        job.id = job_id
        job.status = status
        job.created_at = "2024-01-01T10:00:00Z"
        job.completed_at = "2024-01-01T10:05:00Z" if status == "completed" else None
        job.total_requests = total_requests
        job.input_files = input_files or ["file1.png"]
        job.output_file = output_file if status == "completed" else None
        job.errors = errors
        job.metadata = {"model": "pixtral-12b-2409"}
        return job

    @staticmethod
    def create_batch_jobs_response(jobs: List[Mock]) -> Mock:
        """Create a mock batch jobs list response."""
        response = Mock()
        response.data = jobs
        return response

    @staticmethod
    def create_file_upload_response(file_id: str = "file-123") -> Mock:
        """Create a mock file upload response."""
        response = Mock()
        response.id = file_id
        return response


class FileFactory:
    """Factory for creating test files."""

    @staticmethod
    def create_png_file(
        tmp_path: pathlib.Path, name: str = "test.png", content: bytes = None
    ) -> pathlib.Path:
        """Create a test PNG file."""
        file_path = tmp_path / name
        content = content or b"\x89PNG\r\n\x1a\n" + b"fake png content" * 10
        file_path.write_bytes(content)
        return file_path

    @staticmethod
    def create_jpg_file(
        tmp_path: pathlib.Path, name: str = "test.jpg", content: bytes = None
    ) -> pathlib.Path:
        """Create a test JPEG file."""
        file_path = tmp_path / name
        content = content or b"\xff\xd8\xff\xe0" + b"fake jpeg content" * 10
        file_path.write_bytes(content)
        return file_path

    @staticmethod
    def create_pdf_file(
        tmp_path: pathlib.Path, name: str = "test.pdf", content: bytes = None
    ) -> pathlib.Path:
        """Create a test PDF file."""
        file_path = tmp_path / name
        content = content or b"%PDF-1.4" + b"fake pdf content" * 10
        file_path.write_bytes(content)
        return file_path

    @staticmethod
    def create_multiple_files(
        tmp_path: pathlib.Path, count: int = 3, extensions: List[str] = None
    ) -> List[pathlib.Path]:
        """Create multiple test files."""
        extensions = extensions or [".png", ".jpg", ".pdf"]
        files = []

        for i in range(count):
            ext = extensions[i % len(extensions)]
            if ext == ".png":
                files.append(FileFactory.create_png_file(tmp_path, f"test_{i}{ext}"))
            elif ext == ".jpg":
                files.append(FileFactory.create_jpg_file(tmp_path, f"test_{i}{ext}"))
            elif ext == ".pdf":
                files.append(FileFactory.create_pdf_file(tmp_path, f"test_{i}{ext}"))

        return files

    @staticmethod
    def create_large_file_set(tmp_path: pathlib.Path, count: int = 150) -> List[pathlib.Path]:
        """Create a large set of files to trigger batch partitioning."""
        files = []
        for i in range(count):
            file_path = tmp_path / f"batch_test_{i:03d}.png"
            content = b"\x89PNG\r\n\x1a\n" + f"content_{i}".encode() * 10
            file_path.write_bytes(content)
            files.append(file_path)
        return files


class ConfigFactory:
    """Factory for creating test configuration."""

    @staticmethod
    def create_test_env_vars() -> Dict[str, str]:
        """Create standard test environment variables."""
        return {"MISTRAL_API_KEY": "test-api-key", "PYTHONPATH": "src"}

    @staticmethod
    def create_isolated_paths(tmp_path: pathlib.Path) -> Dict[str, str]:
        """Create isolated XDG paths for testing."""
        return {"XDG_DATA_HOME": str(tmp_path / "data"), "XDG_STATE_HOME": str(tmp_path / "state")}
