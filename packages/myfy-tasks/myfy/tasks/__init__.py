"""
myfy-tasks: Asynchronous task processing for myfy framework.

Provides a SQL-based task queue with worker processes for
executing background jobs.

Quick Start:
    ```python
    from myfy.core import Application
    from myfy.data import DataModule
    from myfy.tasks import TasksModule, task, TaskContext

    # Setup application
    app = Application()
    app.add_module(DataModule())
    app.add_module(TasksModule(auto_create_tables=True))

    # Define a task
    @task
    async def send_email(to: str, subject: str, body: str) -> None:
        # Your implementation here
        pass

    # Define a task with progress
    @task
    async def process_batch(items: list[str], ctx: TaskContext) -> int:
        for i, item in enumerate(items):
            # Process item
            await ctx.update_progress(current=i + 1, total=len(items))
        return len(items)

    # Dispatch tasks
    task_id = await send_email.send(
        to="user@example.com",
        subject="Hello",
        body="World",
    )

    # Get result
    result = await send_email.get_result(task_id)
    ```

Running Workers:
    ```bash
    myfy tasks worker --concurrency 4
    ```
"""

from .config import TasksSettings
from .context import TaskContext
from .decorator import task
from .errors import (
    TaskAlreadyRegisteredError,
    TaskCancelledError,
    TaskError,
    TaskExecutionError,
    TaskNotFoundError,
    TaskSerializationError,
    TasksModuleNotConfiguredError,
    TaskTimeoutError,
)
from .extensions import ITaskProvider
from .models import TaskRecord, TasksBase, TaskStatus
from .module import TasksModule, tasks_module
from .queue import TaskQueue
from .registry import TaskRegistry
from .result import TaskResult
from .task import Task
from .worker import TaskWorker

__version__ = "0.1.0"

__all__ = [
    "ITaskProvider",
    "Task",
    "TaskAlreadyRegisteredError",
    "TaskCancelledError",
    "TaskContext",
    "TaskError",
    "TaskExecutionError",
    "TaskNotFoundError",
    "TaskQueue",
    "TaskRecord",
    "TaskRegistry",
    "TaskResult",
    "TaskSerializationError",
    "TaskStatus",
    "TaskTimeoutError",
    "TaskWorker",
    "TasksBase",
    "TasksModule",
    "TasksModuleNotConfiguredError",
    "TasksSettings",
    "__version__",
    "task",
    "tasks_module",
]
