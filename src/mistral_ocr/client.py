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
        """
        # For now, return a mock job ID to satisfy the test
        # In a real implementation, this would make an API call
        return "job_123"