from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Mapped, mapped_column, Session, relationship
from typing import Generator

# sqlite file
DB_PATH = Path(__file__).parent / "localgpt.db"

# engine + local db factory
engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# orm base class
class Base(DeclarativeBase):
    pass

# users table
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)

    # relationship with chats
    chats = relationship("Chat", back_populates="user")

# fastapi dependency for db
def get_db() -> Generator[Session, None, None]:
    s: Session = SessionLocal()
    try:
        yield s
    finally:
        s.close()

# chat table
class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="chats")

    messages = relationship("Message", back_populates="chat")

# message table
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    content = Column(String, index=True)

    chat = relationship("Chat", back_populates="messages")

# init tables if new file
Base.metadata.create_all(engine)
