"""Unified settings management for Mistral OCR."""

import os
import pathlib
from typing import Optional

from .config import ConfigurationManager
from .constants import MOCK_MODE_ENV_VAR
from .exceptions import InvalidConfigurationError, MissingConfigurationError
from .paths import XDGPaths


class Settings:
    """Unified settings manager that combines configuration and path management."""
    
    def __init__(self) -> None:
        """Initialize the settings manager."""
        self._config = ConfigurationManager()
    
    # API Configuration
    def get_api_key(self) -> str:
        """Get the Mistral API key.
        
        Returns:
            API key from environment or config file
            
        Raises:
            MissingConfigurationError: If no API key is found
        """
        api_key = self._config.get_api_key()
        if not api_key:
            raise MissingConfigurationError(
                "API key must be provided either as parameter or "
                "MISTRAL_API_KEY environment variable"
            )
        return api_key
    
    def get_api_key_optional(self) -> Optional[str]:
        """Get the API key without raising an exception if missing.
        
        Returns:
            API key or None if not configured
        """
        return self._config.get_api_key()
    
    def set_api_key(self, api_key: str) -> None:
        """Set the API key in configuration.
        
        Args:
            api_key: The API key to store
            
        Raises:
            InvalidConfigurationError: If the API key is invalid
        """
        self._config.set_api_key(api_key)
    
    def get_default_model(self) -> str:
        """Get the default OCR model.
        
        Returns:
            Default model name
        """
        return self._config.get_default_model()
    
    def set_default_model(self, model: str) -> None:
        """Set the default OCR model.
        
        Args:
            model: Model name to use as default
            
        Raises:
            InvalidConfigurationError: If the model name is invalid
        """
        self._config.set_default_model(model)
    
    def get_timeout(self) -> int:
        """Get the API timeout in seconds."""
        return self._config.get_timeout()
    
    def set_timeout(self, timeout: int) -> None:
        """Set the API timeout in seconds.
        
        Args:
            timeout: Timeout value in seconds
            
        Raises:
            InvalidConfigurationError: If timeout value is invalid
        """
        self._config.set_timeout(timeout)
    
    def get_max_retries(self) -> int:
        """Get the maximum number of API retries."""
        return self._config.get_max_retries()
    
    def set_max_retries(self, retries: int) -> None:
        """Set the maximum number of API retries.
        
        Args:
            retries: Maximum retry count
            
        Raises:
            InvalidConfigurationError: If retry count is invalid
        """
        self._config.set_max_retries(retries)
    
    # Path Management
    @property
    def database_path(self) -> pathlib.Path:
        """Get the database file path."""
        return XDGPaths.get_database_path()
    
    @property
    def log_file_path(self) -> pathlib.Path:
        """Get the log file path."""
        return XDGPaths.get_log_file_path()
    
    @property
    def data_directory(self) -> pathlib.Path:
        """Get the data directory."""
        return XDGPaths.get_data_dir()
    
    @property
    def state_directory(self) -> pathlib.Path:
        """Get the state directory."""
        return XDGPaths.get_state_dir()
    
    @property
    def cache_directory(self) -> pathlib.Path:
        """Get the cache directory."""
        return XDGPaths.get_cache_dir()
    
    @property
    def config_directory(self) -> pathlib.Path:
        """Get the config directory."""
        return XDGPaths.get_config_dir()
    
    def get_download_directory(self) -> pathlib.Path:
        """Get the download directory for results."""
        return self._config.get_download_directory()
    
    def set_download_directory(self, path: pathlib.Path) -> None:
        """Set the download directory for results.
        
        Args:
            path: Path to download directory
            
        Raises:
            InvalidConfigurationError: If the path is invalid
        """
        self._config.set_download_directory(path)
    
    def resolve_download_destination(
        self, destination: Optional[pathlib.Path] = None
    ) -> pathlib.Path:
        """Resolve the download destination directory.
        
        Args:
            destination: Optional custom destination path
            
        Returns:
            Resolved destination path (custom destination or configured default)
        """
        if destination is not None:
            return destination
        return self.get_download_directory()
    
    # Configuration Management
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._config.reset_to_defaults()
    
    def get_raw_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a raw configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)
    
    def set_raw_config(self, key: str, value: str) -> None:
        """Set a raw configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config.set(key, value)
    
    # Validation
    def validate_configuration(self) -> None:
        """Validate the current configuration.
        
        Raises:
            MissingConfigurationError: If required settings are missing
            InvalidConfigurationError: If settings are invalid
        """
        # Check required settings
        self.get_api_key()  # Will raise if missing
        
        # Validate model name
        model = self.get_default_model()
        self._config.validate_model_name(model)
        
        # Validate timeout and retries
        timeout = self.get_timeout()
        if timeout < 1 or timeout > 3600:
            raise InvalidConfigurationError("Timeout must be between 1 and 3600 seconds")
            
        retries = self.get_max_retries()
        if retries < 0 or retries > 10:
            raise InvalidConfigurationError("Max retries must be between 0 and 10")
    
    def is_mock_mode(self) -> bool:
        """Check if mock mode is enabled via environment variable.
        
        Returns:
            True if mock mode is enabled
        """
        return os.environ.get(MOCK_MODE_ENV_VAR, "").lower() in ("1", "true", "yes")


# Global settings instance for convenience
_settings_instance: Optional[Settings] = None

def get_settings() -> Settings:
    """Get the global settings instance.
    
    Returns:
        Global Settings instance
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

def reset_settings() -> None:
    """Reset the global settings instance (mainly for testing)."""
    global _settings_instance
    _settings_instance = None