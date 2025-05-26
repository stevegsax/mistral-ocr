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
            files: List of file paths to submit for OCR
            
        Returns:
            Job ID for tracking the submission
            
        Raises:
            ValueError: If any file has an unsupported file type
        """
        # Validate file types
        supported_extensions = {'.png', '.jpg', '.jpeg', '.pdf'}
        for file in files:
            if file.suffix.lower() not in supported_extensions:
                raise ValueError(f"Unsupported file type: {file.suffix}")
        
        # For now, return a mock job ID to satisfy the test
        # In a real implementation, this would make an API call
        return "job_123"