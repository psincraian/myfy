"""
SQLAlchemy models for full_stack integration tests.
"""

from sqlalchemy import Column, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Task(Base):
    """Task model for the todo application."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    status = Column(String(20), default="pending", nullable=False)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON/template context."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
        }
