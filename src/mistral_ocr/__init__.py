"""Mistral OCR client library - simplified version."""

from ._version import __version__
from .simple_client import SimpleMistralOCRClient

# Backward compatibility alias
MistralOCRClient = SimpleMistralOCRClient

__all__ = [
    "SimpleMistralOCRClient",
    "MistralOCRClient",
    "__version__",
]
