"""Document management for Mistral OCR."""

import uuid
from typing import Optional, Tuple

import structlog

from .constants import DOCUMENT_NAME_TEMPLATE, UUID_PREFIX_LENGTH
from .database import Database


class DocumentManager:
    """Manages document creation and UUID/name resolution."""

    def __init__(self, database: Database, logger: structlog.BoundLogger) -> None:
        """Initialize the document manager.

        Args:
            database: Database instance for document storage
            logger: Logger instance for logging operations
        """
        self.database = database
        self.logger = logger

    def resolve_document_uuid_and_name(
        self, document_name: Optional[str], document_uuid: Optional[str]
    ) -> Tuple[str, str]:
        """Resolve document UUID and name for job association.

        Args:
            document_name: Optional document name
            document_uuid: Optional document UUID

        Returns:
            Tuple of (document_uuid, document_name)
        """
        if document_uuid:
            self.logger.info(f"Using existing document UUID: {document_uuid}")
            # Use existing UUID, generate name if not provided
            resolved_name = document_name or DOCUMENT_NAME_TEMPLATE.format(
                uuid_prefix=document_uuid[:UUID_PREFIX_LENGTH]
            )
            self.database.store_document(document_uuid, resolved_name)
            return document_uuid, resolved_name

        if document_name:
            # Check if we should append to an existing document or create new one
            existing_uuid = self.database.get_recent_document_by_name(document_name)
            if existing_uuid:
                self.logger.info(
                    f"Appending to existing document '{document_name}' (UUID: {existing_uuid})"
                )
                return existing_uuid, document_name
            else:
                new_uuid = str(uuid.uuid4())
                self.logger.info(f"Creating new document '{document_name}' (UUID: {new_uuid})")
                self.database.store_document(new_uuid, document_name)
                return new_uuid, document_name

        # Generate both UUID and name
        new_uuid = str(uuid.uuid4())
        generated_name = DOCUMENT_NAME_TEMPLATE.format(uuid_prefix=new_uuid[:UUID_PREFIX_LENGTH])
        self.logger.info(f"Creating new document '{generated_name}' (UUID: {new_uuid})")
        self.database.store_document(new_uuid, generated_name)
        return new_uuid, generated_name
