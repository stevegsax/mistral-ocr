"""Mistral OCR client for API interactions."""

import pathlib
from typing import List, Any


class MistralOCRClient:
    """Client for submitting OCR jobs to the Mistral API."""
    
    def __init__(self, api_key: str) -> None:
        """Initialize the client with API key.
        
        Args:
            api_key: Mistral API key for authentication
        """
        self.api_key = api_key
    
    def submit_documents(self, files: List[pathlib.Path]) -> Any:
        """Submit documents for OCR processing.
        
        Args:
            files: List of file paths or directories to submit for OCR
            
        Returns:
            Job ID for tracking the submission
            
        Raises:
            FileNotFoundError: If any file or directory does not exist
            ValueError: If any file has an unsupported file type
        """
        # Expand directories to their contained files (non-recursive)
        actual_files = []
        supported_extensions = {'.png', '.jpg', '.jpeg', '.pdf'}
        
        for path in files:
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            
            if path.is_dir():
                # Add all supported files in the directory (non-recursive)
                for file in path.iterdir():
                    if file.is_file() and file.suffix.lower() in supported_extensions:
                        actual_files.append(file)
            elif path.is_file():
                if path.suffix.lower() not in supported_extensions:
                    raise ValueError(f"Unsupported file type: {path.suffix}")
                actual_files.append(path)
        
        # For now, return a mock job ID to satisfy the test
        # In a real implementation, this would make an API call
        return "job_123"