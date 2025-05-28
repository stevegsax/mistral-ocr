"""Mistral OCR client library."""

from ._version import __version__
from .client import MistralOCRClient
from .models import OCRResult

__all__ = ["MistralOCRClient", "OCRResult", "__version__"]
