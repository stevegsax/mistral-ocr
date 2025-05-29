# Mistral OCR Usage Guide

This guide explains how to use the Mistral OCR CLI tool for extracting text from images and documents.

## Overview

The Mistral OCR client allows you to extract text from images and documents using the Mistral AI API. The tool uses batch processing for efficient handling of multiple files and provides comprehensive job management capabilities.

## Prerequisites

1. A Mistral API key
2. Files to process (PNG, JPEG, or PDF formats)

## Configuration

### Setting Up Your API Key

**Option 1: Environment Variable**
```bash
export MISTRAL_API_KEY="your-api-key-here"
```

**Option 2: Configuration File**
```bash
# Set API key in configuration file
uv run python -m mistral_ocr config set api-key "your-api-key-here"

# View current configuration
uv run python -m mistral_ocr config show

# Set default model
uv run python -m mistral_ocr config set model "pixtral-12b-2412"

# Set default download directory
uv run python -m mistral_ocr config set download-dir "/path/to/downloads"

# Reset configuration to defaults
uv run python -m mistral_ocr config reset
```

## File Submission

### Basic File Submission

```bash
# Submit a single file
uv run python -m mistral_ocr submit document.png

# Submit a PDF document
uv run python -m mistral_ocr submit report.pdf

# Submit with a custom model
uv run python -m mistral_ocr submit image.jpg --model mistral-ocr-latest
```

### Directory Processing

```bash
# Submit all supported files in a directory (non-recursive)
uv run python -m mistral_ocr submit /path/to/documents/

# Submit all files recursively (includes subdirectories)
uv run python -m mistral_ocr submit /path/to/documents/ --recursive

# Submit directory with document naming
uv run python -m mistral_ocr submit /path/to/invoices/ --recursive --name "Q4_Invoices"
```

### Document Management

```bash
# Create a new document with a specific name
uv run python -m mistral_ocr submit page1.png --name "Annual_Report"

# Add more pages to the same document
uv run python -m mistral_ocr submit page2.png --name "Annual_Report"

# Add pages to a specific document by UUID
uv run python -m mistral_ocr submit page3.png --uuid "123e4567-e89b-12d3-a456-426614174000"
```

## Job Management

### Checking Job Status

```bash
# List all jobs with their status
uv run python -m mistral_ocr jobs list

# Show detailed status for a specific job (includes API response details)
uv run python -m mistral_ocr jobs status job_001

# Query all jobs associated with a document name
uv run python -m mistral_ocr documents query "Annual_Report"
```

### Job Control

```bash
# Cancel a running job
uv run python -m mistral_ocr jobs cancel job_001
```

## Result Retrieval

### Getting Results

```bash
# Retrieve results for a completed job (displays in terminal)
uv run python -m mistral_ocr results get job_001

# Download results to default location
uv run python -m mistral_ocr results download job_001

# Download results to a specific directory
uv run python -m mistral_ocr results download job_001 --output /path/to/save/results/

# Download all results for a document by name or UUID
uv run python -m mistral_ocr documents download "Annual_Report" --output /path/to/save/
```

## Job Status Values

Batch jobs can have the following statuses:

- `pending`: The job is waiting to be processed
- `processing`: The job is currently being processed
- `completed`: The job has been completed successfully
- `failed`: The job failed to process

## Supported File Formats

- **Images**: PNG (`.png`), JPEG (`.jpg`, `.jpeg`)
- **Documents**: PDF (`.pdf`)

Hidden files (starting with `.`) are automatically ignored during directory processing.

## Output Structure

Results are downloaded with the following structure:

```
download_directory/
├── document-name/           # Lowercase document name with hyphens
│   ├── filename_001.md      # Markdown format results
│   ├── filename_001.txt     # Plain text results
│   ├── filename_002.md
│   └── filename_002.txt
└── unknown/                 # Files not associated with a document
    ├── file_001.md
    └── file_001.txt
```

## Batch Processing

The tool automatically handles large file sets:

- **Automatic Partitioning**: Files are split into batches of 100 (Mistral API limit)
- **Multiple Job IDs**: Large submissions return multiple job IDs for tracking
- **Cost Optimization**: Uses Mistral's batch API for cost-effective processing

Example with large file set:

```bash
# This will create multiple batch jobs if >100 files
uv run python -m mistral_ocr submit /large_archive/ --recursive --name "Archive_2024"
# Output: "Submitted 3 batch jobs: job_001, job_002, job_003"
```

## Advanced Workflow Examples

### Complete OCR Workflow

```bash
# 1. Submit files
uv run python -m mistral_ocr submit contract.pdf --name "Contract_Review"

# 2. Get detailed status information (note the returned job ID from step 1)
uv run python -m mistral_ocr jobs status job_002

# 3. Download results when completed
uv run python -m mistral_ocr results download job_002 --output ./processed_contracts/

# 4. Monitor document processing status
uv run python -m mistral_ocr documents query "Contract_Review"
```

### Large Archive Processing

```bash
# Process a large document archive with automatic batching
uv run python -m mistral_ocr submit /archive/legal_documents/ --recursive \
  --name "Legal_Archive_2024" --model mistral-ocr-latest

# List all jobs and their current status
uv run python -m mistral_ocr jobs list
```

## Error Handling

The tool provides detailed error messages for common issues:

- **File not found**: Clear indication of missing files or directories
- **Unsupported formats**: Lists supported file types
- **API errors**: Displays Mistral API error details
- **Job failures**: Status information for failed processing

## Configuration Files

The tool follows XDG Base Directory specification:

- **Config**: `~/.config/mistral-ocr/config.json` (or `$XDG_CONFIG_HOME/mistral-ocr/`)
- **Data**: `~/.local/share/mistral-ocr/` (or `$XDG_DATA_HOME/mistral-ocr/`)
- **Database**: `~/.local/state/mistral-ocr/mistral_ocr.db` (or `$XDG_STATE_HOME/mistral-ocr/`)

## Help

Display help and available options:

```bash
uv run python -m mistral_ocr --help
```

## Available Models

Available OCR models (specify with `--model` or set as default):
- `mistral-ocr-latest`: The latest OCR model (default)
- `pixtral-12b-2412`: Pixtral vision model
- Other models as provided by Mistral API

## Best Practices

- Use document names to organize related files
- Check job status before attempting to retrieve results
- Store job IDs for tracking long-running jobs
- Use configuration commands to set up your environment once
- Handle potential API errors gracefully
- Use batch processing for efficiency with multiple files
- Monitor job status regularly for large operations