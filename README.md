# mistral-ocr

> Command line tool to submit, track, and retrieve OCR batches to the Mistral API

A Python CLI tool for submitting documents to the Mistral OCR service, managing batch jobs, and retrieving results. Supports PNG, JPEG, and PDF files with automatic batch partitioning and document management.

## Features

- **File Submission**: Submit individual files or entire directories for OCR processing
- **Batch Processing**: Automatic partitioning for 100+ files per Mistral API limits
- **Document Management**: Associate files with named documents using UUIDs
- **Job Tracking**: Check status, cancel jobs, and query by document name
- **Result Retrieval**: Download OCR results in text and markdown formats
- **XDG Compliance**: Follows XDG Base Directory specification for config and data

## Installation

The package is managed with `uv`. To set up the development environment:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Install the package in development mode
uv pip install -e .

# Install additional dependencies if needed
uv add <package>
```

## Configuration

Set your Mistral API key as an environment variable:

```bash
export MISTRAL_API_KEY="your-api-key-here"
```

Alternatively, you can store it in the configuration file using the CLI (stored in `~/.config/mistral-ocr/config.json`).

## Usage Examples

### Basic File Submission

Submit a single file for OCR processing:

```bash
# Submit a single image file
uv run python -m mistral_ocr --submit document.png

# Submit a PDF document
uv run python -m mistral_ocr --submit report.pdf

# Submit with a custom model
uv run python -m mistral_ocr --submit image.jpg --model mistral-ocr-latest
```

### Directory Processing

Submit entire directories with various options:

```bash
# Submit all supported files in a directory (non-recursive)
uv run python -m mistral_ocr --submit /path/to/documents/

# Submit all files recursively (includes subdirectories)
uv run python -m mistral_ocr --submit /path/to/documents/ --recursive

# Submit directory with document naming
uv run python -m mistral_ocr --submit /path/to/invoices/ --recursive --document-name "Q4_Invoices"
```

### Document Management

Associate files with named documents for better organization:

```bash
# Create a new document with a specific name
uv run python -m mistral_ocr --submit page1.png --document-name "Annual_Report"

# Add more pages to the same document (creates new document if name doesn't exist)
uv run python -m mistral_ocr --submit page2.png --document-name "Annual_Report"

# Add pages to a specific document by UUID
uv run python -m mistral_ocr --submit page3.png --document-uuid "123e4567-e89b-12d3-a456-426614174000"
```

### Job Management

Track and manage your OCR jobs:

```bash
# Check the status of a specific job
uv run python -m mistral_ocr --check-job job_001

# List all jobs with their status
uv run python -m mistral_ocr --list-jobs

# Show detailed status for a specific job (includes API response details)
uv run python -m mistral_ocr --job-status job_001

# Query all jobs associated with a document name
uv run python -m mistral_ocr --query-document "Annual_Report"

# Cancel a running job
uv run python -m mistral_ocr --cancel-job job_001
```

### Result Retrieval

Get and download OCR results:

```bash
# Retrieve results for a completed job (displays in terminal)
uv run python -m mistral_ocr --get-results job_001

# Download results to default location (XDG_DATA_HOME or ~/.local/share/mistral-ocr/)
uv run python -m mistral_ocr --download-results job_001

# Download results to a specific directory
uv run python -m mistral_ocr --download-results job_001 --download-to /path/to/save/results/

# Download all results for a document by name or UUID
uv run python -m mistral_ocr --download-document "Annual_Report" --download-to /path/to/save/
```

### Advanced Examples

Complex workflow examples:

```bash
# Process a large document archive with automatic batching
uv run python -m mistral_ocr --submit /archive/legal_documents/ --recursive \
  --document-name "Legal_Archive_2024" --model mistral-ocr-latest

# Submit, check status, and download results in sequence
uv run python -m mistral_ocr --submit contract.pdf --document-name "Contract_Review"
# Note the returned job ID, then:
uv run python -m mistral_ocr --check-job job_002
uv run python -m mistral_ocr --job-status job_002  # Get detailed status information
uv run python -m mistral_ocr --download-results job_002 --download-to ./processed_contracts/

# Monitor document processing status
uv run python -m mistral_ocr --query-document "Contract_Review"

# List all jobs and their current status
uv run python -m mistral_ocr --list-jobs
```

## Supported File Types

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
uv run python -m mistral_ocr --submit /large_archive/ --recursive --document-name "Archive_2024"
# Output: "Submitted 3 batch jobs: job_001, job_002, job_003"
```

## Error Handling

The tool provides detailed error messages for common issues:

- **File not found**: Clear indication of missing files or directories
- **Unsupported formats**: Lists supported file types
- **API errors**: Displays Mistral API error details
- **Job failures**: Status information for failed processing

## Development

```bash
# Run tests
pytest

# Lint and format code
ruff check
ruff format

# Type checking
mypy src/
```

## Directory Structure

The tool follows XDG Base Directory specification:

- **Config**: `~/.config/mistral-ocr/` (or `$XDG_CONFIG_HOME/mistral-ocr/`)
- **Data**: `~/.local/share/mistral-ocr/` (or `$XDG_DATA_HOME/mistral-ocr/`)
- **Cache**: `~/.cache/mistral-ocr/` (or `$XDG_CACHE_HOME/mistral-ocr/`)

## Help

Display help and available options:

```bash
uv run python -m mistral_ocr --help
```

## Implementation Notes

- This program is written in Python 3.12+
- The package is managed with `uv`
- Use `ruff` to lint or reformat
- Install the package with `uv pip install -e .`
- Run the command line program with `uv run python -m mistral_ocr`