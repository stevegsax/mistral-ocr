"""SQLAlchemy models for Mistral OCR database."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Document(Base):
    """Document model for storing document metadata."""

    __tablename__ = "documents"

    uuid: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    downloaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="document")
    pages: Mapped[list["Page"]] = relationship("Page", back_populates="document")


class Job(Base):
    """Job model for storing batch job information."""

    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    document_uuid: Mapped[str] = mapped_column(
        String, ForeignKey("documents.uuid"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    file_count: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    last_api_refresh: Mapped[Optional[datetime]] = mapped_column(DateTime)
    api_response_json: Mapped[Optional[str]] = mapped_column(Text)
    api_created_at: Mapped[Optional[str]] = mapped_column(String)
    api_completed_at: Mapped[Optional[str]] = mapped_column(String)
    total_requests: Mapped[Optional[int]] = mapped_column(Integer)
    input_files_json: Mapped[Optional[str]] = mapped_column(Text)
    output_file: Mapped[Optional[str]] = mapped_column(String)
    errors_json: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    document: Mapped[Document] = relationship("Document", back_populates="jobs")


class Page(Base):
    """Page model for storing individual page/file information."""

    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    document_uuid: Mapped[str] = mapped_column(
        String, ForeignKey("documents.uuid"), nullable=False
    )
    file_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    document: Mapped[Document] = relationship("Document", back_populates="pages")