"""
SQLAlchemy models for web_data integration tests.

These are real models used to test database operations through HTTP handlers.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import declarative_base, relationship

# Create a separate Base for these tests to avoid conflicts
Base = declarative_base()


class User(Base):
    """User model for testing CRUD operations."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationship to posts
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Post(Base):
    """Post model for testing relationships and foreign keys."""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(String(10000), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationship to user
    author = relationship("User", back_populates="posts")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "author_id": self.author_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
