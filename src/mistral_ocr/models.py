"""Data models for Mistral OCR."""

from pydantic import BaseModel


class OCRResult(BaseModel):
    """OCR result from the Mistral API."""

    text: str
    markdown: str
    file_name: str
    job_id: str