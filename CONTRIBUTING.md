# Contributing to Mistral OCR - Simplified

> A streamlined guide for contributing to the simplified mistral-ocr project

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

# Install in development mode
uv pip install -e .

# Run tests to verify setup
pytest

# Run CLI to verify installation
uv run python -m mistral_ocr --help
```

### First Contribution Workflow

1. **Understand the Simplified Architecture**: Read `ARCHITECTURE.md` for the streamlined system overview
2. **Run the CLI**: `uv run python -m mistral_ocr --help`
3. **Run Tests**: `pytest` (all 50 tests should pass in ~8 seconds)
4. **Make Changes**: Follow simple test-driven development
5. **Quality Checks**: `ruff check --fix && ruff format && mypy src/ && pytest`

## Simplified Architecture Overview

### Core Components (2 Classes)

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Entry     │───▶│ SimpleMistral    │───▶│  Mistral API    │
│ (simple_cli.py) │    │ OCRClient        │    │                 │
└─────────────────┘    │(simple_client.py)│    └─────────────────┘
                       └──────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   OCRDatabase   │
                       │   (SQLite)      │
                       └─────────────────┘
```

### Data Flow

1. **File Submission**: CLI → File validation → Base64 encoding → Mistral API → Database storage
2. **Job Tracking**: Simple status checks with database caching
3. **Result Retrieval**: Download OCR results and store text content in database
4. **Search**: SQL LIKE queries on stored OCR content

### Key Principles

- **Simplicity First**: No unnecessary abstractions or enterprise patterns
- **Single Responsibility**: Each component has one clear purpose
- **User-Focused**: Optimize for actual user workflows
- **Type Safety**: Use `Optional[T]` instead of `T | None` (per CLAUDE.md)
- **Direct Error Handling**: Simple try/catch without complex retry mechanisms

## Development Workflow

### Simple TDD Process

1. **Write a failing test** that describes the expected behavior
2. **Write minimal code** to make the test pass
3. **Run quality checks** to ensure code meets standards
4. **Commit and iterate**

### Code Organization (6 Files Total)

```
src/mistral_ocr/
├── __init__.py              # Simple exports (14 lines)
├── __main__.py              # CLI entry point (7 lines)
├── simple_cli.py            # CLI commands (200 lines)
├── simple_client.py         # Core functionality (330 lines)
├── data_types.py            # Pydantic models (kept from enterprise)
└── _version.py              # Version info
```

## Common Development Tasks

### Adding a New CLI Command

1. **Add command function** in `simple_cli.py`:
```python
def new_command(args: Any) -> int:
    """New command implementation."""
    client = SimpleMistralOCRClient()
    try:
        result = client.new_method(args.param)
        print(f"Result: {result}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
```

2. **Add argument parser** in `main()` function:
```python
new_parser = subparsers.add_parser('new-cmd', help='New command')
new_parser.add_argument('param', help='Parameter')
new_parser.set_defaults(func=new_command)
```

3. **Write tests** in `tests/unit/test_cli_subcommands.py` or `tests/integration/test_cli_integration.py`

### Adding a New Client Method

1. **Add method** to `SimpleMistralOCRClient` class:
```python
def new_method(self, param: str) -> str:
    """New functionality."""
    # Validate input
    if not param:
        raise ValueError("Parameter required")
    
    # Database operation if needed
    result = self.db.some_operation(param)
    
    # API call if needed (with simple error handling)
    try:
        api_result = self.client.some_api_call(param)
        return str(api_result)
    except Exception as e:
        raise ValueError(f"API error: {e}")
```

2. **Add database operations** if needed in `OCRDatabase` class:
```python
def some_operation(self, param: str) -> List[Dict]:
    """Database operation."""
    rows = self.connection.execute(
        "SELECT * FROM table WHERE column = ?", (param,)
    ).fetchall()
    return [dict(row) for row in rows]
```

### Adding New File Type Support

1. **Update file detection** in `simple_cli.py`:
```python
# In submit_command function, add new extension
for ext in ['*.png', '*.jpg', '*.jpeg', '*.pdf', '*.newext']:
    files.extend(path.glob(ext))
```

2. **Update encoding logic** in `simple_client.py`:
```python
# In _create_batch_file method
if file_ext in ['.png', '.jpg', '.jpeg']:
    mime_type = f"image/{'jpeg' if file_ext in ['.jpg', '.jpeg'] else 'png'}"
elif file_ext == '.newext':
    mime_type = "application/new-format"
else:
    mime_type = "application/pdf"
```

3. **Write tests** for the new file type

## Testing Guidelines

### Test Structure (50 Tests Total)

```
tests/
├── unit/                           # 29 tests - Core functionality
│   ├── test_simple_client.py      # 17 tests - Client and database
│   └── test_cli_subcommands.py    # 12 tests - CLI validation
├── integration/                    # 21 tests - Complete workflows
│   └── test_cli_integration.py    # End-to-end CLI testing
├── conftest.py                     # Simple fixtures
├── shared_fixtures.py             # Test utilities
└── factories.py                    # Test data creation
```

### Running Tests

```bash
# All tests (fast - ~8 seconds)
pytest

# Specific test categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests only
pytest tests/unit/test_simple_client.py -v  # Specific module

# With coverage
pytest --cov=src/mistral_ocr
```

### Writing New Tests

```python
# Unit test example
def test_new_functionality(tmp_path):
    """Test new functionality."""
    client = SimpleMistralOCRClient(api_key="test-key", db_path=str(tmp_path / "test.db"))
    
    # Test the functionality
    result = client.new_method("test_param")
    assert result == "expected_value"
    
    # Clean up
    client.db.close()

# Integration test example
def test_cli_new_command():
    """Test new CLI command."""
    result = run_cli("new-cmd", "test_param", env_vars={"MISTRAL_API_KEY": "test-key"})
    
    assert result.returncode == 0
    assert "expected output" in result.stdout
```

## Code Quality Standards

### Required Checks

```bash
# Auto-fix style issues
ruff check --fix
ruff format

# Type checking
mypy src/

# Tests
pytest

# All checks in sequence
ruff check --fix && ruff format && mypy src/ && pytest
```

### Code Style

- **Line length**: 100 characters max
- **Type hints**: Required for all functions and methods
- **Optional syntax**: Use `Optional[T]` instead of `T | None` (per CLAUDE.md)
- **Error handling**: Simple try/catch blocks, not complex retry mechanisms
- **Docstrings**: Required for classes and public methods

### Example Code Style

```python
def example_method(self, param: Optional[str] = None) -> List[Dict]:
    """Example method with proper style.
    
    Args:
        param: Optional parameter description
        
    Returns:
        List of dictionaries with results
        
    Raises:
        ValueError: If param is invalid
    """
    if param is None:
        param = "default_value"
    
    try:
        results = self._process_param(param)
        return results
    except Exception as e:
        raise ValueError(f"Processing failed: {e}")
```

## Debugging Common Issues

### Database Issues

```bash
# Check database location
python -c "from mistral_ocr.simple_client import SimpleMistralOCRClient; client = SimpleMistralOCRClient(api_key='test'); print(client.db.db_path)"

# Reset database for testing
rm ~/.mistral-ocr/database.db
```

### API Issues

```bash
# Test with mock client (no real API calls)
python -c "from mistral_ocr import SimpleMistralOCRClient; client = SimpleMistralOCRClient(api_key='test'); print('Mock client works')"

# Test CLI without API key (should show error)
uv run python -m mistral_ocr submit test.png
```

### Import Issues

```bash
# Reinstall in development mode
uv pip install -e .

# Verify installation
python -c "from mistral_ocr import SimpleMistralOCRClient; print('Import successful')"
```

## Migration from Enterprise Version

### What Changed

**Removed (80% reduction)**:
- Complex manager classes (5 → 0)
- Async/await utilities
- Progress tracking with Rich UI
- Audit logging and security events
- Retry mechanisms with exponential backoff
- Complex configuration management
- SQLAlchemy ORM complexity

**Kept (Essential features)**:
- Core OCR functionality
- Database content storage
- Search capabilities
- Type safety
- CLI interface

### API Compatibility

Basic operations remain similar:

```python
# Enterprise version
client = MistralOCRClient(api_key="key")
job_id = client.submit_documents(files, document_name="Doc")
results = client.get_results(job_id)

# Simplified version
client = SimpleMistralOCRClient(api_key="key")
job_id = client.submit(files, "Doc")
results = client.results(job_id)
```

## Contributing Guidelines

### Before Submitting a PR

1. ✅ All tests pass: `pytest`
2. ✅ Code quality checks pass: `ruff check --fix && ruff format && mypy src/`
3. ✅ New functionality has tests
4. ✅ Documentation updated (if user-facing changes)
5. ✅ Follows simplified architecture patterns

### PR Requirements

- **Clear description**: What changes and why
- **Tests included**: For any new functionality
- **Simple approach**: No unnecessary complexity
- **Type safety**: Proper type annotations
- **User focus**: Changes should benefit actual users

### Example PR Checklist

```
- [ ] Added new CLI command with proper error handling
- [ ] Added unit tests for new functionality
- [ ] Added integration test for CLI workflow
- [ ] Updated help text and examples
- [ ] All existing tests still pass
- [ ] Code follows style guidelines
- [ ] No enterprise-style complexity introduced
```

## Architecture Guidelines

### Do's

✅ **Simple Functions**: Single responsibility, clear purpose
✅ **Direct Error Handling**: Simple try/catch blocks
✅ **Type Safety**: Use `Optional[T]` syntax
✅ **User-Focused**: Optimize for real workflows
✅ **SQLite Operations**: Direct database queries
✅ **Clear CLI Commands**: Simple argument parsing

### Don'ts

❌ **Complex Managers**: No manager pattern abstractions
❌ **Async/Await**: Keep operations synchronous
❌ **Enterprise Patterns**: No dependency injection complexity
❌ **Complex Retry Logic**: Simple error handling only
❌ **ORM Complexity**: Use direct SQLite operations
❌ **Nested Commands**: Keep CLI structure flat

## Getting Help

1. **Architecture Guide**: `ARCHITECTURE.md` explains the simplified system
2. **Test Examples**: Look at existing tests for usage patterns
3. **Code Examples**: The simplified codebase is easy to read and understand
4. **Issues**: Search existing GitHub issues for similar problems

## Performance Considerations

The simplified architecture provides:

- **Fast Startup**: ~100ms (vs 500ms enterprise version)
- **Low Memory**: ~10MB (vs 50MB enterprise version)
- **Quick Tests**: 50 tests in ~8 seconds
- **Simple Operations**: Direct SQLite queries vs ORM overhead

## Future Extensions

When adding new features, maintain the simplified approach:

1. **New Commands**: Add single functions to `simple_cli.py`
2. **New Client Methods**: Add to `SimpleMistralOCRClient` class
3. **Database Features**: Add simple methods to `OCRDatabase`
4. **Configuration**: Use environment variables only

Remember: **Simplicity is a feature**. The 80% reduction in code complexity makes the system more reliable, maintainable, and developer-friendly while preserving 100% of essential user functionality.

Welcome to the simplified Mistral OCR project! The streamlined architecture makes it an excellent environment for learning and contributing.