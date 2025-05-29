# Developer API Reference

> Complete reference for using mistral-ocr programmatically in Python applications

## Installation

```bash
pip install mistral-ocr
# or with uv
uv add mistral-ocr
```

## Quick Start

```python
from mistral_ocr import MistralOCRClient
import pathlib

# Initialize client
client = MistralOCRClient(api_key="your-mistral-api-key")

# Submit files for OCR
files = [pathlib.Path("document.pdf"), pathlib.Path("image.png")]
job_ids = client.submit_documents(files, document_name="MyDocument")

# Check job status
status = client.check_job_status(job_ids[0])
print(f"Job status: {status}")

# Download results when complete
if status == "completed":
    client.download_results(job_ids[0], destination="./results")
```

## Core Classes

### MistralOCRClient

The main interface for OCR operations.

#### Constructor

```python
MistralOCRClient(
    api_key: Optional[str] = None,
    settings: Optional[Settings] = None
) -> None
```

**Parameters:**
- `api_key`: Mistral API key. If None, reads from `MISTRAL_API_KEY` environment variable
- `settings`: Custom settings object. If None, uses default settings

**Example:**
```python
# Using environment variable
client = MistralOCRClient()

# Using explicit API key
client = MistralOCRClient(api_key="your-key")

# Using custom settings
from mistral_ocr import Settings
settings = Settings()
settings.set_progress_enabled(False)
client = MistralOCRClient(api_key="your-key", settings=settings)
```

#### Document Submission

##### `submit_documents()`

Submit files for OCR processing.

```python
submit_documents(
    files: List[pathlib.Path],
    recursive: bool = False,
    document_name: Optional[str] = None,
    document_uuid: Optional[str] = None,
    model: Optional[str] = None,
) -> Union[str, List[str]]
```

**Parameters:**
- `files`: List of file paths or directories to process
- `recursive`: Process directories recursively
- `document_name`: Name to associate with the document (creates new if not exists)
- `document_uuid`: UUID of existing document to add files to
- `model`: OCR model to use (defaults to configured model)

**Returns:**
- Single job ID string if one batch, or list of job IDs if multiple batches

**Raises:**
- `FileNotFoundError`: If any file doesn't exist
- `UnsupportedFileTypeError`: If any file has unsupported extension
- `JobSubmissionError`: If API submission fails

**Example:**
```python
import pathlib

# Submit single file
job_id = client.submit_documents([pathlib.Path("document.pdf")])

# Submit directory recursively with custom name
job_ids = client.submit_documents(
    [pathlib.Path("./documents")], 
    recursive=True,
    document_name="Invoice_Batch_Q4"
)

# Submit to existing document
job_id = client.submit_documents(
    [pathlib.Path("page2.png")],
    document_uuid="123e4567-e89b-12d3-a456-426614174000"
)

# Use specific model
job_id = client.submit_documents(
    [pathlib.Path("contract.pdf")],
    model="pixtral-12b-2412"
)
```

#### Job Management

##### `check_job_status()`

Check the status of a specific job.

```python
check_job_status(job_id: str) -> str
```

**Parameters:**
- `job_id`: Job ID to check

**Returns:**
- Job status string: "pending", "running", "completed", "failed", "cancelled"

**Example:**
```python
status = client.check_job_status("job_001")
if status == "completed":
    print("Job finished successfully!")
```

##### `list_jobs()`

List all jobs with their current status.

```python
list_jobs() -> List[JobInfo]
```

**Returns:**
- List of `JobInfo` objects containing job metadata

**Example:**
```python
jobs = client.list_jobs()
for job in jobs:
    print(f"Job {job.job_id}: {job.status} ({job.total_requests} files)")
```

##### `get_job_details()`

Get detailed information about a specific job.

```python
get_job_details(job_id: str) -> JobDetails
```

**Parameters:**
- `job_id`: Job ID to get details for

**Returns:**
- `JobDetails` object with comprehensive job information

**Example:**
```python
details = client.get_job_details("job_001")
print(f"Created: {details.created_at}")
print(f"API Status: {details.api_status}")
print(f"Input Files: {len(details.input_files)}")
```

##### `cancel_job()`

Cancel a running or pending job.

```python
cancel_job(job_id: str) -> bool
```

**Parameters:**
- `job_id`: Job ID to cancel

**Returns:**
- `True` if cancellation successful, `False` otherwise

**Example:**
```python
success = client.cancel_job("job_001")
if success:
    print("Job cancelled successfully")
```

#### Result Retrieval

##### `get_results()`

Get OCR results for a completed job.

```python
get_results(job_id: str) -> List[OCRResult]
```

**Parameters:**
- `job_id`: Job ID to retrieve results for

**Returns:**
- List of `OCRResult` objects containing extracted text

**Raises:**
- `JobNotCompletedError`: If job is not yet completed
- `ResultNotAvailableError`: If results cannot be retrieved

**Example:**
```python
try:
    results = client.get_results("job_001")
    for result in results:
        print(f"File: {result.filename}")
        print(f"Text: {result.text[:100]}...")  # First 100 chars
except JobNotCompletedError:
    print("Job still processing...")
```

##### `download_results()`

Download and save OCR results to disk.

```python
download_results(
    job_id: str,
    destination: Optional[pathlib.Path] = None
) -> None
```

**Parameters:**
- `job_id`: Job ID to download results for
- `destination`: Directory to save results (uses default if None)

**Example:**
```python
# Download to default location
client.download_results("job_001")

# Download to specific directory
client.download_results("job_001", pathlib.Path("./my_results"))
```

##### `download_document_results()`

Download all results for a document (by name or UUID).

```python
download_document_results(
    document_identifier: str,
    destination: Optional[pathlib.Path] = None
) -> None
```

**Parameters:**
- `document_identifier`: Document name or UUID
- `destination`: Directory to save results

**Example:**
```python
# Download by document name
client.download_document_results("Invoice_Batch_Q4")

# Download by UUID
client.download_document_results("123e4567-e89b-12d3-a456-426614174000")
```

#### Document Management

##### `query_document_jobs()`

Get all jobs associated with a document.

```python
query_document_jobs(document_identifier: str) -> List[JobInfo]
```

**Parameters:**
- `document_identifier`: Document name or UUID

**Returns:**
- List of `JobInfo` objects for the document

**Example:**
```python
jobs = client.query_document_jobs("Invoice_Batch_Q4")
completed_jobs = [job for job in jobs if job.status == "completed"]
print(f"Document has {len(completed_jobs)} completed jobs")
```

## Data Types

### OCRResult

```python
class OCRResult:
    filename: str          # Original filename
    text: str             # Extracted text content
    markdown: str         # Formatted markdown content
    page_number: int      # Page number (for multi-page documents)
```

### JobInfo

```python
class JobInfo:
    job_id: str           # Unique job identifier
    status: str           # Current job status
    total_requests: int   # Number of files in job
    created_at: str       # Job creation timestamp
    document_uuid: str    # Associated document UUID
```

### JobDetails

```python
class JobDetails:
    job_id: str           # Unique job identifier
    status: str           # Current job status
    created_at: str       # Job creation timestamp
    api_created_at: Optional[str]     # API creation timestamp
    api_completed_at: Optional[str]   # API completion timestamp
    total_requests: int   # Number of files in job
    input_files: List[str]            # List of input file IDs
    output_file: Optional[str]        # Output file ID (when completed)
    errors: Optional[List[str]]       # Error messages (if any)
    metadata: Dict[str, Any]          # Additional job metadata
    last_api_refresh: Optional[str]   # Last API status refresh
```

## Configuration

### Settings Class

Manage application configuration programmatically.

```python
from mistral_ocr import Settings

settings = Settings()

# API Configuration
settings.set_api_key("your-api-key")
settings.set_default_model("pixtral-12b-2412")
settings.set_timeout(600)  # 10 minutes
settings.set_max_retries(5)

# Progress Configuration  
settings.set_progress_enabled(True)
settings.set_job_monitor_interval(15)  # seconds

# Directory Configuration
settings.set_download_directory(pathlib.Path("./downloads"))

# Get current settings
api_key = settings.get_api_key()
model = settings.get_default_model()
timeout = settings.get_timeout()
```

### Environment Variables

```bash
# API Key
export MISTRAL_API_KEY="your-api-key"

# Mock mode for testing
export MISTRAL_OCR_MOCK_MODE="1"
```

## Progress Monitoring

### Enabling Progress Tracking

```python
# Enable/disable progress globally
client.settings.set_progress_enabled(True)

# Or disable for specific client
client.progress_manager.enabled = False
```

### Custom Progress Callbacks

```python
from mistral_ocr.progress import ProgressManager

# Create custom progress manager
progress_manager = ProgressManager(enabled=True)

# Use with client
client = MistralOCRClient(
    api_key="your-key",
    settings=settings
)
client.progress_manager = progress_manager
```

## Error Handling

### Exception Hierarchy

```python
from mistral_ocr.exceptions import (
    MistralOCRError,           # Base exception
    DatabaseError,             # Database issues
    FileHandlingError,         # File operations
    UnsupportedFileTypeError,  # Invalid file types
    JobSubmissionError,        # API submission failures
    JobNotCompletedError,      # Results not ready
    ResultNotAvailableError,   # Results unavailable
    InvalidConfigurationError, # Configuration issues
    MissingConfigurationError, # Missing required config
)

try:
    job_id = client.submit_documents([pathlib.Path("document.pdf")])
except UnsupportedFileTypeError as e:
    print(f"File type not supported: {e}")
except JobSubmissionError as e:
    print(f"Failed to submit job: {e}")
except MistralOCRError as e:
    print(f"General error: {e}")
```

### Retry Configuration

```python
# Configure retry behavior globally
settings.set_max_retries(5)
settings.set_timeout(300)

# Individual operations use automatic retry with exponential backoff
```

## Advanced Usage

### Batch Processing

```python
import pathlib

# Process large directory with automatic batching
large_dir = pathlib.Path("./invoices_2024")
files = list(large_dir.rglob("*.pdf"))  # Find all PDFs

print(f"Processing {len(files)} files...")

# Submit (automatically creates multiple batches if > 100 files)
job_ids = client.submit_documents(
    [large_dir],
    recursive=True,
    document_name="Invoices_2024"
)

print(f"Created {len(job_ids)} batch jobs: {job_ids}")

# Monitor all jobs
for job_id in job_ids:
    status = client.check_job_status(job_id)
    print(f"Job {job_id}: {status}")
```

### Concurrent Operations

```python
import asyncio
from mistral_ocr.async_utils import run_async_in_sync_context

# Check multiple job statuses concurrently
job_ids = ["job_001", "job_002", "job_003"]

async def check_all_statuses():
    # Use the client's async capabilities
    manager = client.job_manager
    if hasattr(manager, 'check_multiple_job_statuses_async'):
        return await manager.check_multiple_job_statuses_async(job_ids)
    else:
        # Fallback to sequential
        return [client.check_job_status(job_id) for job_id in job_ids]

# Run async operation in sync context
statuses = run_async_in_sync_context(check_all_statuses)
print(dict(zip(job_ids, statuses)))
```

### Custom Document Workflows

```python
def process_invoice_batch(invoice_dir: pathlib.Path, quarter: str):
    """Process a batch of invoices for a specific quarter."""
    
    # Create document with descriptive name
    document_name = f"Invoices_Q{quarter}_{invoice_dir.name}"
    
    # Submit all PDF files
    pdf_files = list(invoice_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found")
        return
    
    print(f"Processing {len(pdf_files)} invoices for Q{quarter}")
    
    job_ids = client.submit_documents(
        pdf_files,
        document_name=document_name
    )
    
    # Wait for completion
    print("Waiting for jobs to complete...")
    for job_id in job_ids:
        while True:
            status = client.check_job_status(job_id)
            if status in ["completed", "failed", "cancelled"]:
                break
            time.sleep(30)  # Check every 30 seconds
    
    # Download results
    print("Downloading results...")
    client.download_document_results(document_name)
    print(f"Results saved for {document_name}")

# Usage
process_invoice_batch(pathlib.Path("./q4_invoices"), "4")
```

### Integration with Web Applications

```python
from flask import Flask, request, jsonify
import pathlib
import tempfile

app = Flask(__name__)
client = MistralOCRClient()  # Uses env var for API key

@app.route("/ocr", methods=["POST"])
def ocr_endpoint():
    """OCR endpoint for web application."""
    try:
        # Get uploaded file
        file = request.files["document"]
        
        # Save to temporary location
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = pathlib.Path(tmp.name)
        
        # Submit for OCR
        job_id = client.submit_documents([tmp_path])
        
        # Clean up temp file
        tmp_path.unlink()
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": "Document submitted for OCR"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route("/ocr/<job_id>/status", methods=["GET"])
def check_status(job_id):
    """Check OCR job status."""
    try:
        status = client.check_job_status(job_id)
        return jsonify({
            "job_id": job_id,
            "status": status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/ocr/<job_id>/results", methods=["GET"])
def get_results(job_id):
    """Get OCR results."""
    try:
        results = client.get_results(job_id)
        return jsonify({
            "job_id": job_id,
            "results": [
                {
                    "filename": r.filename,
                    "text": r.text,
                    "markdown": r.markdown
                }
                for r in results
            ]
        })
    except JobNotCompletedError:
        return jsonify({"error": "Job not completed yet"}), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 400
```

## Testing

### Mock Mode

```python
# Enable mock mode for testing
client = MistralOCRClient(api_key="test")  # "test" triggers mock mode

# Or via environment
import os
os.environ["MISTRAL_OCR_MOCK_MODE"] = "1"
client = MistralOCRClient(api_key="your-key")  # Uses mock mode
```

### Unit Testing

```python
import pytest
import pathlib
from mistral_ocr import MistralOCRClient

@pytest.fixture
def client():
    """Create a test client with mock mode."""
    return MistralOCRClient(api_key="test")

@pytest.fixture
def test_file(tmp_path):
    """Create a test file."""
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"fake pdf content")
    return file_path

def test_submit_document(client, test_file):
    """Test document submission."""
    job_id = client.submit_documents([test_file])
    assert job_id.startswith("job_")
    
    # Check status
    status = client.check_job_status(job_id)
    assert status in ["pending", "running", "completed"]

def test_document_workflow(client, tmp_path):
    """Test complete document workflow."""
    # Create test files
    files = []
    for i in range(3):
        file_path = tmp_path / f"page{i}.png"
        file_path.write_bytes(b"fake png content")
        files.append(file_path)
    
    # Submit with document name
    job_ids = client.submit_documents(files, document_name="TestDoc")
    
    # Verify all jobs created
    assert len(job_ids) >= 1
    
    # Check document association
    doc_jobs = client.query_document_jobs("TestDoc")
    assert len(doc_jobs) >= 1
```

This API reference provides comprehensive coverage of the mistral-ocr Python interface, enabling developers to integrate OCR capabilities into their applications effectively.