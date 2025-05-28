"""Input validation decorators for common patterns."""

import functools
import pathlib
from typing import Any, Callable, TypeVar

from .constants import MIN_API_KEY_LENGTH, MAX_API_TIMEOUT_SECONDS, MAX_RETRIES_LIMIT
from .exceptions import (
    InvalidConfigurationError, 
    InvalidJobIdError, 
    DatabaseConnectionError,
    UnsupportedFileTypeError
)

F = TypeVar('F', bound=Callable[..., Any])


def validate_api_key(func: F) -> F:
    """Decorator to validate API key parameters.
    
    Validates that the first argument after self is a valid API key:
    - Must be a non-empty string
    - Must meet minimum length requirements
    
    Raises:
        InvalidConfigurationError: If API key is invalid
    """
    @functools.wraps(func)
    def wrapper(self, api_key: str, *args, **kwargs):
        if not api_key or not isinstance(api_key, str):
            raise InvalidConfigurationError("API key must be a non-empty string")
        
        if len(api_key.strip()) < MIN_API_KEY_LENGTH:
            raise InvalidConfigurationError("API key appears to be too short")
        
        return func(self, api_key, *args, **kwargs)
    return wrapper


def validate_job_id(func: F) -> F:
    """Decorator to validate job ID format.
    
    Validates that the first argument after self is a valid job ID:
    - Cannot contain 'invalid' (case-insensitive)
    
    Raises:
        InvalidJobIdError: If job ID is invalid
    """
    @functools.wraps(func)
    def wrapper(self, job_id: str, *args, **kwargs):
        if "invalid" in job_id.lower():
            raise InvalidJobIdError(f"Invalid job ID: {job_id}")
        
        return func(self, job_id, *args, **kwargs)
    return wrapper


def validate_model_name(func: F) -> F:
    """Decorator to validate model name parameters.
    
    Validates that the first argument after self is a valid model name:
    - Must be a non-empty string
    - Must not be whitespace only
    
    Raises:
        InvalidConfigurationError: If model name is invalid
    """
    @functools.wraps(func)
    def wrapper(self, model: str, *args, **kwargs):
        if not model or not isinstance(model, str):
            raise InvalidConfigurationError("Model name must be a non-empty string")
        
        if not model.strip():
            raise InvalidConfigurationError("Model name cannot be empty")
        
        return func(self, model, *args, **kwargs)
    return wrapper


def validate_timeout_range(func: F) -> F:
    """Decorator to validate timeout value ranges.
    
    Validates that the first argument after self is a valid timeout:
    - Must be an integer
    - Must be between 1 and MAX_API_TIMEOUT_SECONDS
    
    Raises:
        InvalidConfigurationError: If timeout is invalid
    """
    @functools.wraps(func)
    def wrapper(self, timeout: int, *args, **kwargs):
        if not isinstance(timeout, int) or timeout < 1 or timeout > MAX_API_TIMEOUT_SECONDS:
            raise InvalidConfigurationError(
                f"Timeout must be an integer between 1 and {MAX_API_TIMEOUT_SECONDS} seconds"
            )
        
        return func(self, timeout, *args, **kwargs)
    return wrapper


def validate_retry_count(func: F) -> F:
    """Decorator to validate retry count ranges.
    
    Validates that the first argument after self is a valid retry count:
    - Must be an integer
    - Must be between 0 and MAX_RETRIES_LIMIT
    
    Raises:
        InvalidConfigurationError: If retry count is invalid
    """
    @functools.wraps(func)
    def wrapper(self, retries: int, *args, **kwargs):
        if not isinstance(retries, int) or retries < 0 or retries > MAX_RETRIES_LIMIT:
            raise InvalidConfigurationError(
                f"Max retries must be an integer between 0 and {MAX_RETRIES_LIMIT}"
            )
        
        return func(self, retries, *args, **kwargs)
    return wrapper


def validate_file_exists(func: F) -> F:
    """Decorator to validate file existence.
    
    Validates that the first pathlib.Path argument after self exists:
    - Path must exist on filesystem
    
    Raises:
        FileNotFoundError: If file does not exist
    """
    @functools.wraps(func)
    def wrapper(self, file_path: pathlib.Path, *args, **kwargs):
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return func(self, file_path, *args, **kwargs)
    return wrapper


def validate_directory_path(func: F) -> F:
    """Decorator to validate and create directory paths.
    
    Validates that the first pathlib.Path argument after self is a valid directory:
    - Must be a Path object
    - Creates directory if it doesn't exist (with parents)
    
    Raises:
        InvalidConfigurationError: If path is invalid or cannot be created
    """
    @functools.wraps(func)
    def wrapper(self, path: pathlib.Path, *args, **kwargs):
        if not isinstance(path, pathlib.Path):
            raise InvalidConfigurationError("Directory path must be a Path object")
        
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise InvalidConfigurationError(f"Cannot create directory {path}: {e}")
        
        return func(self, path, *args, **kwargs)
    return wrapper


def require_database_connection(func: F) -> F:
    """Decorator to ensure database connection exists.
    
    Validates that self.connection is not None before executing the function.
    
    Raises:
        DatabaseConnectionError: If database is not connected
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'connection') or not self.connection:
            raise DatabaseConnectionError("Database not connected")
        
        return func(self, *args, **kwargs)
    return wrapper


def validate_supported_file_type(supported_extensions: set) -> Callable[[F], F]:
    """Decorator factory to validate file types against supported extensions.
    
    Args:
        supported_extensions: Set of supported file extensions (e.g., {'.png', '.jpg'})
    
    Returns:
        Decorator that validates file type
        
    Raises:
        UnsupportedFileTypeError: If file type is not supported
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, file_path: pathlib.Path, *args, **kwargs):
            if file_path.suffix.lower() not in supported_extensions:
                raise UnsupportedFileTypeError(
                    f"Unsupported file type: {file_path.suffix}"
                )
            
            return func(self, file_path, *args, **kwargs)
        return wrapper
    return decorator