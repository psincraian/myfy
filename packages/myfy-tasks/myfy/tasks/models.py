"""
SQLAlchemy models for task queue.

Defines the TaskRecord model and TaskStatus enum for database persistence.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class JSONType(TypeDecorator):
    """
    Database-agnostic JSON type.

    Stores JSON data as text for compatibility with all SQL databases.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:  # noqa: ARG002
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value: str | None, dialect: Any) -> Any:  # noqa: ARG002
        if value is not None:
            return json.loads(value)
        return None


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TasksBase(DeclarativeBase):
    """Base class for tasks module models."""


def generate_task_id() -> str:
    """Generate a unique task ID."""
    return str(uuid.uuid4())


class TaskRecord(TasksBase):
    """
    SQLAlchemy model for task queue.

    Stores task definitions, arguments, status, and results.
    """

    __tablename__ = "myfy_tasks"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_task_id,
    )

    # Task identification
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    args: Mapped[dict] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskStatus.PENDING.value,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Retry configuration
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    # Timing
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Error information
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error_traceback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Result
    result: Mapped[Any | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    # Worker tracking
    worker_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Progress tracking
    progress_current: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    progress_total: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    progress_message: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (Index("idx_myfy_tasks_status_scheduled", "status", "scheduled_at"),)

    def __repr__(self) -> str:
        return f"TaskRecord(id={self.id!r}, name={self.name!r}, status={self.status!r})"
