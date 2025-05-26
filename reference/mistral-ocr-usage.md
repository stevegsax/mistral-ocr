# Mistral OCR Usage Guide

This guide explains how to use the Mistral OCR functionality in this project.

## Overview

The Mistral OCR client allows you to extract text from images and documents using the Mistral AI API. The client uses batch processing for efficient handling of multiple files.

## Prerequisites

1. A Mistral API key (set as an environment variable `MISTRAL_API_KEY` or in your config)
2. Files to process (images or documents)

## Basic Usage

### Process files in batch mode

```python
from ocr_test_mistral.ocr import MistralOCRClient

# Initialize the client
client = MistralOCRClient()

# Submit files for processing
file_paths = ["path/to/image1.png", "path/to/document.pdf"]
job_id = client.submit_batch_job(file_paths)
print(f"Job submitted with ID: {job_id}")

# Later, check job status
status = client.get_batch_job_status(job_id)
print(f"Job status: {status}")

# Once completed, get results
if status == "completed":
    results = client.get_batch_job_results(job_id)
    for result in results:
        print(f"Text from {result.file_name}:")
        print(result.text)
        print(f"Markdown from {result.file_name}:")
        print(result.markdown)
```

### Command Line Interface

You can also use the command line interface:

```bash
# Submit files for processing
python -m ocr_test_mistral --submit file1.png file2.jpg

# Check job status
python -m ocr_test_mistral --check-job <job_id>

# Get job results
python -m ocr_test_mistral --get-results <job_id>
```

## Job Status

Batch jobs can have the following statuses:

- `pending`: The job is waiting to be processed
- `processing`: The job is currently being processed
- `completed`: The job has been completed successfully
- `failed`: The job failed to process

## Response Format

The OCR result objects contain:

- `text`: Extracted text in plain format
- `markdown`: Extracted text in markdown format
- `file_name`: Original file name
- `job_id`: Batch job ID

## Implementation Details

Under the hood, the client:

1. Uploads files to the Mistral API
2. Creates a batch job for OCR processing
3. Checks job status
4. Retrieves and parses results when the job is completed

## Supported File Formats

The Mistral OCR API supports the following file formats:

- PNG images (*.png)
- JPEG images (*.jpg, *.jpeg)
- PDF documents (*.pdf)

## Advanced Options

You can specify the OCR model to use:

```python
job_id = client.submit_batch_job(file_paths, model="mistral-ocr-latest")
```

Available models:
- `mistral-ocr-latest`: The latest OCR model
- Other models as provided by Mistral API

## Error Handling

The client provides helpful error messages for common issues:

- File not found
- API authentication errors
- Batch job creation failures
- Invalid job ID

## Best Practices

- Use batch processing for multiple files to improve efficiency
- Check job status before attempting to retrieve results
- Store job IDs for long-running jobs
- Handle potential API errors gracefully