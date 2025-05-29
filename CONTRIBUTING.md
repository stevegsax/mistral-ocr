# Contributing to Mistral OCR

> A comprehensive guide for developers contributing to the mistral-ocr project

## Quick Start

### Prerequisites
- Python 3.12+
- `uv` package manager
- Git

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/stevegsax/mistral-ocr.git
cd mistral-ocr

# Activate virtual environment  
source .venv/bin/activate

# Install in development mode
uv pip install -e .

# Install development dependencies
uv add --dev pytest mypy ruff

# Run tests to verify setup
uv run pytest
```

### First Contribution Workflow

1. **Understand the Process**: Read `PROCESS.md` for our TDD approach
2. **Check Current Work**: Review `specs/02_TODO.md` for open tasks
3. **Run the CLI**: `uv run python -m mistral_ocr --help`
4. **Run Tests**: `uv run pytest tests/unit/` (should be fast)
5. **Make Changes**: Follow the TDD cycle in `PROCESS.md`
6. **Quality Checks**: `ruff check && ruff format && mypy src/`

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
- **Retry with Backoff**: API operations use exponential backoff for resilience
- **Progress Tracking**: Rich library provides terminal UI with context managers
- **Type Safety**: Comprehensive type hints throughout the codebase

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
├── config.py                # Configuration management
├── settings.py              # Unified settings facade
├── validation.py            # Input validation decorators
├── exceptions.py            # Custom exception hierarchy
├── types.py                 # TypedDict definitions
├── constants.py             # Application constants
└── utils/                   # Utility modules
    ├── file_operations.py   # File handling utilities
    └── retry_manager.py     # Retry logic with backoff
```

## Common Development Tasks

### Adding a New CLI Command

1. **Add argument parser** in `__main__.py`
2. **Create handler function** with appropriate validation
3. **Write tests** in `tests/unit/` or `tests/integration/`
4. **Update documentation** in README.md

### Adding a New File Type

1. **Update `constants.py`** with new MIME type and extension
2. **Add validation** in `files.py` FileCollector
3. **Test encoding** in `utils/file_operations.py`
4. **Write tests** for the new file type support

### Adding Configuration Options

1. **Add constant** in `constants.py`
2. **Add methods** in `config.py` ConfigurationManager
3. **Expose in** `settings.py` Settings class
4. **Add CLI commands** in `__main__.py`
5. **Update documentation**

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
uv run pytest tests/unit/ -v

# All tests with coverage
uv run pytest --cov=src/mistral_ocr

# Specific test category
uv run pytest tests/unit/test_file_submission.py -v
```

### Writing New Tests
```python
# Use existing fixtures for consistency
def test_new_feature(client, tmp_path):
    """Test description following our docstring format."""
    # Arrange
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"fake png content")
    
    # Act
    result = client.submit_documents([test_file])
    
    # Assert
    assert result.startswith("job_")
```

## Code Quality Standards

### Required Checks
```bash
# Linting and formatting
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run mypy src/

# Tests
uv run pytest
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
```

**Test Failures**
```bash
# Clean build artifacts
rm -rf build/ dist/ src/mistral_ocr.egg-info/

# Reset test database
rm -rf /tmp/pytest-of-*/
```

**API Rate Limiting**
```bash
# Use mock mode for development
export MISTRAL_OCR_MOCK_MODE=1
```

### Getting Help

1. **Documentation**: Check `PROCESS.md`, `README.md`, and this guide
2. **Tests**: Look at existing tests for usage examples
3. **Issues**: Search existing GitHub issues
4. **Code**: The codebase has comprehensive docstrings and type hints

## Contributing Guidelines

### Before Submitting a PR
1. ✅ All tests pass: `uv run pytest`
2. ✅ Code quality checks pass: `ruff check && mypy src/`
3. ✅ Documentation updated (if user-facing changes)
4. ✅ Followed TDD process from `PROCESS.md`

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