# Python CLI Application Template Guide

This guide provides a comprehensive template for building robust Python CLI applications. Use this as a blueprint for creating enterprise-grade command-line tools with configuration management, logging, database access, and comprehensive testing.

## Project Structure Template

```
your-app/
├── pyproject.toml             # Modern Python project configuration
├── requirements.txt           # Dependency fallback
├── uv.lock                    # Locked dependencies
├── README.md                  # Project documentation
├── CLAUDE.md                  # AI assistant instructions
├── src/
│   └── your_app/
│       ├── __init__.py        # Clean public API exports
│       ├── __main__.py        # CLI entry point
│       ├── audit.py           # Audit trail system
│       ├── client.py          # Main orchestration client
│       ├── config.py          # Configuration management
│       ├── constants.py       # Application constants
│       ├── data_types.py      # Pydantic dataclasses
│       ├── database.py        # Database operations
│       ├── db_models.py       # SQLAlchemy ORM models
│       ├── exceptions.py      # Custom exception hierarchy
│       ├── logging.py         # Structured logging setup
│       ├── paths.py           # XDG path management
│       ├── progress.py        # Progress tracking (Rich UI)
│       ├── settings.py        # Unified settings facade
│       ├── validation.py      # Input validation decorators
│       └── utils/
│           ├── __init__.py
│           ├── retry_manager.py    # Retry logic with backoff
│           └── file_operations.py  # File utilities
├── tests/
│   ├── conftest.py            # Shared test configuration
│   ├── factories.py           # Test data factories
│   ├── shared_fixtures.py     # Common test fixtures
│   ├── unit/                  # Unit tests
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_client.py
│   │   └── test_*.py
│   └── integration/           # Integration tests
│       ├── __init__.py
│       └── test_*.py
└── scripts/                   # Utility scripts
    └── setup-dev
```

## Core Configuration Files

### pyproject.toml Template

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "your-app"
version = "0.1.0"
description = "Description of your CLI application"
authors = [
    {name = "Your Name", email = "your.email@example.com"},
]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.12"
keywords = ["cli", "tool"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "pydantic>=2.0.0",
    "sqlalchemy>=2.0.0",
    "rich>=13.0.0",
    "click>=8.0.0",  # or argparse for simpler cases
    "structlog>=23.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
    "coverage>=7.0.0",
]

[project.scripts]
your-app = "your_app.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.mypy]
python_version = "3.12"
disallow_untyped_defs = true
disallow_incomplete_defs = true
disallow_untyped_calls = true
warn_return_any = true
warn_unused_ignores = true
show_error_codes = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--strict-markers --strict-config"
markers = [
    "unit: Unit tests with mocked dependencies",
    "integration: Integration tests that may use real services",
    "slow: Slow tests that should be run less frequently",
]
```

### CLAUDE.md Template

```markdown
# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Commands

### Package Management
- Use `uv` for all package management instead of pip
- Add dependencies: `uv add <package>`
- Install in development mode: `uv pip install -e .`
- Run the CLI: `uv run python -m your_app`

### Development
- Activate virtual environment: `source .venv/bin/activate`
- Run tests: `pytest`
- Lint and format: `ruff check` and `ruff format`
- Type checking: `mypy src/`

### CLI Commands

#### [Define your application's CLI commands here]

### Logging and Monitoring
- Log files location: `~/.local/state/your-app/`
  - `app.log` - Main application log
  - `audit.log` - Audit trail events
  - `security.log` - Authentication and security events
  - `performance.log` - Performance metrics
- Monitor real-time: `tail -f ~/.local/state/your-app/app.log`

## Architecture

[Describe your application's purpose and architecture]

## Development Rules

- Use type hints throughout
- Line length limit: 100 characters
- Python 3.12+ required
- When creating method signatures, use `Optional` rather than union syntax (`| None`)

## Code Style
- When creating method signatures, use `Optional` rather than union syntax (`| None`)
```

## Core Implementation Templates

### 1. Main Client Class (client.py)

```python
"""Main client orchestrating all application operations."""

from typing import Optional
from contextlib import contextmanager

from .config import ConfigurationManager
from .settings import Settings
from .database import DatabaseManager
from .logging import get_logger
from .audit import AuditLogger, AuditEventType
from .progress import ProgressManager
from .exceptions import YourAppError
from .data_types import YourDataClass


class YourAppClient:
    """Main client class orchestrating all application operations."""
    
    def __init__(self, api_key: Optional[str] = None, enable_progress: bool = False):
        """Initialize the client with configuration and dependencies."""
        self.settings = Settings()
        self.database = DatabaseManager()
        self.audit_logger = AuditLogger(component="client")
        self.progress_manager = ProgressManager(enabled=enable_progress)
        
        # Set API key if provided
        if api_key:
            self.settings.set_api_key(api_key)
        
        # Connect to database
        self.database.connect()
        self.database.initialize_schema()
        
        logger = get_logger(__name__)
        logger.info("YourAppClient initialized successfully", api_key_configured=bool(api_key))
    
    @contextmanager
    def operation_context(self, operation: str):
        """Context manager for tracking operations with audit logging."""
        with self.audit_logger.operation_context(operation, AuditEventType.OPERATION_START):
            try:
                yield
            except Exception as e:
                logger = get_logger(__name__)
                logger.error("Operation failed", operation=operation, error=str(e))
                raise
    
    def your_main_operation(self, data: YourDataClass) -> str:
        """Example main operation with full error handling and audit trail."""
        with self.operation_context("your_main_operation"):
            try:
                # Your business logic here
                result = self._process_data(data)
                
                self.audit_logger.audit(
                    AuditEventType.OPERATION_SUCCESS,
                    f"Successfully processed data: {data.id}",
                    data_id=data.id,
                    result_id=result
                )
                
                return result
                
            except Exception as e:
                self.audit_logger.audit(
                    AuditEventType.OPERATION_FAILURE,
                    f"Failed to process data: {data.id}",
                    error=str(e),
                    data_id=data.id,
                    outcome="failure"
                )
                raise YourAppError(f"Operation failed: {e}") from e
    
    def _process_data(self, data: YourDataClass) -> str:
        """Internal data processing logic."""
        # Implement your core business logic
        return f"processed-{data.id}"
```

### 2. Configuration Management (config.py)

```python
"""Configuration management with validation and multi-source support."""

import os
import json
from pathlib import Path
from typing import Any, Optional, Dict
from functools import wraps

from .paths import XDGPaths
from .exceptions import ConfigurationError
from .validation import validate_required_string
from .logging import get_logger


def validate_api_key(func):
    """Decorator to validate API key format."""
    @wraps(func)
    def wrapper(self, api_key: str, *args, **kwargs):
        if not api_key or not isinstance(api_key, str):
            raise ConfigurationError("API key must be a non-empty string")
        if len(api_key) < 10:  # Adjust based on your requirements
            raise ConfigurationError("API key appears to be too short")
        return func(self, api_key, *args, **kwargs)
    return wrapper


class ConfigurationManager:
    """Manages application configuration with file and environment support."""
    
    def __init__(self):
        self.config_path = XDGPaths.get_config_dir() / "config.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_data: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self._config_data = json.load(f)
                logger = get_logger(__name__)
                logger.debug("Loaded configuration from file", config_path=str(self.config_path))
            except (json.JSONDecodeError, OSError) as e:
                logger = get_logger(__name__)
                logger.warning("Failed to load config file", error=str(e), config_path=str(self.config_path))
                self._config_data = {}
        else:
            self._config_data = {}
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self._config_data, f, indent=2)
            logger = get_logger(__name__)
            logger.debug("Saved configuration to file", config_path=str(self.config_path))
        except OSError as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with environment variable precedence."""
        # Check environment variable first
        env_key = f"YOUR_APP_{key.upper()}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value
        
        # Fall back to config file
        return self._config_data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save to file."""
        self._config_data[key] = value
        self._save_config()
    
    @validate_api_key
    def set_api_key(self, api_key: str) -> None:
        """Set API key with validation."""
        self.set("api_key", api_key)
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config_data = {}
        self._save_config()
        logger = get_logger(__name__)
        logger.info("Configuration reset to defaults")
    
    def show_config(self) -> Dict[str, Any]:
        """Show current configuration (excluding sensitive values)."""
        config_copy = self._config_data.copy()
        # Mask sensitive values
        if "api_key" in config_copy:
            config_copy["api_key"] = "*" * 8 + config_copy["api_key"][-4:]
        return config_copy
```

### 3. Settings Facade (settings.py)

```python
"""Unified settings interface combining configuration and paths."""

import os
from typing import Optional
from pathlib import Path

from .config import ConfigurationManager
from .paths import XDGPaths
from .exceptions import ConfigurationError

# Environment variable names
API_KEY_ENV_VAR = "YOUR_APP_API_KEY"
MODEL_ENV_VAR = "YOUR_APP_MODEL"


class Settings:
    """Unified settings interface for the application."""
    
    def __init__(self):
        self._config = ConfigurationManager()
        self._paths = XDGPaths()
    
    def get_api_key(self) -> str:
        """Get API key with environment precedence."""
        api_key = os.environ.get(API_KEY_ENV_VAR)
        if api_key:
            return api_key
        
        api_key = self._config.get("api_key")
        if not api_key:
            raise ConfigurationError(
                f"API key not found. Set {API_KEY_ENV_VAR} environment variable "
                "or use 'your-app config set api-key <key>'"
            )
        return api_key
    
    def set_api_key(self, api_key: str) -> None:
        """Set API key."""
        self._config.set_api_key(api_key)
    
    def get_model(self) -> str:
        """Get model with fallback to default."""
        return (
            os.environ.get(MODEL_ENV_VAR) or 
            self._config.get("model", "default-model")
        )
    
    def set_model(self, model: str) -> None:
        """Set model."""
        self._config.set("model", model)
    
    def get_download_dir(self) -> Path:
        """Get download directory."""
        download_dir = self._config.get("download_dir")
        if download_dir:
            return Path(download_dir)
        return self._paths.get_data_dir() / "downloads"
    
    def set_download_dir(self, path: str) -> None:
        """Set download directory."""
        self._config.set("download_dir", path)
    
    # Add more settings as needed for your application
    
    def reset(self) -> None:
        """Reset all settings."""
        self._config.reset()
    
    def show_all(self) -> dict:
        """Show all current settings."""
        return {
            "api_key": "*" * 8 + self.get_api_key()[-4:] if self.get_api_key() else None,
            "model": self.get_model(),
            "download_dir": str(self.get_download_dir()),
            **self._config.show_config()
        }
```

### 4. Database Management (database.py)

```python
"""Database management with SQLAlchemy ORM."""

from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager
from functools import wraps

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .db_models import Base, YourModel
from .paths import XDGPaths
from .exceptions import DatabaseError
from .logging import get_logger


def require_database_connection(func):
    """Decorator to ensure database connection before operations."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.session:
            raise DatabaseError("Database not connected. Call connect() first.")
        return func(self, *args, **kwargs)
    return wrapper


class DatabaseManager:
    """Manages SQLAlchemy database operations."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (XDGPaths.get_data_dir() / "app.db")
        self.engine = None
        self.session_factory = None
        self.session: Optional[Session] = None
    
    def connect(self) -> None:
        """Connect to the database."""
        try:
            # Ensure data directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create engine and session factory
            self.engine = create_engine(f"sqlite:///{self.db_path}")
            self.session_factory = sessionmaker(bind=self.engine)
            self.session = self.session_factory()
            
            logger = get_logger(__name__)
            logger.info("Connected to database", db_path=str(self.db_path))
            
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to connect to database: {e}")
    
    def initialize_schema(self) -> None:
        """Initialize database schema."""
        if not self.engine:
            raise DatabaseError("Database not connected")
        
        try:
            Base.metadata.create_all(self.engine)
            self._migrate_schema()
            logger = get_logger(__name__)
            logger.info("Database schema initialized")
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to initialize schema: {e}")
    
    def _migrate_schema(self) -> None:
        """Handle schema migrations."""
        # Add any necessary schema migrations here
        # Example:
        # new_columns = [
        #     ("new_field", "TEXT"),
        # ]
        # 
        # for column_name, column_type in new_columns:
        #     try:
        #         self.session.execute(text(f"SELECT {column_name} FROM your_table LIMIT 1"))
        #     except Exception:
        #         self.session.execute(text(f"ALTER TABLE your_table ADD COLUMN {column_name} {column_type}"))
        #         self.session.commit()
        pass
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        if not self.session:
            raise DatabaseError("Database not connected")
        
        try:
            yield self.session
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
    
    @require_database_connection
    def create_item(self, **kwargs) -> YourModel:
        """Create a new item in the database."""
        try:
            with self.transaction() as session:
                item = YourModel(**kwargs)
                session.add(item)
                session.flush()  # To get the ID
                return item
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to create item: {e}")
    
    @require_database_connection
    def get_item_by_id(self, item_id: str) -> Optional[YourModel]:
        """Get item by ID."""
        try:
            return self.session.query(YourModel).filter(YourModel.id == item_id).first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get item: {e}")
    
    @require_database_connection
    def get_all_items(self) -> List[YourModel]:
        """Get all items."""
        try:
            return self.session.query(YourModel).all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get items: {e}")
    
    def close(self) -> None:
        """Close database connection."""
        if self.session:
            self.session.close()
            self.session = None
        logger = get_logger(__name__)
        logger.info("Database connection closed")
```

### 5. Database Models (db_models.py)

```python
"""SQLAlchemy ORM models."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, func, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class YourModel(Base):
    """Example model for your application."""
    
    __tablename__ = "your_table"
    
    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True)
    
    # Basic fields
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=func.current_timestamp()
    )
    
    # Relationships (example)
    # related_items: Mapped[List["RelatedModel"]] = relationship(
    #     "RelatedModel", back_populates="parent"
    # )
    
    def __repr__(self) -> str:
        return f"<YourModel(id='{self.id}', name='{self.name}', status='{self.status}')>"


# Add more models as needed for your application
```

### 6. Exception Hierarchy (exceptions.py)

```python
"""Custom exception hierarchy for the application."""

from typing import Optional


class YourAppError(Exception):
    """Base exception for all application errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}. Details: {self.details}"
        return self.message


class ConfigurationError(YourAppError):
    """Configuration-related errors."""
    pass


class DatabaseError(YourAppError):
    """Database operation errors."""
    pass


class ValidationError(YourAppError):
    """Input validation errors."""
    pass


class APIError(YourAppError):
    """External API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class RetryableError(YourAppError):
    """Errors that should trigger retry logic."""
    
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class NonRetryableError(YourAppError):
    """Errors that should not be retried."""
    pass
```

### 7. Logging Setup (logging.py)

```python
"""Structured logging configuration with structlog and JSON output."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

import structlog
from structlog.stdlib import LoggerFactory

from .paths import XDGPaths


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = False
) -> None:
    """Set up structured logging with JSON output to files."""
    
    # Create logs directory
    log_dir = XDGPaths.get_state_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper()),
        handlers=[]
    )
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add file handler with JSON formatting
    if log_to_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(file_handler)
        
        # Use JSON formatter for file output
        processors.append(structlog.processors.JSONRenderer())
    
    # Add console handler with human-readable formatting if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(console_handler)
        
        # Use colored output for console if available
        if log_to_console and not log_to_file:
            processors.append(structlog.dev.ConsoleRenderer())
        elif log_to_console:
            # If both file and console, use JSON for consistency
            processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set specific logger levels to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Log configuration success
    logger = structlog.get_logger(__name__)
    logger.info(
        "Logging configured successfully",
        log_level=level,
        file_logging=log_to_file,
        console_logging=log_to_console,
        log_directory=str(log_dir)
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
```

### 8. Audit Logging (audit.py)

```python
"""Comprehensive audit logging system using structlog."""

import uuid
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from contextlib import contextmanager

import structlog

from .paths import XDGPaths


class AuditEventType(Enum):
    """Types of audit events."""
    APPLICATION_START = "application_start"
    APPLICATION_END = "application_end"
    OPERATION_START = "operation_start"
    OPERATION_SUCCESS = "operation_success"
    OPERATION_FAILURE = "operation_failure"
    AUTHENTICATION = "authentication"
    CONFIGURATION_CHANGE = "configuration_change"
    DATABASE_OPERATION = "database_operation"


class AuditLogger:
    """Structured audit logging for security and compliance using structlog."""
    
    def __init__(self, component: str = "unknown"):
        self.component = component
        self._session_id = str(uuid.uuid4())[:8]
        self._setup_loggers()
    
    def _setup_loggers(self) -> None:
        """Set up specialized structured loggers."""
        # Get specialized loggers for different log types
        self.audit_logger = structlog.get_logger("audit")
        self.security_logger = structlog.get_logger("security")
        self.performance_logger = structlog.get_logger("performance")
    
    def audit(
        self,
        event_type: AuditEventType,
        message: str,
        *,
        level: str = "info",
        outcome: str = "success",
        **kwargs
    ) -> None:
        """Log an audit event with structured data."""
        logger_method = getattr(self.audit_logger, level, self.audit_logger.info)
        
        logger_method(
            message,
            event_type=event_type.value,
            component=self.component,
            session_id=self._session_id,
            outcome=outcome,
            **kwargs
        )
    
    def security_event(self, event: str, **kwargs) -> None:
        """Log a security event with structured data."""
        self.security_logger.info(
            f"Security event: {event}",
            event=event,
            component=self.component,
            session_id=self._session_id,
            **kwargs
        )
    
    def performance_metric(self, operation: str, duration: float, **kwargs) -> None:
        """Log a performance metric with structured data."""
        self.performance_logger.info(
            f"Performance metric for {operation}",
            operation=operation,
            duration_seconds=duration,
            component=self.component,
            session_id=self._session_id,
            **kwargs
        )
    
    @contextmanager
    def operation_context(self, operation: str, event_type: AuditEventType):
        """Context manager for tracking operations with timing."""
        start_time = time.time()
        operation_id = str(uuid.uuid4())[:8]
        
        self.audit(
            event_type,
            f"Started {operation}",
            operation=operation,
            operation_id=operation_id
        )
        
        try:
            yield {"operation_id": operation_id}
            
            duration = time.time() - start_time
            self.audit(
                AuditEventType.OPERATION_SUCCESS,
                f"Completed {operation}",
                operation=operation,
                operation_id=operation_id,
                duration_seconds=duration
            )
            self.performance_metric(operation, duration, operation_id=operation_id)
            
        except Exception as e:
            duration = time.time() - start_time
            self.audit(
                AuditEventType.OPERATION_FAILURE,
                f"Failed {operation}: {e}",
                operation=operation,
                operation_id=operation_id,
                error=str(e),
                duration_seconds=duration,
                outcome="failure",
                level="error"
            )
            raise
```

### 9. Progress Tracking (progress.py)

```python
"""Progress tracking and UI components using Rich."""

import time
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass

from rich.console import Console
from rich.progress import (
    Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, 
    TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
)
from rich.live import Live
from rich.table import Table
from rich.text import Text


class DummyProgress:
    """No-op progress tracker for when progress display is disabled."""
    
    def add_task(self, description: str, total: Optional[int] = None) -> str:
        return "dummy-task"
    
    def update(self, task_id: str, advance: int = 1, **kwargs) -> None:
        pass
    
    def remove_task(self, task_id: str) -> None:
        pass


@dataclass
class ProgressContext:
    """Context for progress tracking operations."""
    progress: Progress
    main_task: TaskID
    total_items: int
    completed_items: int = 0
    
    def update(self, advance: int = 1, **kwargs) -> None:
        """Update progress with optional additional information."""
        self.completed_items += advance
        self.progress.update(self.main_task, advance=advance, **kwargs)
    
    def complete(self) -> None:
        """Mark progress as complete."""
        remaining = self.total_items - self.completed_items
        if remaining > 0:
            self.progress.update(self.main_task, advance=remaining)


class ProgressManager:
    """Manages progress tracking and UI components."""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.console = Console(file=None) if enabled else None
    
    @contextmanager
    def create_progress(self, show_speed: bool = False, show_time: bool = True):
        """Create a progress tracker with specified features."""
        if not self.enabled:
            yield DummyProgress()
            return
        
        columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ]
        
        if show_time:
            columns.extend([TimeElapsedColumn(), TimeRemainingColumn()])
        
        progress = Progress(*columns, console=self.console)
        
        with progress:
            yield progress
    
    @contextmanager
    def track_operation(self, description: str, total: Optional[int] = None):
        """Track a single operation with context."""
        with self.create_progress() as progress:
            if isinstance(progress, DummyProgress):
                yield DummyProgress()
                return
            
            task_id = progress.add_task(description, total=total)
            context = ProgressContext(progress, task_id, total or 0)
            
            try:
                yield context
            finally:
                if total and context.completed_items < total:
                    context.complete()


class LiveStatusMonitor:
    """Live status monitoring for long-running operations."""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.console = Console() if enabled else None
    
    @contextmanager
    def monitor_status(self, title: str = "Status Monitor"):
        """Create a live status monitor."""
        if not self.enabled:
            yield DummyStatusMonitor()
            return
        
        monitor = StatusMonitor(title, self.console)
        with Live(monitor.create_table(), refresh_per_second=2, console=self.console) as live:
            monitor.live = live
            yield monitor


class DummyStatusMonitor:
    """No-op status monitor."""
    
    def update_status(self, key: str, value: str, status: str = "running") -> None:
        pass
    
    def set_completed(self, key: str) -> None:
        pass
    
    def set_failed(self, key: str, error: str) -> None:
        pass


class StatusMonitor:
    """Live status monitoring implementation."""
    
    def __init__(self, title: str, console: Console):
        self.title = title
        self.console = console
        self.live: Optional[Live] = None
        self.statuses: Dict[str, Dict[str, Any]] = {}
    
    def create_table(self) -> Table:
        """Create the status table."""
        table = Table(title=self.title)
        table.add_column("Item", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="white")
        
        for key, status_info in self.statuses.items():
            status_text = Text(status_info["status"])
            
            if status_info["status"] == "completed":
                status_text.style = "green"
            elif status_info["status"] == "failed":
                status_text.style = "red"
            elif status_info["status"] == "running":
                status_text.style = "yellow"
            
            table.add_row(
                key,
                status_text,
                status_info.get("details", "")
            )
        
        return table
    
    def update_status(self, key: str, value: str, status: str = "running") -> None:
        """Update status for a specific item."""
        self.statuses[key] = {
            "status": status,
            "details": value,
            "updated_at": time.time()
        }
        
        if self.live:
            self.live.update(self.create_table())
    
    def set_completed(self, key: str) -> None:
        """Mark an item as completed."""
        if key in self.statuses:
            self.statuses[key]["status"] = "completed"
            if self.live:
                self.live.update(self.create_table())
    
    def set_failed(self, key: str, error: str) -> None:
        """Mark an item as failed."""
        if key in self.statuses:
            self.statuses[key]["status"] = "failed"
            self.statuses[key]["details"] = error
            if self.live:
                self.live.update(self.create_table())
```

### 10. CLI Entry Point (__main__.py)

```python
"""CLI entry point with comprehensive command handling."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .client import YourAppClient
from .settings import Settings
from .audit import AuditLogger, AuditEventType
from .exceptions import YourAppError, ConfigurationError
from .logging import setup_logging, get_logger


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog="your-app",
        description="Your CLI application description"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"your-app {__version__}"
    )
    
    parser.add_argument(
        "--api-key",
        help="API key (can also use YOUR_APP_API_KEY environment variable)"
    )
    
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Enable progress display"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--console-logging",
        action="store_true",
        help="Enable console logging in addition to file logging"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Config commands
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_parser.add_subparsers(dest="config_action")
    
    config_subparsers.add_parser("show", help="Show current configuration")
    config_subparsers.add_parser("reset", help="Reset configuration to defaults")
    
    set_parser = config_subparsers.add_parser("set", help="Set configuration value")
    set_parser.add_argument("key", help="Configuration key")
    set_parser.add_argument("value", help="Configuration value")
    
    # Main operation commands
    operation_parser = subparsers.add_parser("process", help="Process data")
    operation_parser.add_argument("input", help="Input to process")
    operation_parser.add_argument("--name", help="Optional name for the operation")
    
    # List commands
    list_parser = subparsers.add_parser("list", help="List items")
    list_parser.add_argument("--filter", help="Filter items")
    
    return parser


def handle_config_command(args: argparse.Namespace) -> None:
    """Handle configuration commands."""
    settings = Settings()
    
    if args.config_action == "show":
        config = settings.show_all()
        print("Current configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
    
    elif args.config_action == "set":
        if args.key == "api-key":
            settings.set_api_key(args.value)
        elif args.key == "model":
            settings.set_model(args.value)
        elif args.key == "download-dir":
            settings.set_download_dir(args.value)
        else:
            raise ConfigurationError(f"Unknown configuration key: {args.key}")
        
        print(f"Set {args.key} = {args.value}")
    
    elif args.config_action == "reset":
        settings.reset()
        print("Configuration reset to defaults")


def handle_process_command(args: argparse.Namespace, client: YourAppClient) -> None:
    """Handle data processing commands."""
    from .data_types import YourDataClass
    
    # Create data object from input
    data = YourDataClass(
        id=args.input,
        name=args.name or f"Process {args.input}"
    )
    
    try:
        result = client.your_main_operation(data)
        print(f"Processing complete. Result: {result}")
    except YourAppError as e:
        print(f"Processing failed: {e}")
        sys.exit(1)


def handle_list_command(args: argparse.Namespace, client: YourAppClient) -> None:
    """Handle list commands."""
    try:
        items = client.database.get_all_items()
        
        if args.filter:
            # Apply filter logic here
            items = [item for item in items if args.filter.lower() in item.name.lower()]
        
        if items:
            print(f"Found {len(items)} items:")
            for item in items:
                print(f"  {item.id}: {item.name} ({item.status})")
        else:
            print("No items found")
    except YourAppError as e:
        print(f"Failed to list items: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set up logging with specified level and console option
    setup_logging(
        level=args.log_level,
        log_to_file=True,  # Always log to file
        log_to_console=args.console_logging
    )
    
    # Set up audit logging
    audit_logger = AuditLogger(component="cli")
    
    try:
        # Log application start
        audit_logger.audit(
            AuditEventType.APPLICATION_START,
            "Started your-app CLI",
            command=args.command,
            version=__version__,
            args=vars(args)
        )
        
        # Handle commands that don't require client
        if args.command == "config":
            handle_config_command(args)
            return
        
        # Commands that require client
        if not args.command:
            parser.print_help()
            return
        
        # Initialize client
        client = YourAppClient(
            api_key=args.api_key,
            enable_progress=args.progress
        )
        
        # Route to command handlers
        if args.command == "process":
            handle_process_command(args, client)
        elif args.command == "list":
            handle_list_command(args, client)
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
            sys.exit(1)
    
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    
    except YourAppError as e:
        print(f"Application error: {e}")
        audit_logger.audit(
            AuditEventType.APPLICATION_END,
            f"Application failed: {e}",
            outcome="failure",
            level="error"
        )
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        audit_logger.audit(
            AuditEventType.APPLICATION_END,
            "Application interrupted by user",
            outcome="cancelled"
        )
        sys.exit(130)
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        audit_logger.audit(
            AuditEventType.APPLICATION_END,
            f"Application failed with unexpected error: {e}",
            outcome="failure",
            level="error"
        )
        logger = get_logger(__name__)
        logger.exception("Unexpected error in main", error=str(e))
        sys.exit(1)
    
    else:
        audit_logger.audit(
            AuditEventType.APPLICATION_END,
            "Application completed successfully"
        )


if __name__ == "__main__":
    main()
```

## Testing Templates

### conftest.py

```python
"""Shared test configuration and fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from your_app.client import YourAppClient
from your_app.database import DatabaseManager
from your_app.config import ConfigurationManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, temp_dir):
    """Set up isolated test environment."""
    monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(temp_dir / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_dir / "config"))
    monkeypatch.setenv("YOUR_APP_API_KEY", "test-api-key")


@pytest.fixture
def mock_api_client():
    """Mock external API client."""
    with patch("your_app.client.YourExternalAPIClient") as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def test_database(temp_dir):
    """Create test database."""
    db = DatabaseManager(db_path=temp_dir / "test.db")
    db.connect()
    db.initialize_schema()
    yield db
    db.close()


@pytest.fixture
def test_client(temp_dir, mock_api_client, test_database):
    """Create test client with mocked dependencies."""
    client = YourAppClient(api_key="test-api-key")
    client.database = test_database
    return client


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    from your_app.data_types import YourDataClass
    return YourDataClass(
        id="test-123",
        name="Test Data",
        description="Sample data for testing"
    )
```

## Usage Instructions

1. **Initialize Your Project**:
   ```bash
   mkdir your-new-app
   cd your-new-app
   uv init
   ```

2. **Copy and Adapt Templates**:
   - Copy the directory structure
   - Replace `your_app` with your actual package name
   - Replace `YourApp*` classes with your domain-specific names
   - Update the CLI commands to match your application's functionality

3. **Configure Development Environment**:
   ```bash
   # Install dependencies
   uv add pydantic sqlalchemy rich click structlog

   # Install development dependencies  
   uv add --dev pytest pytest-asyncio mypy ruff coverage

   # Install in development mode
   uv pip install -e .
   ```

4. **Customize for Your Domain**:
   - Update `db_models.py` with your data models
   - Modify `data_types.py` with your Pydantic dataclasses
   - Implement your business logic in `client.py`
   - Update CLI commands in `__main__.py`
   - Add domain-specific configuration in `config.py`

5. **Set Up Testing**:
   ```bash
   # Run tests
   pytest

   # Type checking
   mypy src/

   # Linting
   ruff check src/
   ```

This template provides a solid foundation for building enterprise-grade CLI applications with comprehensive logging, configuration management, database operations, and testing infrastructure.
