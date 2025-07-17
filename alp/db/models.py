from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean
import uuid, datetime as dt


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'user'
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(nullable=False)
    learning_style: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now(dt.UTC))


class Note(Base):
    __tablename__ = "note"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class Concept(Base):
    __tablename__ = "concept"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_known: Mapped[bool] = mapped_column(Boolean, default=False)


class Edge(Base):
    __tablename__ = "edge"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("concept.id"))
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("concept.id"))
