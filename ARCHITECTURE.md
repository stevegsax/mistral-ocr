# Architecture Documentation

> Deep dive into the mistral-ocr system architecture, design patterns, and component relationships
> 
> **For Developers**: This document explains how to understand, navigate, and extend the codebase

## System Overview

Mistral OCR is a Python CLI tool that provides a robust interface to the Mistral OCR API with local job tracking, batch processing, and progress monitoring capabilities.

### Core Principles

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Dependency Injection**: Components receive dependencies through constructors
3. **Fail-Safe Operation**: Extensive error handling and retry mechanisms
4. **User Experience**: Rich progress feedback and intuitive CLI interface
5. **Type Safety**: Comprehensive type annotations throughout

## Component Architecture

### High-Level Component Diagram

```
                              ┌─────────────────┐
                              │   CLI Layer     │
                              │  (__main__.py)  │
                              └─────────┬───────┘
                                        │
                                        ▼
                              ┌─────────────────┐
                              │ Client Facade   │
                              │  (client.py)    │
                              └─────────┬───────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
        ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
        │ Submission      │ │ Job Management  │ │ Result          │
        │ Manager         │ │ Manager         │ │ Manager         │
        └─────────┬───────┘ └─────────┬───────┘ └─────────┬───────┘
                  │                   │                   │
                  └───────────────────┼───────────────────┘
                                      │
                          ┌───────────┼───────────┐
                          ▼           ▼           ▼
                ┌─────────────┐ ┌──────────┐ ┌─────────────┐
                │ Database    │ │ Progress │ │ Config      │
                │ Layer       │ │ Manager  │ │ Manager     │
                └─────────────┘ └──────────┘ └─────────────┘
```

### Manager Pattern Implementation

Each major functionality area is handled by a dedicated manager class:

#### **BatchSubmissionManager** (`batch_submission_manager.py`)
- **Responsibility**: File processing and batch creation
- **Key Operations**: 
  - File collection and validation
  - Automatic batch partitioning (100 files max)
  - JSONL batch file creation
  - API submission with retry logic
  - Progress tracking integration

#### **BatchJobManager** (`batch_job_manager.py`)
- **Responsibility**: Job lifecycle management
- **Key Operations**:
  - Job status monitoring
  - Concurrent status refresh
  - Job cancellation
  - API response processing

#### **ResultManager** (`result_manager.py`)
- **Responsibility**: Result retrieval and organization
- **Key Operations**:
  - Result download with progress tracking
  - File organization by document
  - OCR result parsing (text/markdown)
  - Concurrent download operations

#### **DocumentManager** (`document_manager.py`)
- **Responsibility**: Document naming and UUID association
- **Key Operations**:
  - Document creation and lookup
  - UUID generation and validation
  - Name-to-UUID resolution

#### **ProgressManager** (`progress.py`)
- **Responsibility**: Real-time UI updates
- **Key Operations**:
  - Multi-phase progress tracking
  - Live job monitoring
  - Terminal UI with Rich library
  - Graceful degradation

## Data Flow Architecture

### File Submission Flow

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ User Input  │───▶│ File Collection │───▶│ Validation      │
│ (CLI args)  │    │ (FileCollector) │    │ (extensions)    │
└─────────────┘    └─────────────────┘    └─────────┬───────┘
                                                    │
┌─────────────┐    ┌─────────────────┐    ┌─────────▼───────┐
│ Job Storage │◀───│ API Submission  │◀───│ Batch Creation  │
│ (Database)  │    │ (Mistral API)   │    │ (JSONL format)  │
└─────────────┘    └─────────────────┘    └─────────────────┘
```

### Job Monitoring Flow

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Scheduled   │───▶│ Concurrent      │───▶│ Status Update   │
│ Refresh     │    │ API Calls       │    │ (Database)      │
└─────────────┘    └─────────────────┘    └─────────┬───────┘
                                                    │
┌─────────────┐    ┌─────────────────┐    ┌─────────▼───────┐
│ User        │◀───│ Progress        │◀───│ Change          │
│ Notification│    │ Display         │    │ Detection       │
└─────────────┘    └─────────────────┘    └─────────────────┘
```

### Result Retrieval Flow

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Completed   │───▶│ Download        │───▶│ File            │
│ Jobs Query  │    │ API Call        │    │ Organization    │
└─────────────┘    └─────────────────┘    └─────────┬───────┘
                                                    │
┌─────────────┐    ┌─────────────────┐    ┌─────────▼───────┐
│ User Files  │◀───│ Result Parsing  │◀───│ Storage         │
│ (.txt/.md)  │    │ (text/markdown) │    │ (XDG dirs)      │
└─────────────┘    └─────────────────┘    └─────────────────┘
```

## Design Patterns

### 1. **Facade Pattern**
- **Implementation**: `MistralOCRClient` class
- **Purpose**: Provides a simplified interface to the complex subsystem
- **Benefits**: Single entry point, hides complexity from CLI layer

### 2. **Manager Pattern**
- **Implementation**: All `*Manager` classes
- **Purpose**: Encapsulates related functionality and state
- **Benefits**: Clear separation of concerns, testable components

### 3. **Dependency Injection**
- **Implementation**: Constructor-based injection throughout
- **Purpose**: Loose coupling, easier testing and configuration
- **Example**:
```python
class BatchSubmissionManager:
    def __init__(
        self,
        database: Database,
        api_client: Optional["Mistral"],
        document_manager: DocumentManager,
        # ... other dependencies
    ) -> None:
```

### 4. **Strategy Pattern**
- **Implementation**: Progress tracking (enabled/disabled modes)
- **Purpose**: Runtime algorithm selection
- **Benefits**: Configurable behavior without code changes

### 5. **Decorator Pattern**
- **Implementation**: Validation decorators, retry decorators
- **Purpose**: Add functionality without modifying core logic
- **Examples**: `@validate_api_key`, `@with_retry`

### 6. **Context Manager Pattern**
- **Implementation**: Progress tracking, database connections
- **Purpose**: Resource management and cleanup
- **Example**:
```python
with tracker.track_submission(total_files, batch_count) as progress_ctx:
    # File processing with automatic progress updates
```

## Configuration Architecture

### Configuration Hierarchy

```
Environment Variables (highest priority)
    ↓
Configuration File (~/.config/mistral-ocr/config.json)
    ↓  
Application Defaults (lowest priority)
```

### Settings Management

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Settings        │───▶│ Configuration   │───▶│ XDG Paths       │
│ (facade)        │    │ Manager         │    │ (storage)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

- **Settings**: User-facing facade with validation
- **ConfigurationManager**: Low-level config file operations
- **XDGPaths**: Cross-platform directory management

## Storage Architecture

### Database Schema

The SQLite database provides local state persistence:

```sql
-- Job tracking
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    document_uuid TEXT NOT NULL,
    status TEXT NOT NULL,
    total_requests INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- ... additional fields
);

-- Document metadata
CREATE TABLE documents (
    uuid TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    downloaded BOOLEAN DEFAULT FALSE
);

-- Page associations  
CREATE TABLE pages (
    file_path TEXT,
    document_uuid TEXT,
    file_id TEXT,
    PRIMARY KEY (file_path, document_uuid)
);
```

### File Organization

Following XDG Base Directory Specification:

```
~/.config/mistral-ocr/          # Configuration
├── config.json                # User settings

~/.local/share/mistral-ocr/     # Data
├── mistral_ocr.db             # SQLite database
└── downloads/                 # Downloaded results
    ├── document-name/         # Organized by document
    │   ├── file1.txt
    │   └── file1.md
    └── unknown/               # Unassociated files

~/.cache/mistral-ocr/          # Cache (future use)

~/.local/state/mistral-ocr/    # Logs
└── mistral.log               # Application logs
```

## Error Handling Architecture

### Error Hierarchy

```
MistralOCRError (base)
├── DatabaseError
│   ├── DatabaseConnectionError
│   └── DatabaseOperationError
├── FileHandlingError
│   ├── UnsupportedFileTypeError
│   └── FileNotFoundError
├── APIError
│   ├── JobSubmissionError
│   ├── JobNotCompletedError
│   └── ResultNotAvailableError
└── ConfigurationError
    ├── InvalidConfigurationError
    └── MissingConfigurationError
```

### Retry Strategy

```python
@with_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
def _api_upload_file(self, file_path: pathlib.Path, purpose: str):
    # Automatic retry with exponential backoff
    # Transient errors (network, 5xx) are retried
    # Permanent errors (4xx, validation) are not retried
```

### Error Classification

- **Retryable Errors**: Network issues, server errors (5xx), timeouts
- **Non-Retryable Errors**: Authentication, validation, client errors (4xx)
- **Fatal Errors**: Configuration errors, file system issues

## Logging and Audit Architecture

The logging system provides comprehensive observability through structured logging, audit trails, and performance monitoring.

### Logging Component Hierarchy

```
                              ┌─────────────────┐
                              │   Core Logger   │
                              │ (structlog)     │
                              └─────────┬───────┘
                                        │
                      ┌─────────────────┼─────────────────┐
                      ▼                 ▼                 ▼
            ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
            │  AuditLogger    │ │ SecurityLogger  │ │PerformanceLogger│
            │                 │ │                 │ │                 │
            │ • Events        │ │ • Auth Events   │ │ • Timing        │
            │ • Operations    │ │ • Data Access   │ │ • Metrics       │
            │ • Context       │ │ • Config Change │ │ • Resource Use  │
            └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Audit Event Types

```python
class AuditEventType(Enum):
    # User Actions
    CLI_COMMAND = "cli_command"
    CONFIG_CHANGE = "config_change"
    
    # File Operations  
    FILE_SUBMISSION = "file_submission"
    FILE_DOWNLOAD = "file_download"
    FILE_ACCESS = "file_access"
    
    # API Operations
    API_REQUEST = "api_request"
    BATCH_SUBMISSION = "batch_submission"
    JOB_OPERATION = "job_operation"
    
    # System Events
    APPLICATION_START = "application_start"
    AUTHENTICATION = "authentication"
    ERROR_RECOVERY = "error_recovery"
```

### Log Processing Pipeline

```python
# Structured log processing with automatic enrichment
class AuditProcessor:
    def __call__(self, event_dict):
        # Add audit metadata
        if self.is_audit_event(event_dict):
            event_dict['audit_trail'] = True
            
        # Sanitize sensitive data  
        if 'api_key' in event_dict:
            event_dict['api_key_hash'] = hash_key(event_dict['api_key'])
            del event_dict['api_key']
            
        return event_dict
```

### Log File Strategy

- **Rotation**: 50MB max per file, 5 backup retention
- **Format**: JSON for structured analysis, colored console for development
- **Separation**: Specialized files for audit, security, performance
- **Location**: XDG-compliant state directory (`~/.local/state/mistral-ocr/`)

### Session Correlation

All operations within a CLI session share a session ID for traceability:

```python
class AuditLogger:
    def __init__(self, component: str):
        self.session_id = str(uuid.uuid4())[:8]
        
    def audit(self, event_type, message, **context):
        log_data = {
            'session_id': self.session_id,
            'component': component,
            'event_type': event_type.value,
            **context
        }
```

### Performance Monitoring

```python
@contextmanager
def operation_context(operation: str, resource_id: str = None):
    start_time = time.time()
    operation_id = str(uuid.uuid4())[:8]
    
    audit_logger.audit(
        AuditEventType.DATA_PROCESSING,
        f"Starting {operation}",
        operation_id=operation_id,
        resource_id=resource_id
    )
    
    try:
        yield {"operation_id": operation_id}
        
        duration = time.time() - start_time
        audit_logger.audit(
            AuditEventType.DATA_PROCESSING,
            f"Completed {operation}",
            operation_id=operation_id,
            outcome="success",
            duration_seconds=duration
        )
    except Exception as e:
        # Log failure with error context
        audit_logger.audit(
            AuditEventType.DATA_PROCESSING,
            f"Failed {operation}: {str(e)}",
            level="error",
            operation_id=operation_id,
            outcome="failure",
            error_type=type(e).__name__
        )
        raise
```

## Async and Concurrency Architecture

### Concurrent Processing

```python
class AsyncAPIManager:
    def __init__(self, max_concurrent_requests: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
    async def run_concurrent_operations(self, operations):
        # Rate-limited concurrent execution
        async with self.semaphore:
            # Execute operation
```

### Thread Safety

- **Database**: SQLite with WAL mode for concurrent reads
- **Configuration**: Thread-safe read/write operations
- **Progress**: Thread-safe UI updates with Rich

## Testing Architecture

### Test Organization

```
tests/
├── unit/           # Fast, isolated tests with mocks
├── integration/    # End-to-end workflow tests  
├── fixtures/       # Shared test data and mocks
└── conftest.py     # Test configuration
```

### Mock Strategy

- **API Calls**: Mocked by default with realistic responses
- **File System**: Temporary directories for isolation
- **Database**: In-memory SQLite for fast tests
- **Configuration**: Override with test values

## Performance Considerations

### Batch Processing

- **API Limits**: 100 files per batch (Mistral limitation)
- **Automatic Partitioning**: Large submissions split automatically
- **Concurrent Upload**: Multiple batch uploads in parallel

### Memory Management

- **Streaming**: Large files processed in chunks
- **Progress Tracking**: Minimal memory overhead
- **Database**: Connection pooling and query optimization

### Network Optimization

- **Retry Logic**: Exponential backoff prevents API hammering
- **Rate Limiting**: Semaphore-based concurrency control
- **Connection Reuse**: HTTP connection pooling

## Extension Points

### Adding New File Types

1. Update `constants.py` with new MIME types
2. Add validation in `FileCollector`
3. Update encoding logic in `FileEncodingUtils`

### Custom Progress Displays

1. Inherit from `ProgressManager`
2. Override display methods
3. Inject custom implementation in client

### Alternative Storage Backends

1. Implement `Database` interface
2. Add configuration options
3. Update dependency injection

This architecture provides a solid foundation for maintainable, testable, and extensible OCR processing while maintaining excellent user experience through comprehensive error handling and progress feedback.

---

## Developer Guide

### Module Reference

Understanding what each module does is crucial for effective development:

#### Core Modules

**`client.py`** - Main Facade
- Entry point for all OCR operations
- Coordinates between all manager classes
- Handles authentication and client initialization
- **Usage**: Primary interface for CLI commands

**`__main__.py`** - CLI Interface
- Argument parsing and command routing
- User input validation
- Error presentation to users
- **Usage**: CLI command definitions and help text

#### Manager Modules

**`batch_submission_manager.py`** - File Processing
- File collection and validation
- Batch creation (JSONL format) 
- API upload coordination
- **Key Classes**: `BatchSubmissionManager`, `FileCollector`
- **Usage**: When adding new file type support

**`batch_job_manager.py`** - Job Lifecycle
- Job status monitoring and updates
- Concurrent API operations
- Job cancellation logic
- **Key Classes**: `BatchJobManager`
- **Usage**: When modifying job status logic

**`result_manager.py`** - Result Handling
- Result download and parsing
- File organization by document
- **Key Classes**: `ResultManager`, `OCRResultParser`
- **Usage**: When changing result processing

**`document_manager.py`** - Document Organization
- Document naming and UUID management
- Document-to-job associations
- **Key Classes**: `DocumentManager`
- **Usage**: When modifying document organization

**`progress.py`** - UI Feedback
- Real-time progress tracking
- Rich terminal UI components
- **Key Classes**: `ProgressManager`
- **Usage**: When adding new progress indicators

#### Data and Configuration

**`data_types.py`** - Type Definitions
- Pydantic models for API responses
- Database record types
- Configuration structures
- **Key Classes**: `JobInfo`, `BatchResultEntry`, `ProcessedOCRResult`
- **Usage**: When adding new data structures

**`models.py`** - Legacy Models
- Original data models (being migrated to data_types.py)
- **Key Classes**: `OCRResult`
- **Usage**: Understanding legacy code

**`config.py`** - Configuration Management
- User settings and preferences
- Environment variable handling
- **Key Classes**: `ConfigurationManager`
- **Usage**: When adding new configuration options

**`settings.py`** - Settings Facade
- High-level settings interface
- Validation and defaults
- **Key Classes**: `Settings`
- **Usage**: When adding user-configurable options

#### Infrastructure

**`database.py`** - Data Persistence
- SQLite operations
- Job and document tracking
- **Key Classes**: `Database`
- **Usage**: When adding new database operations

**`db_models.py`** - SQLAlchemy Models
- Database table definitions
- Relationships and constraints
- **Key Classes**: `Job`, `Document`, `Page`, `Download`
- **Usage**: When modifying database schema

**`parsing.py`** - Response Processing
- API response parsing with Pydantic validation
- OCR result extraction
- **Key Classes**: `OCRResultParser`
- **Usage**: When handling new API response formats

**`validation.py`** - Input Validation
- Decorator-based validation
- Common validation patterns
- **Key Functions**: `@validate_api_key`, `@validate_file_path`
- **Usage**: When adding new validation rules

#### Utilities

**`utils/file_operations.py`** - File Handling
- File I/O operations
- Path manipulation
- **Key Classes**: `FileIOUtils`, `FileSystemUtils`
- **Usage**: When adding file operations

**`utils/retry_manager.py`** - Resilience
- Retry logic with exponential backoff
- Error classification
- **Key Functions**: `@with_retry`
- **Usage**: When adding API operations

**`async_utils.py`** - Concurrency
- Async/await helpers
- Concurrent operations
- **Key Classes**: `ConcurrentJobProcessor`
- **Usage**: When adding concurrent operations

**`audit.py`** - Observability
- Audit logging and trails
- Security event tracking
- **Key Classes**: `AuditLogger`, `SecurityLogger`
- **Usage**: When adding audit events

**`exceptions.py`** - Error Handling
- Custom exception hierarchy
- Error classification
- **Key Classes**: `MistralOCRError`, `JobError`, `APIError`
- **Usage**: When adding new error types

**`constants.py`** - Configuration Values
- Magic numbers and strings
- Default values
- **Usage**: When adding new constants

**`paths.py`** - Directory Management
- XDG Base Directory implementation
- Cross-platform path handling
- **Key Classes**: `XDGPaths`
- **Usage**: When adding new file locations

### Data Validation Architecture

The codebase uses **Pydantic** for robust data validation and type safety:

#### Pydantic Model Hierarchy

```python
# API Response Models (data_types.py)
@dataclass(config=ConfigDict(extra="forbid"))
class OCRPage:
    """Individual page result from API."""
    text: Optional[str] = None
    markdown: Optional[str] = None

@dataclass(config=ConfigDict(extra="forbid"))
class OCRResponseBody:
    """API response body structure."""
    pages: Optional[List[OCRPage]] = None
    text: Optional[str] = None
    content: Optional[str] = None
    markdown: Optional[str] = None
    choices: Optional[List[Dict[str, Any]]] = None

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

#### Validation Pipeline

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
        except Exception as e:
            self.logger.error(f"Error processing result: {e}")
```

#### Benefits of Pydantic Integration

1. **Type Safety**: Automatic validation of API responses
2. **Error Handling**: Clear validation error messages
3. **Documentation**: Self-documenting data structures
4. **IDE Support**: Better autocompletion and type checking

### Developer Workflow

#### Setting Up Development Environment

```bash
# 1. Clone and setup
git clone <repository>
cd mistral-ocr

# 2. Install with development dependencies
uv pip install -e .

# 3. Run tests to verify setup
pytest

# 4. Check code quality
ruff check
mypy src/
```

#### Development Process

1. **Understanding the Feature**
   - Read relevant sections in this document
   - Examine existing similar features
   - Check the module reference above

2. **Writing Tests First (TDD)**
   ```python
   # In tests/unit/test_new_feature.py
   def test_new_feature_basic_operation():
       """Test the core functionality."""
       client = MistralOCRClient(api_key="test")  # Mock mode
       result = client.new_feature_method()
       assert result.expected_property == "expected_value"
   ```

3. **Implementing the Feature**
   - Follow existing patterns (Manager classes, dependency injection)
   - Use type hints throughout
   - Add proper error handling
   - Include logging and audit events

4. **Code Quality Checks**
   ```bash
   # Run before committing
   ruff check --fix  # Auto-fix style issues
   mypy src/         # Type checking
   pytest           # All tests pass
   ```

#### Common Development Patterns

**Adding a New Manager Class**

```python
class NewFeatureManager:
    """Handles new feature operations."""
    
    def __init__(
        self,
        database: Database,
        api_client: Optional["Mistral"],
        logger: structlog.BoundLogger,
        mock_mode: bool = False,
    ) -> None:
        self.database = database
        self.client = api_client
        self.logger = logger
        self.mock_mode = mock_mode
    
    @with_retry(max_retries=3, base_delay=2.0)
    def _api_operation(self, param: str) -> Any:
        """API operation with retry logic."""
        if self.mock_mode:
            return self._mock_response()
        
        try:
            return self.client.new_operation(param)
        except Exception as e:
            if self._is_transient_error(e):
                raise RetryableError(f"Transient error: {e}")
            raise
    
    def public_method(self, param: str) -> ProcessedResult:
        """Main public interface method."""
        with self.logger.bind(operation="new_feature", param=param):
            self.logger.info("Starting new feature operation")
            
            try:
                raw_result = self._api_operation(param)
                processed = self._process_result(raw_result)
                
                self.logger.info("Completed new feature operation", 
                               result_count=len(processed))
                return processed
                
            except Exception as e:
                self.logger.error("Failed new feature operation", error=str(e))
                raise NewFeatureError(f"Operation failed: {e}")
```

**Adding a New CLI Command**

```python
# In __main__.py
def add_new_command_parser(subparsers):
    """Add new command to CLI."""
    parser = subparsers.add_parser(
        'new-command', 
        help='Description of new command'
    )
    parser.add_argument('--param', required=True, help='Parameter description')
    parser.set_defaults(func=handle_new_command)

def handle_new_command(args):
    """Handle the new command."""
    try:
        client = MistralOCRClient(api_key=args.api_key)
        result = client.new_feature_method(args.param)
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

**Adding New Data Models**

```python
# In data_types.py
@dataclass(config=ConfigDict(extra="forbid", validate_assignment=True))
class NewDataModel:
    """New data structure with validation."""
    
    id: str
    name: str
    created_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Custom validation after initialization."""
        if not self.id.startswith("prefix_"):
            raise ValueError("ID must start with 'prefix_'")
```

#### Testing Patterns

**Unit Test Structure**

```python
class TestNewFeature:
    """Test new feature functionality."""
    
    @pytest.fixture
    def manager(self, mock_database, mock_logger):
        """Create manager instance for testing."""
        return NewFeatureManager(
            database=mock_database,
            api_client=None,  # Mock mode
            logger=mock_logger,
            mock_mode=True
        )
    
    def test_success_case(self, manager):
        """Test successful operation."""
        result = manager.public_method("test_param")
        assert isinstance(result, ProcessedResult)
        assert result.param == "test_param"
    
    def test_error_handling(self, manager):
        """Test error conditions."""
        with pytest.raises(NewFeatureError):
            manager.public_method("invalid_param")
    
    @patch('mistral_ocr.new_feature_manager.external_dependency')
    def test_with_mocks(self, mock_dependency, manager):
        """Test with external dependencies mocked."""
        mock_dependency.return_value = "expected_value"
        result = manager.public_method("test_param")
        assert result.value == "expected_value"
```

**Integration Test Structure**

```python
class TestNewFeatureIntegration:
    """Test new feature end-to-end."""
    
    def test_full_workflow(self, test_client, tmp_path):
        """Test complete workflow."""
        # Setup test data
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # Execute operation
        result = test_client.new_feature_method(str(test_file))
        
        # Verify results
        assert result.success
        assert (tmp_path / "output").exists()
```

### Feature Development Guide

#### Adding New File Type Support

1. **Update Constants**
   ```python
   # In constants.py
   MIME_TYPE_NEW_FORMAT = "application/new-format"
   ```

2. **Update Validation**
   ```python
   # In file validation logic
   SUPPORTED_EXTENSIONS.add('.newext')
   MIME_TYPE_MAP['.newext'] = MIME_TYPE_NEW_FORMAT
   ```

3. **Add Processing Logic**
   ```python
   # In batch_submission_manager.py
   def _process_new_format(self, file_path: Path) -> Dict[str, Any]:
       """Process new file format."""
       # Implementation specific to new format
   ```

4. **Add Tests**
   ```python
   def test_new_format_processing(self, client, tmp_path):
       new_file = tmp_path / "test.newext"
       new_file.write_bytes(b"new format content")
       
       job_id = client.submit_documents([new_file])
       assert job_id is not None
   ```

#### Adding New Configuration Options

1. **Update Data Types**
   ```python
   # In data_types.py
   @dataclass(config=ConfigDict(extra="allow"))
   class ConfigData:
       # ... existing fields ...
       new_option: Optional[str] = None
   ```

2. **Add Settings Methods**
   ```python
   # In settings.py
   def get_new_option(self) -> str:
       """Get new configuration option."""
       return self.config_manager.get("new_option", "default_value")
   
   def set_new_option(self, value: str) -> None:
       """Set new configuration option."""
       self.config_manager.set("new_option", value)
   ```

3. **Add CLI Support**
   ```python
   # In __main__.py config commands
   elif args.config_action == "set" and args.key == "new-option":
       client.settings.set_new_option(args.value)
   ```

#### Adding New API Operations

1. **Create Manager Method**
   ```python
   # In appropriate manager class
   @with_retry(max_retries=3, base_delay=2.0)
   def _api_new_operation(self, param: str) -> Any:
       """New API operation with retry logic."""
       if self.mock_mode:
           return {"mock": "response"}
       
       try:
           return self.client.new_api_method(param)
       except Exception as e:
           if self._is_transient_error(e):
               raise RetryableError(f"API error: {e}")
           raise
   ```

2. **Add Data Models**
   ```python
   # In data_types.py
   @dataclass(config=ConfigDict(extra="forbid"))
   class NewAPIResponse:
       """Response from new API operation."""
       result: str
       status: int
       metadata: Optional[Dict[str, Any]] = None
   ```

3. **Add Error Handling**
   ```python
   # In exceptions.py
   class NewOperationError(APIError):
       """Error in new API operation."""
       pass
   ```

### Code Style and Conventions

#### Type Annotations
- Use `Optional[T]` instead of `T | None` (per CLAUDE.md)
- Always include return type annotations
- Use `TYPE_CHECKING` for circular imports

#### Error Handling
- Create specific exception types for different error conditions
- Use `@with_retry` for transient errors
- Log errors with structured context

#### Logging
- Use structured logging with `structlog`
- Include operation context in log messages
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)

#### Testing
- Write tests before implementation (TDD)
- Use descriptive test names that explain the scenario
- Test both success and failure cases
- Use fixtures for common test setup

This guide provides the foundation for understanding and extending the Mistral OCR codebase effectively.