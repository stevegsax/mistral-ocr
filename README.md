# mistral-ocr

> Command line tool to submit, track, and retrieve OCR batches to the Mistral API

A Python CLI tool for submitting documents to the Mistral OCR service, managing batch jobs, and retrieving results. Supports PNG, JPEG, and PDF files with automatic batch partitioning and document management.

## Features

- **File Submission**: Submit individual files or entire directories for OCR processing
- **Batch Processing**: Automatic partitioning for 100+ files per Mistral API limits
- **Document Management**: Associate files with named documents using UUIDs
- **Job Tracking**: Check status, cancel jobs, and query by document name
- **Result Retrieval**: Download OCR results in text and markdown formats
- **Configuration Management**: CLI commands for API key, model, and directory settings
- **Progress Monitoring**: Real-time progress bars and status updates during processing
- **Comprehensive Logging**: Enterprise-grade audit trails, security events, and performance metrics
- **Error Recovery**: Automatic retry with exponential backoff for transient failures
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

### API Key Setup

Set your Mistral API key using one of these methods:

**Option 1: Environment Variable**
```bash
export MISTRAL_API_KEY="your-api-key-here"
```

**Option 2: Configuration File**
```bash
# Set API key in configuration file (~/.config/mistral-ocr/config.json)
uv run python -m mistral_ocr config set api-key "your-api-key-here"
```

### Configuration Management

Use the built-in configuration commands to manage your settings:

```bash
# Show current configuration (API key is hidden for security)
uv run python -m mistral_ocr config show

# Set default OCR model
uv run python -m mistral_ocr config set model "pixtral-12b-2412"

# Set default download directory
uv run python -m mistral_ocr config set download-dir "/path/to/downloads"

# Reset all settings to defaults (preserves API key)
uv run python -m mistral_ocr config reset
```

### Progress Monitoring Settings

Progress monitoring is now configured through the main configuration system. The new CLI structure provides a cleaner interface for these settings, which are managed through the unified `config set` command.

### Logging and Audit Trails

Mistral OCR provides comprehensive logging and audit trails for enterprise use, compliance, and debugging. All operations are tracked with structured logs including timing, outcomes, and context.

#### Log Files Location

Logs are stored in the XDG-compliant data directory:

```bash
# Default log locations
~/.local/share/mistral-ocr/mistral.log      # Main application log
~/.local/share/mistral-ocr/audit.log        # Audit trail events
~/.local/share/mistral-ocr/security.log     # Authentication & security events
~/.local/share/mistral-ocr/performance.log  # Performance metrics & timing
```

#### Log Configuration

The logging system automatically configures:
- **Log Rotation**: 50MB max per file, 5 backup files retained
- **Structured Format**: JSON format for programmatic analysis
- **Console Output**: Colored, human-readable format for terminals
- **Security**: API keys are automatically hashed, never logged in plain text

#### What Gets Logged

**Audit Events:**
- CLI command execution with full parameters and timing
- Configuration changes (API key, model, directories)
- Authentication events and client initialization
- File operations (submission, download, access)
- Job lifecycle (creation, status changes, completion)
- Error recovery and retry attempts

**Security Events:**
- API key validation and authentication outcomes
- Data access patterns and file operations
- Configuration modifications with before/after context
- Failed authentication attempts

**Performance Metrics:**
- Operation timing and duration
- Batch processing throughput
- API request/response times
- Resource usage (memory, disk, network)
- Concurrent operation efficiency

#### Example Log Outputs

**CLI Command Audit:**
```json
{
  "event": "Started mistral-ocr CLI",
  "level": "info",
  "timestamp": "2025-05-29T12:33:00Z",
  "event_type": "application_start",
  "component": "cli",
  "session_id": "bcdff1c8",
  "operation": "submit:documents/",
  "outcome": "success",
  "version": "0.6.0",
  "args": {
    "submit": "documents/",
    "recursive": true,
    "document_name": "Invoice_Batch_2024"
  }
}
```

**Authentication Event:**
```json
{
  "event": "Authentication: API key loaded from configuration/environment",
  "level": "info",
  "timestamp": "2025-05-29T12:33:01Z",
  "security": true,
  "component": "client.security",
  "authentication_event": "API key loaded from configuration/environment",
  "outcome": "success",
  "api_key_hash": "a1b2c3d4e5f6g7h8"
}
```

**Performance Metrics:**
```json
{
  "event": "Performance: batch_submission",
  "level": "info",
  "timestamp": "2025-05-29T12:33:15Z",
  "performance": true,
  "component": "submission_manager.performance",
  "operation": "batch_submission",
  "duration_seconds": 14.527,
  "resource_count": 125,
  "resource_size_bytes": 52428800,
  "throughput_items_per_second": 8.62
}
```

**Operation Context:**
```json
{
  "event": "Completed document_submission",
  "level": "info", 
  "timestamp": "2025-05-29T12:33:15Z",
  "event_type": "file_submission",
  "component": "submission_manager",
  "session_id": "bcdff1c8",
  "operation": "document_submission",
  "operation_id": "f4a8b2c1",
  "resource_id": "Document_Invoice_Batch_2024",
  "outcome": "success",
  "duration_seconds": 14.527,
  "batch_count": 2,
  "file_count": 125,
  "job_ids": ["job_123", "job_124"]
}
```

#### Viewing Logs

**Real-time monitoring:**
```bash
# Monitor main application log
tail -f ~/.local/share/mistral-ocr/mistral.log

# Watch audit events in real-time  
tail -f ~/.local/share/mistral-ocr/audit.log | jq '.'

# Monitor security events
tail -f ~/.local/share/mistral-ocr/security.log | jq '.'
```

**Log analysis with jq:**
```bash
# Find all failed operations
jq 'select(.outcome == "failure")' ~/.local/share/mistral-ocr/audit.log

# Get performance metrics for specific operations
jq 'select(.performance == true and .operation == "batch_submission")' \
   ~/.local/share/mistral-ocr/performance.log

# Track a specific session
jq 'select(.session_id == "bcdff1c8")' ~/.local/share/mistral-ocr/mistral.log

# Authentication events summary
jq 'select(.security == true) | {timestamp, event, outcome}' \
   ~/.local/share/mistral-ocr/security.log
```

#### Enterprise Features

- **Session Correlation**: All operations within a CLI session share a session ID for debugging
- **Audit Compliance**: Complete operation trails with timing and outcomes
- **Security Monitoring**: Authentication events, failed access attempts, configuration changes
- **Performance Insights**: Detailed metrics for optimization and capacity planning
- **Error Context**: Rich error information with retry attempts and recovery actions

**Configuration File Location**: `~/.config/mistral-ocr/config.json` (follows XDG Base Directory specification)

## Usage Examples

### Basic File Submission

Submit a single file for OCR processing:

```bash
# Submit a single image file
uv run python -m mistral_ocr submit document.png

# Submit a PDF document
uv run python -m mistral_ocr submit report.pdf

# Submit with a custom model
uv run python -m mistral_ocr submit image.jpg --model mistral-ocr-latest
```

### Directory Processing

Submit entire directories with various options:

```bash
# Submit all supported files in a directory (non-recursive)
uv run python -m mistral_ocr submit /path/to/documents/

# Submit all files recursively (includes subdirectories)
uv run python -m mistral_ocr submit /path/to/documents/ --recursive

# Submit directory with document naming
uv run python -m mistral_ocr submit /path/to/invoices/ --recursive --name "Q4_Invoices"
```

### Document Management

Associate files with named documents for better organization:

```bash
# Create a new document with a specific name
uv run python -m mistral_ocr submit page1.png --name "Annual_Report"

# Add more pages to the same document (creates new document if name doesn't exist)
uv run python -m mistral_ocr submit page2.png --name "Annual_Report"

# Add pages to a specific document by UUID
uv run python -m mistral_ocr submit page3.png --uuid "123e4567-e89b-12d3-a456-426614174000"
```

### Job Management

Track and manage your OCR jobs:

```bash
# List all jobs with their status
uv run python -m mistral_ocr jobs list

# Show detailed status for a specific job (includes API response details)
uv run python -m mistral_ocr jobs status job_001

# Cancel a running job
uv run python -m mistral_ocr jobs cancel job_001
```

### Result Retrieval

Get and download OCR results:

```bash
# Retrieve results for a completed job (displays in terminal)
uv run python -m mistral_ocr results get job_001

# Download results to default location (XDG_DATA_HOME or ~/.local/share/mistral-ocr/)
uv run python -m mistral_ocr results download job_001

# Download results to a specific directory
uv run python -m mistral_ocr results download job_001 --output /path/to/save/results/

# Download all results for a document by name or UUID
uv run python -m mistral_ocr documents download "Annual_Report" --output /path/to/save/
```

### Document Queries

Query and manage documents:

```bash
# Query all jobs associated with a document name
uv run python -m mistral_ocr documents query "Annual_Report"

# Download all results for a document
uv run python -m mistral_ocr documents download "Annual_Report" --output /path/to/save/
```

**Progress Features:**
- **Multi-phase tracking**: Separate progress bars for different operation phases
- **Upload progress**: Real-time file upload progress with transfer speeds
- **Status notifications**: Emoji-enhanced status change announcements
- **Live monitoring**: Real-time job status updates with automatic refresh
- **Graceful degradation**: Automatically disabled in non-interactive terminals

### Advanced Examples

Complex workflow examples:

```bash
# Process a large document archive with automatic batching
uv run python -m mistral_ocr submit /archive/legal_documents/ --recursive \
  --name "Legal_Archive_2024" --model mistral-ocr-latest

# Submit, check status, and download results in sequence
uv run python -m mistral_ocr submit contract.pdf --name "Contract_Review"
# Note the returned job ID, then:
uv run python -m mistral_ocr jobs status job_002  # Get detailed status information
uv run python -m mistral_ocr results download job_002 --output ./processed_contracts/

# Monitor document processing status
uv run python -m mistral_ocr documents query "Contract_Review"

# List all jobs and their current status
uv run python -m mistral_ocr jobs list
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
uv run python -m mistral_ocr submit /large_archive/ --recursive --name "Archive_2024"
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
  - `config.json` - Application configuration settings
- **Data**: `~/.local/share/mistral-ocr/` (or `$XDG_DATA_HOME/mistral-ocr/`)
  - `downloads/` - Downloaded OCR results
  - `mistral_ocr.db` - SQLite database for job tracking
- **State**: `~/.local/state/mistral-ocr/` (or `$XDG_STATE_HOME/mistral-ocr/`)
  - `mistral.log` - Main application log
  - `audit.log` - Audit trail events  
  - `security.log` - Authentication and security events
  - `performance.log` - Performance metrics and timing
- **Cache**: `~/.cache/mistral-ocr/` (or `$XDG_CACHE_HOME/mistral-ocr/`)

## Help

Display help and available options:

```bash
uv run python -m mistral_ocr --help
```

**Available Commands:**
- **submit**: Submit files for OCR processing
  - `submit <path>` - Submit file or directory
  - `--recursive` - Process directories recursively
  - `--name NAME` - Associate with document name
  - `--uuid UUID` - Associate with document UUID
  - `--model MODEL` - Specify OCR model
- **jobs**: Manage OCR jobs
  - `jobs list` - List all jobs
  - `jobs status <job-id>` - Show detailed job status
  - `jobs cancel <job-id>` - Cancel a job
- **results**: Manage job results
  - `results get <job-id>` - Display job results
  - `results download <job-id>` - Download job results
  - `--output DIR` - Specify output directory
- **documents**: Manage documents
  - `documents query <name-or-uuid>` - Query document status
  - `documents download <name-or-uuid>` - Download document results
  - `--output DIR` - Specify output directory
- **config**: Manage configuration
  - `config show` - Show current configuration
  - `config reset` - Reset to defaults
  - `config set <key> <value>` - Set configuration values
    - Keys: `api-key`, `model`, `download-dir`

## Implementation Notes

- This program is written in Python 3.12+
- The package is managed with `uv`
- Use `ruff` to lint or reformat
- Install the package with `uv pip install -e .`
- Run the command line program with `uv run python -m mistral_ocr`

## Developer Documentation

### For Contributors
- **[Contributing Guide](CONTRIBUTING.md)**: Complete developer setup and contribution workflow
- **[Architecture Documentation](ARCHITECTURE.md)**: Deep dive into system design and patterns
- **[Process Guide](PROCESS.md)**: Test-driven development methodology

### For API Users
- **[API Reference](API.md)**: Complete Python API for programmatic usage
- **[Examples](examples/)**: Working code examples for integration

### Reference Documentation
- **[Mistral API Spec](reference/plugin-redoc-0.yaml)**: OpenAPI specification for the Mistral API
- **[API Documentation](reference/)**: Comprehensive Mistral API documentation
- **[Implementation Example](examples/main.py)**: Working example of direct API usage

