"""Configuration management for Mistral OCR."""

import json
import os
import pathlib
from typing import Optional

from .types import ConfigData
from .validation import validate_api_key, validate_model_name, validate_timeout_range, validate_retry_count, validate_directory_path
from .utils.file_operations import FileIOUtils

from .constants import (
    MIN_API_KEY_LENGTH, DEFAULT_API_TIMEOUT_SECONDS, MAX_API_TIMEOUT_SECONDS,
    DEFAULT_MAX_RETRIES, MAX_RETRIES_LIMIT, DEFAULT_OCR_MODEL, API_KEY_ENV_VAR,
    JSON_INDENT_SPACES, DEFAULT_DOWNLOAD_DIR_NAME
)
from .exceptions import InvalidConfigurationError
from .paths import XDGPaths


class ConfigurationManager:
    """Manages configuration settings for the Mistral OCR client."""

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self.config_file = XDGPaths.get_config_file_path()
        self._config = self._load_config()

    @validate_api_key
    def validate_api_key(self, api_key: str) -> None:
        """Validate an API key format.
        
        Args:
            api_key: The API key to validate
            
        Raises:
            InvalidConfigurationError: If the API key format is invalid
        """
        # Validation logic is now handled by the decorator
        pass
    
    @validate_model_name
    def validate_model_name(self, model: str) -> None:
        """Validate a model name format.
        
        Args:
            model: The model name to validate
            
        Raises:
            InvalidConfigurationError: If the model name is invalid
        """
        # Validation logic is now handled by the decorator
        pass

    def _load_config(self) -> dict[str, str]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                return FileIOUtils.read_json_file(self.config_file)
            except (json.JSONDecodeError, IOError):
                # If config file is corrupted, return empty dict
                return {}
        return {}

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            FileIOUtils.write_json_file(self.config_file, self._config, indent=JSON_INDENT_SPACES)
        except IOError:
            # Handle save errors gracefully
            pass

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)  # type: ignore[return-value]

    def set(self, key: str, value: str) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value
        self._save_config()

    def get_api_key(self) -> Optional[str]:
        """Get the Mistral API key.

        Returns:
            API key from environment or config file
        """
        # Environment variable takes precedence
        api_key = os.environ.get(API_KEY_ENV_VAR)
        if api_key:
            return api_key

        # Fallback to config file
        return self.get("api_key")

    def set_api_key(self, api_key: str) -> None:
        """Set the Mistral API key in config file.

        Args:
            api_key: API key to store
            
        Raises:
            InvalidConfigurationError: If the API key is invalid
        """
        self.validate_api_key(api_key)
        self.set("api_key", api_key)

    def get_default_model(self) -> str:
        """Get the default OCR model.

        Returns:
            Default model name
        """
        return self.get("default_model", DEFAULT_OCR_MODEL) or DEFAULT_OCR_MODEL

    def set_default_model(self, model: str) -> None:
        """Set the default OCR model.

        Args:
            model: Model name to use as default
            
        Raises:
            InvalidConfigurationError: If the model name is invalid
        """
        self.validate_model_name(model)
        self.set("default_model", model)

    def get_download_directory(self) -> pathlib.Path:
        """Get the download directory for results.

        Returns:
            Path to download directory
        """
        download_dir = self.get("download_directory")
        if download_dir:
            return pathlib.Path(download_dir)

        return XDGPaths.get_data_dir() / DEFAULT_DOWNLOAD_DIR_NAME

    @validate_directory_path
    def set_download_directory(self, path: pathlib.Path) -> None:
        """Set the download directory for results.

        Args:
            path: Path to download directory
            
        Raises:
            InvalidConfigurationError: If the path is invalid
        """
        # Validation logic is now handled by the decorator
        self.set("download_directory", str(path))

    def get_timeout(self) -> int:
        """Get the API timeout in seconds.
        
        Returns:
            Timeout value in seconds (default: 300)
        """
        timeout_str = self.get("api_timeout", str(DEFAULT_API_TIMEOUT_SECONDS))
        try:
            return int(timeout_str)
        except ValueError:
            return DEFAULT_API_TIMEOUT_SECONDS
    
    @validate_timeout_range
    def set_timeout(self, timeout: int) -> None:
        """Set the API timeout in seconds.
        
        Args:
            timeout: Timeout value in seconds
            
        Raises:
            InvalidConfigurationError: If timeout value is invalid
        """
        # Validation logic is now handled by the decorator
        self.set("api_timeout", str(timeout))
    
    def get_max_retries(self) -> int:
        """Get the maximum number of API retries.
        
        Returns:
            Maximum retry count (default: 3)
        """
        retries_str = self.get("max_retries", str(DEFAULT_MAX_RETRIES))
        try:
            return int(retries_str)
        except ValueError:
            return DEFAULT_MAX_RETRIES
    
    @validate_retry_count
    def set_max_retries(self, retries: int) -> None:
        """Set the maximum number of API retries.
        
        Args:
            retries: Maximum retry count
            
        Raises:
            InvalidConfigurationError: If retry count is invalid
        """
        # Validation logic is now handled by the decorator
        self.set("max_retries", str(retries))
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        # Keep API key but reset other settings
        api_key = self.get_api_key()
        self._config = {}
        if api_key and "MISTRAL_API_KEY" not in os.environ:
            # Only preserve file-based API key if not in environment
            self.set("api_key", api_key)
        self._save_config()
    
    @property
    def database_path(self) -> pathlib.Path:
        """Get the database file path."""
        return XDGPaths.get_database_path()

    @property
    def log_directory(self) -> pathlib.Path:
        """Get the log directory."""
        return XDGPaths.get_state_dir()
    
    @property
    def data_directory(self) -> pathlib.Path:
        """Get the data directory."""
        return XDGPaths.get_data_dir()
    
    @property
    def cache_directory(self) -> pathlib.Path:
        """Get the cache directory."""
        return XDGPaths.get_cache_dir()
    
    @property
    def config_directory(self) -> pathlib.Path:
        """Get the config directory."""
        return XDGPaths.get_config_dir()
