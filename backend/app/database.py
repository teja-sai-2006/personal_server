import os
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship

# Database configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "db", "personal_server.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# SQLAlchemy engine and session
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    emk = Column(String, nullable=False)  # Encrypted Master Key (Base64)
    remk = Column(String, nullable=True)  # Recovery Encrypted Master Key (Base64)
    recovery_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    media = relationship("Media", back_populates="owner")

class Media(Base):
    __tablename__ = "media"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="media")

class SharedItem(Base):
    """Represents a shared folder or individual media item using an Ephemeral Folder Key (EFK)"""
    __tablename__ = "shared_items"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    media_id = Column(Integer, ForeignKey("media.id"), nullable=True) # If null, it's a folder share
    efk = Column(String, nullable=False) # Base64 Encrypted EFK or raw EFK depending on design
    ephemeral_filepath = Column(String, nullable=True) # Path to the EFK encrypted file
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class InviteLink(Base):
    __tablename__ = "invite_links"
    token = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PasswordItem(Base):
    __tablename__ = "password_items"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    website = Column(String, nullable=False)
    username = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=False) # Base64 encrypted with UMK
    created_at = Column(DateTime, default=datetime.utcnow)

class AuthItem(Base):
    __tablename__ = "auth_items"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False) # e.g. "Google", "GitHub"
    encrypted_secret = Column(String, nullable=False) # Base64 encrypted with UMK
    created_at = Column(DateTime, default=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
