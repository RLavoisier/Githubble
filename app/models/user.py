import secrets
import uuid
from datetime import datetime

from sqlalchemy import UUID, Column, String, DateTime

from app.db.engine import Base


def generate_uuid() -> uuid.UUID:
    return uuid.uuid4()


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


class User(Base):
    __tablename__ = "user"

    id = Column(UUID, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True, default=generate_api_key)
    created = Column(DateTime, default=datetime.now)
    modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)
