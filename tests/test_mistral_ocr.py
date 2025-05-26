import subprocess
import pathlib
import pytest

# Helper function to run the CLI

def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python", "-m", "mistral_ocr", *args],
        capture_output=True,
        text=True,
    )


# Basic Integrity Checks

@pytest.mark.xfail(reason="CLI help not implemented")
def test_display_help_message() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


@pytest.mark.xfail(reason="Configuration manager not implemented")
def test_configuration_availability() -> None:
    from mistral_ocr.config import ConfigurationManager  # type: ignore

    config = ConfigurationManager()
    assert config is not None


@pytest.mark.xfail(reason="Logging not implemented")
def test_log_file_creation(tmp_path: pathlib.Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    from mistral_ocr.logging import setup_logging  # type: ignore

    log_file = setup_logging(log_dir)
    assert log_file.exists()


@pytest.mark.xfail(reason="Database layer not implemented")
def test_database_connectivity(tmp_path: pathlib.Path) -> None:
    from mistral_ocr.database import Database  # type: ignore

    db = Database(tmp_path / "test.db")
    db.connect()
    result = db.execute("SELECT 1")
    assert result == 1


# Basic File Submission

@pytest.mark.xfail(reason="File submission not implemented")
def test_submit_single_png(tmp_path: pathlib.Path) -> None:
    test_file = tmp_path / "image.png"
    test_file.write_bytes(b"fakepng")
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    job_id = client.submit_documents([test_file])
    assert job_id is not None


@pytest.mark.xfail(reason="JPEG submission not implemented")
def test_submit_single_jpeg(tmp_path: pathlib.Path) -> None:
    test_file = tmp_path / "image.jpg"
    test_file.write_bytes(b"fakejpeg")
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    job_id = client.submit_documents([test_file])
    assert job_id is not None


@pytest.mark.xfail(reason="PDF submission not implemented")
def test_submit_single_pdf(tmp_path: pathlib.Path) -> None:
    test_file = tmp_path / "document.pdf"
    test_file.write_bytes(b"fakepdf")
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    job_id = client.submit_documents([test_file])
    assert job_id is not None


@pytest.mark.xfail(reason="File type validation not implemented")
def test_unsupported_file_type(tmp_path: pathlib.Path) -> None:
    invalid_file = tmp_path / "file.txt"
    invalid_file.write_text("text")
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    with pytest.raises(ValueError):
        client.submit_documents([invalid_file])


@pytest.mark.xfail(reason="File not found handling not implemented")
def test_file_not_found() -> None:
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    with pytest.raises(FileNotFoundError):
        client.submit_documents([pathlib.Path("missing.png")])


# Directory Submission

@pytest.mark.xfail(reason="Directory submission not implemented")
def test_submit_directory_non_recursive(tmp_path: pathlib.Path) -> None:
    directory = tmp_path / "docs"
    directory.mkdir()
    (directory / "a.png").write_bytes(b"1")
    (directory / "b.png").write_bytes(b"2")
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    job_id = client.submit_documents([directory])
    assert job_id is not None


@pytest.mark.xfail(reason="Recursive directory submission not implemented")
def test_submit_directory_recursive(tmp_path: pathlib.Path) -> None:
    directory = tmp_path / "docs"
    sub = directory / "sub"
    sub.mkdir(parents=True)
    (sub / "a.png").write_bytes(b"1")
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    job_id = client.submit_documents([directory], recursive=True)  # type: ignore
    assert job_id is not None


@pytest.mark.xfail(reason="Batch partitioning not implemented")
def test_automatic_batch_partitioning(tmp_path: pathlib.Path) -> None:
    directory = tmp_path / "docs"
    directory.mkdir()
    for i in range(105):
        (directory / f"{i}.png").write_bytes(b"x")
    files = sorted(directory.iterdir())
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    job_ids = client.submit_documents(files)
    assert len(job_ids) > 1


# Document Naming and Association

@pytest.mark.xfail(reason="Document naming not implemented")
def test_create_new_document_by_name(tmp_path: pathlib.Path) -> None:
    file = tmp_path / "p1.png"
    file.write_bytes(b"p1")
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    job_id = client.submit_documents([file], document_name="Doc")  # type: ignore
    assert job_id is not None


@pytest.mark.xfail(reason="Append to recent document not implemented")
def test_append_pages_to_recent_document(tmp_path: pathlib.Path) -> None:
    file = tmp_path / "p1.png"
    file.write_bytes(b"p1")
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    client.submit_documents([file], document_name="Doc")  # type: ignore
    job_id = client.submit_documents([file], document_name="Doc")  # type: ignore
    assert job_id is not None


@pytest.mark.xfail(reason="Append by UUID not implemented")
def test_append_pages_to_document_by_uuid(tmp_path: pathlib.Path) -> None:
    file = tmp_path / "p1.png"
    file.write_bytes(b"p1")
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    doc_id = "1234"
    job_id = client.submit_documents([file], document_uuid=doc_id)  # type: ignore
    assert job_id is not None


# Job Management

@pytest.mark.xfail(reason="Job status check not implemented")
def test_check_job_status_by_id() -> None:
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    status = client.check_job_status("job123")
    assert status in {"pending", "processing", "completed", "failed"}


@pytest.mark.xfail(reason="Document status query not implemented")
def test_query_status_by_document_name() -> None:
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    statuses = client.query_document_status("Doc")
    assert isinstance(statuses, list)


@pytest.mark.xfail(reason="Job cancellation not implemented")
def test_cancel_job() -> None:
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    result = client.cancel_job("job123")
    assert result is True


@pytest.mark.xfail(reason="Invalid job ID handling not implemented")
def test_invalid_job_id() -> None:
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    with pytest.raises(ValueError):
        client.check_job_status("invalid")


# Result Retrieval

@pytest.mark.xfail(reason="Result retrieval not implemented")
def test_retrieve_results_for_completed_job() -> None:
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    results = client.get_results("job123")
    assert isinstance(results, list)


@pytest.mark.xfail(reason="Pre-completion retrieval not implemented")
def test_retrieve_before_completion() -> None:
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    with pytest.raises(RuntimeError):
        client.get_results("job123")


@pytest.mark.xfail(reason="Auto download not implemented")
def test_automatic_download_results(tmp_path: pathlib.Path) -> None:
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    client.download_results("job123", destination=tmp_path)  # type: ignore
    assert (tmp_path / "job123").exists()


@pytest.mark.xfail(reason="Unknown document storage not implemented")
def test_unknown_document_storage(tmp_path: pathlib.Path) -> None:
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    client.download_results("job123", destination=tmp_path)  # type: ignore
    assert (tmp_path / "unknown").exists()


@pytest.mark.xfail(reason="Redownload not implemented")
def test_redownload_results(tmp_path: pathlib.Path) -> None:
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    client.download_results("job123", destination=tmp_path)  # type: ignore
    client.download_results("job123", destination=tmp_path)  # type: ignore
    assert (tmp_path / "job123").exists()


# Advanced Options and CLI

@pytest.mark.xfail(reason="Custom model not implemented")
def test_specify_custom_model(tmp_path: pathlib.Path) -> None:
    file = tmp_path / "p1.png"
    file.write_bytes(b"p1")
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    job_id = client.submit_documents([file], model="test-model")
    assert job_id is not None


@pytest.mark.xfail(reason="CLI submission not implemented")
def test_command_line_submission(tmp_path: pathlib.Path) -> None:
    file = tmp_path / "p1.png"
    file.write_bytes(b"p1")
    result = run_cli("--submit", str(file))
    assert result.returncode == 0


@pytest.mark.xfail(reason="CLI status check not implemented")
def test_command_line_status_check() -> None:
    result = run_cli("--check-job", "job123")
    assert result.returncode == 0


@pytest.mark.xfail(reason="CLI result retrieval not implemented")
def test_command_line_result_retrieval() -> None:
    result = run_cli("--get-results", "job123")
    assert result.returncode == 0


def test_logging_of_errors(tmp_path: pathlib.Path) -> None:
    import os
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    # Set XDG_DATA_HOME to tmp_path so the client creates logs there
    original_xdg = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    
    try:
        log_file = tmp_path / "mistral.log"
        client = MistralOCRClient(api_key="test")
        try:
            client.submit_documents([pathlib.Path("missing.png")])
        except FileNotFoundError:
            pass
        assert log_file.exists()
    finally:
        # Restore original XDG_DATA_HOME
        if original_xdg is not None:
            os.environ["XDG_DATA_HOME"] = original_xdg
        else:
            os.environ.pop("XDG_DATA_HOME", None)


@pytest.mark.xfail(reason="Batch processing check not implemented")
def test_batch_processing_for_cost_management(tmp_path: pathlib.Path) -> None:
    directory = tmp_path / "docs"
    directory.mkdir()
    for i in range(105):
        (directory / f"{i}.png").write_bytes(b"x")
    files = sorted(directory.iterdir())
    from mistral_ocr.client import MistralOCRClient  # type: ignore

    client = MistralOCRClient(api_key="test")
    job_ids = client.submit_documents(files)
    assert all(len(batch) <= 100 for batch in job_ids)  # type: ignore
