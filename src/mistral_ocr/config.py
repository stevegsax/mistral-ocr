"""Configuration management for Mistral OCR."""

import json
import os
import pathlib
from typing import Optional


class ConfigurationManager:
    """Manages configuration settings for the Mistral OCR client."""

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self.config_dir = self._get_config_directory()
        self.config_file = self.config_dir / "config.json"
        self.data_dir = self._get_data_directory()
        self.cache_dir = self._get_cache_directory()

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._config = self._load_config()

    def _get_config_directory(self) -> pathlib.Path:
        """Get the configuration directory following XDG spec."""
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            return pathlib.Path(xdg_config_home) / "mistral-ocr"

        # Fallback to ~/.config/mistral-ocr
        home = pathlib.Path.home()
        return home / ".config" / "mistral-ocr"

    def _get_data_directory(self) -> pathlib.Path:
        """Get the data directory following XDG spec."""
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return pathlib.Path(xdg_data_home) / "mistral-ocr"

        # Fallback to ~/.local/share/mistral-ocr
        home = pathlib.Path.home()
        return home / ".local" / "share" / "mistral-ocr"

    def _get_cache_directory(self) -> pathlib.Path:
        """Get the cache directory following XDG spec."""
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache_home:
            return pathlib.Path(xdg_cache_home) / "mistral-ocr"

        # Fallback to ~/.cache/mistral-ocr
        home = pathlib.Path.home()
        return home / ".cache" / "mistral-ocr"

    def _load_config(self) -> dict[str, str]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If config file is corrupted, return empty dict
                return {}
        return {}

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self._config, f, indent=2)
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
        api_key = os.environ.get("MISTRAL_API_KEY")
        if api_key:
            return api_key

        # Fallback to config file
        return self.get("api_key")

    def set_api_key(self, api_key: str) -> None:
        """Set the Mistral API key in config file.

        Args:
            api_key: API key to store
        """
        self.set("api_key", api_key)

    def get_default_model(self) -> str:
        """Get the default OCR model.

        Returns:
            Default model name
        """
        return self.get("default_model", "mistral-ocr-latest") or "mistral-ocr-latest"

    def set_default_model(self, model: str) -> None:
        """Set the default OCR model.

        Args:
            model: Model name to use as default
        """
        self.set("default_model", model)

    def get_download_directory(self) -> pathlib.Path:
        """Get the download directory for results.

        Returns:
            Path to download directory
        """
        download_dir = self.get("download_directory")
        if download_dir:
            return pathlib.Path(download_dir)

        return self.data_dir / "downloads"

    def set_download_directory(self, path: pathlib.Path) -> None:
        """Set the download directory for results.

        Args:
            path: Path to download directory
        """
        self.set("download_directory", str(path))

    @property
    def database_path(self) -> pathlib.Path:
        """Get the database file path."""
        return self.data_dir / "mistral_ocr.db"

    @property
    def log_directory(self) -> pathlib.Path:
        """Get the log directory."""
        return self.data_dir / "logs"

