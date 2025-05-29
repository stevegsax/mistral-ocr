# Mistral OCR Implementation Guide

This guide explains how the Mistral OCR functionality is implemented in this project.

## Overview

Our implementation provides a streamlined interface for OCR processing using the Mistral AI API v1. The client uses Mistral's batch jobs API for efficient processing of multiple files.

## Implementation Details

### Client Architecture

The `MistralOCRClient` class provides the following key methods:

1. `submit_batch_job`: Uploads files and creates a batch OCR job
2. `get_batch_job_status`: Returns the status of a batch job (pending, processing, completed, or failed)
3. `get_batch_job_results`: Returns OCR results for a completed batch job

### Batch Processing Workflow

The implementation follows this workflow:

1. **File Upload**:
   - Each file is uploaded to Mistral's file storage using the `files.upload` API
   - File IDs are collected for batch processing

2. **Batch Job Creation**:
   - A batch job is created with the file IDs using the `batch.jobs.create` API
   - The endpoint is set to `/v1/ocr` for OCR processing
   - The specified model (default: `mistral-ocr-latest`) is used for processing

3. **Job Status Checking**:
   - Job status is checked using the `batch.jobs.get` API
   - Possible statuses: pending, processing, completed, failed

4. **Result Retrieval**:
   - For completed jobs, results are retrieved from the job outputs
   - Each output is converted to an `OCRResult` object containing text, markdown, file name, and job ID

### OCR API Integration

The implementation integrates with Mistral's OCR API through the batch jobs API, which provides:
- Asynchronous processing of multiple files
- Efficient use of API resources
- Status tracking for long-running jobs
- Standardized error handling

## Example Usage

```python
from ocr_test_mistral.ocr import MistralOCRClient

# Initialize the client
client = MistralOCRClient()

# Submit files for batch processing
job_id = client.submit_batch_job(["image1.png", "document.pdf"])

# Check job status
status = client.get_batch_job_status(job_id)
print(f"Job status: {status}")

# Once completed, get results
if status == "completed":
    results = client.get_batch_job_results(job_id)
    for result in results:
        print(f"Text from {result.file_name}:")
        print(result.text)
```

## Command Line Interface

The client can be used from the command line with the new subcommand structure:

```bash
# Submit files for batch processing
python -m mistral_ocr submit file1.png file2.jpg

# Check job status
python -m mistral_ocr jobs status <job_id>

# Get job results
python -m mistral_ocr results get <job_id>
```

## Response Structure

The `OCRResult` objects contain:
- `text`: Extracted text in plain format
- `markdown`: Extracted text in markdown format
- `file_name`: Original file name
- `job_id`: Batch job ID

## File Handling

The implementation includes careful handling of file uploads:
- Files are read in binary mode
- Binary data is passed directly to the API
- File names are preserved for reference

## Error Handling

The implementation includes robust error handling for:
- File upload failures
- Batch job creation errors
- Job status checking errors
- Result retrieval errors

## Advanced Features

- Support for different OCR models via the model parameter
- Automatic handling of API errors with meaningful error messages
- Job status monitoring