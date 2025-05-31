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
    downloads: Mapped[list["Download"]] = relationship("Download", back_populates="document")


class Job(Base):
    """Job model for storing batch job information."""

    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    document_uuid: Mapped[str] = mapped_column(String, ForeignKey("documents.uuid"), nullable=False)
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
    downloads: Mapped[list["Download"]] = relationship("Download", back_populates="job")


class Page(Base):
    """Page model for storing individual page/file information."""

    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    document_uuid: Mapped[str] = mapped_column(String, ForeignKey("documents.uuid"), nullable=False)
    file_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    document: Mapped[Document] = relationship("Document", back_populates="pages")


class Download(Base):
    """Downloaded file record with actual OCR content."""

    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_uuid: Mapped[str] = mapped_column(String, ForeignKey("documents.uuid"), nullable=False)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.job_id"), nullable=False)
    document_order: Mapped[int] = mapped_column(Integer, nullable=False)
    text_path: Mapped[str] = mapped_column(String, nullable=False)
    markdown_path: Mapped[str] = mapped_column(String, nullable=False)
    
    # Actual OCR content stored in database
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    markdown_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_data_base64: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    document: Mapped[Document] = relationship("Document", back_populates="downloads")
    job: Mapped[Job] = relationship("Job", back_populates="downloads")
