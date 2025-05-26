"""Logging setup for Mistral OCR."""

import logging
import pathlib


def setup_logging(log_dir: pathlib.Path) -> pathlib.Path:
    """Set up logging and return the log file path.

    Args:
        log_dir: Directory where log file should be created

    Returns:
        Path to the created log file
    """
    # Ensure the log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "mistral.log"

    # Create the log file
    log_file.touch()

    # Configure logging to write to the file
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Force reconfiguration even if logging was already configured
    )

    return log_file
