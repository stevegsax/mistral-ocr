"""XDG Base Directory specification utilities."""

import os
import pathlib
from typing import Optional


class XDGPaths:
    """Utility class for managing XDG Base Directory specification paths."""

    APPLICATION_NAME = "mistral-ocr"

    @classmethod
    def get_data_dir(cls) -> pathlib.Path:
        """Get the XDG data directory for the application.

        Returns:
            Path to data directory (for downloads, etc.)
        """
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            data_dir = pathlib.Path(xdg_data_home) / cls.APPLICATION_NAME
        else:
            # Fallback to XDG spec: ~/.local/share/mistral-ocr
            home = pathlib.Path.home()
            data_dir = home / ".local" / "share" / cls.APPLICATION_NAME

        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    @classmethod
    def get_state_dir(cls) -> pathlib.Path:
        """Get the XDG state directory for the application.

        Returns:
            Path to state directory (for database, logs, persistent state)
        """
        xdg_state_home = os.environ.get("XDG_STATE_HOME")
        if xdg_state_home:
            state_dir = pathlib.Path(xdg_state_home) / cls.APPLICATION_NAME
        else:
            # Fallback to XDG spec: ~/.local/state/mistral-ocr
            home = pathlib.Path.home()
            state_dir = home / ".local" / "state" / cls.APPLICATION_NAME

        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    @classmethod
    def get_log_file_path(cls) -> pathlib.Path:
        """Get the path to the application log file.

        Returns:
            Path to the log file
        """
        return cls.get_state_dir() / "mistral.log"

    @classmethod
    def get_database_path(cls) -> pathlib.Path:
        """Get the path to the application database file.

        Returns:
            Path to the database file
        """
        return cls.get_state_dir() / "mistral_ocr.db"

    @classmethod
    def get_config_dir(cls) -> pathlib.Path:
        """Get the XDG config directory for the application.

        Returns:
            Path to config directory (for configuration files)
        """
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            config_dir = pathlib.Path(xdg_config_home) / cls.APPLICATION_NAME
        else:
            # Fallback to XDG spec: ~/.config/mistral-ocr
            home = pathlib.Path.home()
            config_dir = home / ".config" / cls.APPLICATION_NAME

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @classmethod
    def get_cache_dir(cls) -> pathlib.Path:
        """Get the XDG cache directory for the application.

        Returns:
            Path to cache directory (for temporary files, downloads)
        """
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache_home:
            cache_dir = pathlib.Path(xdg_cache_home) / cls.APPLICATION_NAME
        else:
            # Fallback to XDG spec: ~/.cache/mistral-ocr
            home = pathlib.Path.home()
            cache_dir = home / ".cache" / cls.APPLICATION_NAME

        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @classmethod
    def get_config_file_path(cls) -> pathlib.Path:
        """Get the path to the application configuration file.

        Returns:
            Path to the configuration file
        """
        return cls.get_config_dir() / "config.json"

    @classmethod
    def resolve_download_destination(
        cls, destination: Optional[pathlib.Path] = None
    ) -> pathlib.Path:
        """Resolve the download destination directory.

        Args:
            destination: Optional custom destination path

        Returns:
            Resolved destination path
        """
        if destination is not None:
            return destination

        # Use XDG data directory as default
        return cls.get_data_dir()
