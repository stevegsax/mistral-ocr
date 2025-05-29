# Test Organization

This directory contains the reorganized test suite for Mistral OCR. The tests have been split from one large file into focused, maintainable modules.

## Structure

```
tests/
├── unit/                           # Unit tests for individual components
│   ├── test_async_utils.py        # Async utilities and concurrent processing
│   ├── test_basic_integrity.py    # Basic system integrity and setup
│   ├── test_document_management.py # Document naming and association  
│   ├── test_file_operations.py    # File handling utilities
│   ├── test_file_submission.py    # File submission functionality
│   ├── test_job_management.py     # Job status and management
│   ├── test_result_retrieval.py   # Result download and retrieval
│   └── test_validation.py         # Input validation decorators
├── integration/                    # Integration and workflow tests
│   ├── test_advanced_options.py   # Advanced CLI functionality
│   ├── test_error_handling.py     # Error scenarios and recovery
│   ├── test_integration.py        # Complete workflow tests
│   └── test_job_status_listing.py # Job listing and API refresh
├── conftest.py                     # Shared test configuration
├── shared_fixtures.py             # Reusable test fixtures
└── test_mistral_ocr.py.original   # Archived original large test file
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Scope**: Individual components and functions
- **Speed**: Fast execution (< 100ms per test)
- **Isolation**: Heavy use of mocks, no external dependencies
- **Purpose**: Verify component behavior in isolation

### Integration Tests (`tests/integration/`)
- **Scope**: Complete workflows and interactions
- **Speed**: Slower execution (100ms - 2s per test)  
- **Realism**: Mix of mocks and real component interactions
- **Purpose**: Verify end-to-end functionality

## Running Tests

```bash
# Run all tests
uv run pytest

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests  
uv run pytest tests/integration/

# Run specific test module
uv run pytest tests/unit/test_file_submission.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/mistral_ocr
```

## Key Improvements

1. **Focused Modules**: Each test file has a clear, single responsibility
2. **Shared Fixtures**: Common test setup in `shared_fixtures.py` and `conftest.py`
3. **Proper Categorization**: Unit vs integration tests clearly separated
4. **Maintainable Size**: No test file exceeds 200 lines
5. **Consistent Patterns**: Standardized fixture usage and test structure

## Test Dependencies

- All tests use the existing `conftest.py` fixtures
- Shared utilities available in `shared_fixtures.py`
- Mock mode enabled by default for isolation
- Temporary directories for database isolation

## Migration Notes

The original `test_mistral_ocr.py` (600+ lines) has been split into 11 focused modules:

- `TestBasicIntegrity` → `test_basic_integrity.py` (34 lines)
- `TestFileSubmission` → `test_file_submission.py` (65 lines)  
- `TestDocumentManagement` → `test_document_management.py` (30 lines)
- `TestJobManagement` → `test_job_management.py` (25 lines)
- `TestResultRetrieval` → `test_result_retrieval.py` (45 lines)
- `TestJobStatusListing` → `test_job_status_listing.py` (190 lines) 
- `TestAdvancedOptions` → `test_advanced_options.py` (60 lines)

All tests maintain the same functionality while being more maintainable and focused.