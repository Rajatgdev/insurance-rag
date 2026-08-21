"""SQLAlchemy models: documents, chunks, embeddings, sessions."""
"""SQLAlchemy models mapped to the tables created by db/001_initial.sql.

Tables already exist (created during ingestion), so we map to them and never call
create_all. The embedding column is declared so Chunk.embedding.cosine_distance() works
in retrieval; results deliberately select scalar columns instead, so the vector is never
shipped back over the wire.
"""
from datetime import date

from sqlalchemy import ForeignKey, Text, Boolean, Integer, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from config import settings


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    insurer: Mapped[str] = mapped_column(Text)
    doc_type: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    version_date: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(Text)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    section: Mapped[str | None] = mapped_column(Text)
    clause_id: Mapped[str | None] = mapped_column(Text)
    is_exclusion: Mapped[bool] = mapped_column(Boolean, default=False)
    page: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.EMBED_DIMS))