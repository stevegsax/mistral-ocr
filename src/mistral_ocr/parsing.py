"""OCR result parsing utilities."""

import json
from typing import Any, Dict, List, Optional

import structlog
from pydantic import ValidationError

from .data_types import BatchResultEntry, OCRResponseBody
from .models import OCRResult


class OCRResultParser:
    """Utility class for parsing OCR results from Mistral API responses."""

    def __init__(self, logger: structlog.BoundLogger):
        """Initialize the parser.

        Args:
            logger: Logger instance for reporting
        """
        self.logger = logger

    def parse_batch_output(self, output_content: str, job_id: str) -> List[OCRResult]:
        """Parse JSONL batch output from Mistral API.

        Args:
            output_content: Raw JSONL content from batch API
            job_id: Job ID for context in results

        Returns:
            List of parsed OCR results
        """
        self.logger.info(f"Downloaded output file, content length: {len(output_content)}")
        parsed_results = []

        for result_line in output_content.strip().split("\n"):
            if result_line.strip():
                try:
                    result_data = json.loads(result_line)
                    # First deserialize to Pydantic model for validation
                    batch_entry = BatchResultEntry(**result_data)
                    # Then process to OCR result
                    ocr_result = self._process_batch_entry(batch_entry, job_id)
                    if ocr_result:
                        parsed_results.append(ocr_result)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse result line: {e}")
                except ValidationError as e:
                    self.logger.warning(f"Failed to validate result structure: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing result: {e}")

        return parsed_results

    def _process_batch_entry(
        self, batch_entry: BatchResultEntry, job_id: str
    ) -> Optional[OCRResult]:
        """Process a validated batch entry to OCR result.

        Args:
            batch_entry: Validated Pydantic batch entry
            job_id: Job ID for context

        Returns:
            Parsed OCR result or None if processing fails
        """
        # Extract text content using various possible formats
        text_content = self._extract_text_content_from_body(batch_entry.response.body)
        if not text_content:
            return None

        # Extract markdown content (fallback to text if not available)
        markdown_content = self._extract_markdown_content_from_body(
            batch_entry.response.body, text_content
        )

        return OCRResult(
            text=text_content, 
            markdown=markdown_content, 
            file_name=batch_entry.custom_id, 
            job_id=job_id
        )

    def _parse_individual_ocr_result(
        self, result_data: Dict[str, Any], job_id: str
    ) -> Optional[OCRResult]:
        """Parse an individual OCR result from the batch output.

        Args:
            result_data: Single result data from JSONL
            job_id: Job ID for context

        Returns:
            Parsed OCR result or None if parsing fails
        """
        if "response" not in result_data or "body" not in result_data["response"]:
            return None

        response_body = result_data["response"]["body"]

        # Extract text content using various possible formats
        text_content = self._extract_text_content(response_body)
        if not text_content:
            return None

        # Extract markdown content (fallback to text if not available)
        markdown_content = self._extract_markdown_content(response_body, text_content)

        # Extract file name from custom_id
        file_name = result_data.get("custom_id", "unknown")

        return OCRResult(
            text=text_content, markdown=markdown_content, file_name=file_name, job_id=job_id
        )

    def _extract_text_content(self, response_body: Dict[str, Any]) -> Optional[str]:
        """Extract text content from response body using various formats.

        Args:
            response_body: Response body from API

        Returns:
            Extracted text content or None
        """
        # Check for pages format (Mistral OCR API)
        if "pages" in response_body and response_body["pages"]:
            page = response_body["pages"][0]  # Use first page
            if "text" in page:
                return page["text"]
            elif "markdown" in page:
                return page["markdown"]

        # Check for direct text/content format
        if "text" in response_body:
            return response_body["text"]

        if "content" in response_body:
            return response_body["content"]

        # Fallback to choices format
        if "choices" in response_body and response_body["choices"]:
            choice = response_body["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]

        return None

    def _extract_markdown_content(self, response_body: Dict[str, Any], fallback_text: str) -> str:
        """Extract markdown content from response body.

        Args:
            response_body: Response body from API
            fallback_text: Text content to use as fallback

        Returns:
            Markdown content or fallback text
        """
        # Check for pages format with markdown
        if "pages" in response_body and response_body["pages"]:
            page = response_body["pages"][0]
            if "markdown" in page:
                return page["markdown"]

        # Check for direct markdown format
        if "markdown" in response_body:
            return response_body["markdown"]

        # Use text content as fallback
        return fallback_text

    def _extract_text_content_from_body(self, response_body: OCRResponseBody) -> Optional[str]:
        """Extract text content from typed response body.

        Args:
            response_body: Typed response body from API

        Returns:
            Extracted text content or None
        """
        # Check for pages format (Mistral OCR API)
        if response_body.pages and len(response_body.pages) > 0:
            page = response_body.pages[0]  # Use first page
            if page.text:
                return page.text
            elif page.markdown:
                return page.markdown

        # Check for direct text/content format
        if response_body.text:
            return response_body.text

        if response_body.content:
            return response_body.content

        # Fallback to choices format
        if response_body.choices and len(response_body.choices) > 0:
            choice = response_body.choices[0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]

        return None

    def _extract_markdown_content_from_body(
        self, response_body: OCRResponseBody, fallback_text: str
    ) -> str:
        """Extract markdown content from typed response body.

        Args:
            response_body: Typed response body from API
            fallback_text: Text content to use as fallback

        Returns:
            Markdown content or fallback text
        """
        # Check for pages format with markdown
        if response_body.pages and len(response_body.pages) > 0:
            page = response_body.pages[0]
            if page.markdown:
                return page.markdown

        # Check for direct markdown format
        if response_body.markdown:
            return response_body.markdown

        # Use text content as fallback
        return fallback_text
