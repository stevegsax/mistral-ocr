# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Package Management
- Use `uv` for all package management instead of pip
- Add dependencies: `uv add <package>`
- Install in development mode: `uv pip install -e .`
- Run the CLI: `uv run python -m mistral_ocr`

### Development
- Activate virtual environment: `source .venv/bin/activate`
- Run tests: `pytest`
- Lint and format: `ruff check` and `ruff format`
- Type checking: `mypy src/`

### Testing
- Run all tests: `pytest`
- Run specific test: `pytest tests/test_mistral_ocr.py::test_name`
- Tests use xfail markers for unimplemented features

### CLI Commands

#### Document Submission
- Submit file: `uv run python -m mistral_ocr submit /path/to/file.pdf`
- Submit directory: `uv run python -m mistral_ocr submit /path/to/dir --recursive`
- Submit with options: `uv run python -m mistral_ocr submit /path --name "My Document" --model "mistral-ocr-latest"`

#### Job Management  
- List all jobs: `uv run python -m mistral_ocr jobs list`
- Check job status: `uv run python -m mistral_ocr jobs status <job-id>`
- Cancel job: `uv run python -m mistral_ocr jobs cancel <job-id>`

#### Results Management
- View job results: `uv run python -m mistral_ocr results get <job-id>`
- Download job results: `uv run python -m mistral_ocr results download <job-id> --output /path`

#### Document Management
- Query document: `uv run python -m mistral_ocr documents query "document-name"`
- Download document: `uv run python -m mistral_ocr documents download "document-name" --output /path`

#### Configuration
- Show configuration: `uv run python -m mistral_ocr config show`
- Set API key: `uv run python -m mistral_ocr config set api-key "your-key"`
- Set default model: `uv run python -m mistral_ocr config set model "model-name"`
- Set download directory: `uv run python -m mistral_ocr config set download-dir "/path"`
- Reset to defaults: `uv run python -m mistral_ocr config reset`

### Logging and Monitoring
- Log files location: `~/.local/state/mistral-ocr/`
  - `mistral.log` - Main application log
  - `audit.log` - Audit trail events
  - `security.log` - Authentication and security events
  - `performance.log` - Performance metrics and timing
- Monitor real-time: `tail -f ~/.local/state/mistral-ocr/mistral.log`
- Analyze with jq: `jq 'select(.outcome == "failure")' ~/.local/state/mistral-ocr/audit.log`

## Architecture

This is a Python CLI tool for submitting OCR batches to the Mistral API. The architecture follows a structured 7-phase development process defined in `PROCESS.md` that must be followed in order:

1. Requirements Analysis
2. Architectural Analysis 
3. First Pass Implementation Design (pseudocode)
4. Test Design
5. Test Case Enumeration
6. Test Implementation
7. Implementation

### Core Components
- **CLI Interface**: Command-line entry point in `__main__.py`
- **Client Layer**: `MistralOCRClient` for API interactions
- **Configuration**: `ConfigurationManager` for settings
- **Database**: Local job tracking and document management
- **Progress Tracking**: `ProgressManager` for real-time UI updates (Rich library)
- **Audit System**: Comprehensive logging and audit trails (`audit.py`)
- **Error Recovery**: Retry mechanisms with exponential backoff (`retry_manager.py`)

### Key Features
- Submit individual files or directories (with recursive option)
- Automatic batch partitioning (100 files max per batch)
- Document naming and UUID-based association
- Job status tracking and cancellation
- Result retrieval and automatic download
- Configuration management via CLI commands
- Real-time progress tracking with Rich UI components
- Live job monitoring with status change notifications
- Comprehensive audit trails and security logging
- Enterprise-grade error recovery and retry mechanisms
- Performance monitoring and metrics collection
- Support for PNG, JPEG, and PDF files

## Development Rules

- Follow the structured process in `PROCESS.md` - complete each phase before moving to the next
- Do not change existing tests unless explicitly instructed
- All tests are currently marked with `@pytest.mark.xfail` as placeholders for TDD approach
- Use type hints throughout (configured in pyproject.toml)
- Line length limit: 100 characters
- Python 3.12+ required

## Code Style
- When creating method signatures, use `Optional` rather than union syntax (`| None`)
