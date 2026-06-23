from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship, sessionmaker

# SQLite is simple and enough for a local coursework web application.
DB_PATH = Path(__file__).parent / "localgpt.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Deleting a user also deletes that user's chats and messages.
    chats: Mapped[list["Chat"]] = relationship(
        "Chat",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(80), default="New chat", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    chat: Mapped[Chat] = relationship("Chat", back_populates="messages")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that opens and closes a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(engine)


def _has_column(conn, table_name: str, column_name: str) -> bool:
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def apply_simple_sqlite_migrations() -> None:
    """Add new columns when an older local database already exists.

    This is intentionally simple and readable for a coursework project.
    It avoids losing existing users, chats and messages when the setup script is rerun.
    """
    with engine.begin() as conn:
        if not _has_column(conn, "users", "created_at"):
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN created_at DATETIME")
            conn.exec_driver_sql("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

        if not _has_column(conn, "chats", "title"):
            conn.exec_driver_sql("ALTER TABLE chats ADD COLUMN title VARCHAR(80) DEFAULT 'New chat'")
            conn.exec_driver_sql("UPDATE chats SET title = 'New chat' WHERE title IS NULL OR title = ''")

        if not _has_column(conn, "chats", "created_at"):
            conn.exec_driver_sql("ALTER TABLE chats ADD COLUMN created_at DATETIME")
            conn.exec_driver_sql("UPDATE chats SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

        if not _has_column(conn, "chats", "updated_at"):
            conn.exec_driver_sql("ALTER TABLE chats ADD COLUMN updated_at DATETIME")
            conn.exec_driver_sql("UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

        if not _has_column(conn, "messages", "created_at"):
            conn.exec_driver_sql("ALTER TABLE messages ADD COLUMN created_at DATETIME")
            conn.exec_driver_sql("UPDATE messages SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")


apply_simple_sqlite_migrations()
