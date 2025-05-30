# Contributing to Mistral OCR

> A comprehensive guide for developers contributing to the mistral-ocr project

## Quick Start

### Prerequisites
- Python 3.12+
- `uv` package manager (recommended) or `pip`
- Git

> **Note**: This project uses `uv` for package management. If you don't have `uv` installed, you can install it with `pip install uv` or use standard `pip` commands instead.

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/stevegsax/mistral-ocr.git
cd mistral-ocr

# Create and activate virtual environment (if not using uv)
# python -m venv .venv
# source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
uv pip install -e .

# Development dependencies are in pyproject.toml, install with:
# uv add --dev pytest mypy ruff (if not already in pyproject.toml)

# Run tests to verify setup
pytest

# Run CLI to verify installation
uv run python -m mistral_ocr --help
```

### First Contribution Workflow

1. **Understand the Architecture**: Read `ARCHITECTURE.md` for system overview and developer guide
2. **Check Current Work**: Review `specs/02_TODO.md` for open tasks
3. **Run the CLI**: `uv run python -m mistral_ocr --help`
4. **Run Tests**: `pytest tests/unit/` (should be fast)
5. **Make Changes**: Follow the TDD cycle in `PROCESS.md`
6. **Quality Checks**: `ruff check --fix && ruff format && mypy src/ && pytest`

## Architecture Overview

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Entry     │───▶│  MistralOCRClient │───▶│  Mistral API    │
│   (__main__.py) │    │   (client.py)     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
            ┌─────────────────────────────────────────────┐
            │           Component Managers                │
            ├─────────────────────────────────────────────┤
            │ • BatchSubmissionManager (file processing)  │
            │ • BatchJobManager (status tracking)         │
            │ • ResultManager (download handling)         │
            │ • DocumentManager (UUID/name association)   │
            │ • ProgressManager (UI updates)             │
            └─────────────────────────────────────────────┘
                              │
                              ▼
            ┌─────────────────────────────────────────────┐
            │              Storage Layer                  │
            ├─────────────────────────────────────────────┤
            │ • Database (SQLite - job tracking)         │
            │ • ConfigurationManager (settings)          │
            │ • XDG Paths (file organization)            │
            └─────────────────────────────────────────────┘
```

### Data Flow

1. **File Submission**: CLI → FileCollector → BatchSubmissionManager → Mistral API
2. **Job Tracking**: Database stores job metadata, BatchJobManager monitors status
3. **Result Retrieval**: ResultManager downloads and organizes completed jobs
4. **Progress Monitoring**: ProgressManager provides real-time UI updates

### Key Patterns

- **Manager Pattern**: Each major functionality has a dedicated manager class
- **Dependency Injection**: Components receive dependencies through constructors  
- **Pydantic Validation**: API responses are validated using Pydantic models
- **Retry with Backoff**: API operations use exponential backoff for resilience
- **Progress Tracking**: Rich library provides terminal UI with context managers
- **Type Safety**: Comprehensive type hints and runtime validation throughout
- **Structured Logging**: All operations use structured logging with audit trails

## Development Workflow

### Following the TDD Process

Our development follows the process in `PROCESS.md`:

1. **Feature Discovery**: Break down requirements into small, testable tasks
2. **Test-First Design**: Write failing tests that describe expected behavior
3. **Minimal Implementation**: Write just enough code to make tests pass
4. **Integration & Validation**: Run full test suite and quality checks
5. **Planning Next Iteration**: Update specs and plan next increment

### Code Organization

```
src/mistral_ocr/
├── __main__.py              # CLI entry point
├── client.py                # Main facade coordinating managers
├── batch_submission_manager.py  # File processing and batch creation
├── batch_job_manager.py     # Job status tracking and management
├── result_manager.py        # Result download and parsing  
├── document_manager.py      # Document naming and UUID handling
├── progress.py              # Progress tracking and UI updates
├── database.py              # SQLite operations and schema
├── db_models.py             # SQLAlchemy ORM models
├── config.py                # Configuration management
├── settings.py              # Unified settings facade
├── validation.py            # Input validation decorators
├── exceptions.py            # Custom exception hierarchy
├── data_types.py            # Pydantic models for API responses
├── models.py                # Legacy data models (being migrated)
├── parsing.py               # API response parsing with validation
├── constants.py             # Application constants
├── paths.py                 # XDG Base Directory management
├── audit.py                 # Audit logging and security events
├── async_utils.py           # Async/concurrency utilities
├── files.py                 # File handling and collection
├── logging.py               # Structured logging setup
└── utils/                   # Utility modules
    ├── file_operations.py   # File I/O and filesystem utilities
    └── retry_manager.py     # Retry logic with exponential backoff
```

## Data Validation Architecture

### Pydantic Models

The codebase uses **Pydantic** for robust data validation and type safety:

```python
# API Response Models (data_types.py)
@dataclass(config=ConfigDict(extra="forbid"))
class OCRPage:
    """Individual page result from API."""
    text: Optional[str] = None
    markdown: Optional[str] = None

@dataclass(config=ConfigDict(extra="forbid"))
class BatchResultEntry:
    """Single result from batch JSONL output."""
    custom_id: str
    response: OCRApiResponse

@dataclass(config=ConfigDict(extra="forbid"))
class ProcessedOCRResult:
    """Validated result ready for storage."""
    text: str
    markdown: str
    file_name: str
    job_id: str
    custom_id: str
```

### Validation Pipeline

API responses are automatically validated before processing:

```python
# In parsing.py - API response processing
def parse_batch_output(self, output_content: str, job_id: str) -> List[OCRResult]:
    for result_line in output_content.strip().split("\n"):
        try:
            result_data = json.loads(result_line)
            # Pydantic validation step
            batch_entry = BatchResultEntry(**result_data)
            # Process validated data
            ocr_result = self._process_batch_entry(batch_entry, job_id)
        except ValidationError as e:
            self.logger.warning(f"Failed to validate result structure: {e}")
```

### Benefits

1. **Type Safety**: Automatic validation of API responses
2. **Error Handling**: Clear validation error messages
3. **Documentation**: Self-documenting data structures
4. **IDE Support**: Better autocompletion and type checking

## Common Development Tasks

### Adding a New CLI Command

1. **Add argument parser** in `__main__.py`
2. **Create handler function** with appropriate validation
3. **Write tests** in `tests/unit/` or `tests/integration/`
4. **Update documentation** in README.md

### Adding a New File Type

1. **Update `constants.py`** with new MIME type and extension
2. **Add validation** in `files.py` FileCollector
3. **Update encoding logic** in `utils/file_operations.py`
4. **Add Pydantic models** in `data_types.py` if needed for API responses
5. **Write tests** for the new file type support

### Adding Configuration Options

1. **Add constant** in `constants.py`
2. **Update data model** in `data_types.py` ConfigData class
3. **Add methods** in `config.py` ConfigurationManager
4. **Expose in** `settings.py` Settings class
5. **Add CLI commands** in `__main__.py`
6. **Write tests** for new configuration options
7. **Update documentation**

### Debugging Common Issues

#### Mock vs Real Mode
```python
# Mock mode (default for tests)
client = MistralOCRClient(api_key="test")  # Automatically enables mock mode

# Real mode (for actual API calls)
client = MistralOCRClient(api_key="your-real-api-key")
```

#### Database Issues
```bash
# Check database location
uv run python -c "from mistral_ocr.settings import get_settings; print(get_settings().database_path)"

# Reset database (dev only)
rm ~/.local/share/mistral-ocr/mistral_ocr.db
```

#### Progress Tracking Issues
```python
# Disable progress for debugging
client.progress_manager.enabled = False

# Or via configuration
client.settings.set_progress_enabled(False)
```

## Testing Guidelines

### Test Organization
- **Unit tests**: `tests/unit/` - Fast, isolated, heavily mocked
- **Integration tests**: `tests/integration/` - End-to-end workflows
- **Shared fixtures**: `tests/conftest.py` and `tests/shared_fixtures.py`

### Running Tests
```bash
# Fast unit tests only
pytest tests/unit/ -v

# All tests with coverage
pytest --cov=src/mistral_ocr

# Specific test category
pytest tests/unit/test_file_submission.py -v

# Run with output capture disabled (for debugging)
pytest tests/unit/test_result_retrieval.py -v -s
```

### Writing New Tests
```python
# Use existing fixtures for consistency
def test_new_feature(client, tmp_path):
    """Test description following our docstring format."""
    # Reset mock counters for predictable behavior
    from mistral_ocr.result_manager import ResultManager
    ResultManager._mock_download_results_call_count = 0
    
    # Arrange
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"fake png content")
    
    # Act
    result = client.submit_documents([test_file])
    
    # Assert
    assert result.startswith("job_")
    
def test_pydantic_validation():
    """Test Pydantic model validation."""
    from mistral_ocr.data_types import ProcessedOCRResult
    
    # Valid data should work
    result = ProcessedOCRResult(
        text="Sample text",
        markdown="# Sample",
        file_name="test.pdf",
        job_id="job_123",
        custom_id="test_001"
    )
    assert result.text == "Sample text"
    
    # Invalid data should raise ValidationError
    with pytest.raises(ValidationError):
        ProcessedOCRResult(text="", markdown="")  # Missing required fields
```

## Code Quality Standards

### Required Checks
```bash
# Linting and formatting
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/

# Tests
pytest

# All checks in sequence
ruff check --fix && ruff format && mypy src/ && pytest
```

### Code Style
- **Line length**: 100 characters max
- **Type hints**: Required for all public interfaces
- **Docstrings**: Required for classes and public methods
- **Optional syntax**: Use `Optional[T]` instead of `T | None`

### Commit Guidelines
- Follow conventional commit format
- Reference issue numbers when applicable
- Include tests for new functionality
- Update documentation for user-facing changes

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure package is installed in development mode
uv pip install -e .

# Or with standard pip
pip install -e .
```

**Test Failures**
```bash
# Clean build artifacts
rm -rf build/ dist/ src/mistral_ocr.egg-info/

# Reset test database
rm -rf /tmp/pytest-of-*/

# Reset mock counters for predictable test behavior
# This is often needed when tests run in different orders
python -c "from mistral_ocr.result_manager import ResultManager; ResultManager._mock_download_results_call_count = 0"
```

**Pydantic Validation Errors**
```bash
# Check that your data matches the expected structure
# Validation errors will show which fields are missing or invalid
# Example: ValidationError: 1 validation error for BatchResultEntry

# Debug by examining the data structure in the debugger or logs
```

**API Rate Limiting**
```bash
# Use mock mode for development (default with api_key="test")
export MISTRAL_OCR_MOCK_MODE=1

# Or use test API key in code
client = MistralOCRClient(api_key="test")  # Automatically enables mock mode
```

### Getting Help

1. **Documentation**: Check `ARCHITECTURE.md` (developer guide), `PROCESS.md`, `README.md`, and this guide
2. **Module Reference**: See `ARCHITECTURE.md` for detailed module explanations and usage guidance
3. **Tests**: Look at existing tests for usage examples
4. **Issues**: Search existing GitHub issues
5. **Code**: The codebase has comprehensive docstrings and type hints

## Contributing Guidelines

### Before Submitting a PR
1. ✅ All tests pass: `pytest`
2. ✅ Code quality checks pass: `ruff check --fix && ruff format && mypy src/`
3. ✅ New Pydantic models added for any new API data structures
4. ✅ Documentation updated (if user-facing changes)
5. ✅ Followed TDD process from `PROCESS.md`

### PR Requirements
- Clear description of changes and motivation
- Tests for new functionality
- Documentation updates for user-facing changes
- Follows existing code patterns and architecture

### Review Process
1. Automated checks must pass (tests, linting, type checking)
2. Code review for design and implementation
3. Documentation review for clarity and completeness
4. Integration testing for complex changes

Welcome to the project! The codebase is well-structured and thoroughly tested, making it a great environment for learning and contributing.