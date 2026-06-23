from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Mapped, mapped_column, Session
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

# fastapi dependency for db
def get_db() -> Generator[Session, None, None]:
    s: Session = SessionLocal()
    try:
        yield s
    finally:
        s.close()

# init tables if new file
Base.metadata.create_all(engine)
