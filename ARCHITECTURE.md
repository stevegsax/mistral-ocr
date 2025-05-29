# Architecture Documentation

> Deep dive into the mistral-ocr system architecture, design patterns, and component relationships

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