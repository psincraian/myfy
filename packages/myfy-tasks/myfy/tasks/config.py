"""
Tasks module configuration.

Each module defines its own settings for modularity (ADR-0002).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from myfy.core.config import BaseSettings


class TasksSettings(BaseSettings):
    """
    Tasks module settings.

    Configure task processing, worker behavior, and queue settings.

    Environment variables use the MYFY_TASKS_ prefix:
    - MYFY_TASKS_POLL_INTERVAL
    - MYFY_TASKS_WORKER_CONCURRENCY
    - MYFY_TASKS_DEFAULT_MAX_RETRIES
    - etc.

    Example:
        ```python
        # Via environment
        export MYFY_TASKS_POLL_INTERVAL=2.0
        export MYFY_TASKS_WORKER_CONCURRENCY=8

        # Via code
        settings = TasksSettings(
            poll_interval=2.0,
            worker_concurrency=8,
        )
        ```
    """

    # Worker settings
    poll_interval: float = Field(
        default=1.0,
        description="Seconds between polling for new tasks",
        ge=0.1,
    )
    worker_concurrency: int = Field(
        default=4,
        description="Number of concurrent task executions per worker",
        ge=1,
    )
    worker_id: str | None = Field(
        default=None,
        description="Unique worker ID (auto-generated if not set)",
    )

    # Task execution settings
    default_max_retries: int = Field(
        default=3,
        description="Default maximum retry attempts for failed tasks",
        ge=0,
    )
    retry_delay_seconds: float = Field(
        default=60.0,
        description="Seconds to wait before retrying a failed task",
        ge=0,
    )
    task_timeout: float = Field(
        default=300.0,
        description="Maximum seconds a task can run before being killed",
        ge=1,
    )

    # Queue settings
    table_name: str = Field(
        default="myfy_tasks",
        description="Database table name for task queue",
    )
    claim_batch_size: int = Field(
        default=10,
        description="Number of tasks to claim in a single poll",
        ge=1,
    )
    stale_task_timeout: float = Field(
        default=3600.0,
        description="Seconds before a running task is considered stale and reclaimable",
        ge=60,
    )

    model_config = SettingsConfigDict(env_prefix="MYFY_TASKS_")
