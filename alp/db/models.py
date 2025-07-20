from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""
    pass


class User(Base):
    """User account model storing user profile (e.g., learning style)."""
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(nullable=False)
    learning_style: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now(dt.UTC))


class Note(Base):
    """Note model storing raw note content added by the user."""
    __tablename__ = "note"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class Concept(Base):
    """Concept model representing a knowledge graph node (may reference a Note)."""
    __tablename__ = "concept"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_known: Mapped[bool] = mapped_column(Boolean, default=False)


class Edge(Base):
    """Directed edge in the knowledge graph (source -> target concept relationship)."""
    __tablename__ = "edge"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("concept.id"))
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("concept.id"))
