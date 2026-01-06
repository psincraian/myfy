# myfy-tasks

Asynchronous task processing module for the myfy framework.

Provides Celery/Dramatiq-like background task execution using a SQL-based queue.

## Installation

```bash
pip install myfy-tasks
```

## Quick Start

### 1. Define Tasks

```python
from myfy.tasks import task, TaskContext

# Simple task
@task
async def send_email(to: str, subject: str, body: str) -> None:
    """Send an email asynchronously."""
    # Your email sending logic here
    print(f"Sending email to {to}: {subject}")

# Task with progress reporting
@task
async def process_batch(items: list[str], ctx: TaskContext) -> int:
    """Process items with progress tracking."""
    for i, item in enumerate(items):
        # Process item...
        await ctx.update_progress(current=i + 1, total=len(items))
    return len(items)

# Task with custom options
@task(max_retries=5)
async def unreliable_task(data: str) -> str:
    """Task that might fail and needs retries."""
    return f"processed: {data}"
```

### 2. Configure Your Application

```python
from myfy import Application
from myfy.data import DataModule
from myfy.tasks import TasksModule

app = Application(
    modules=[
        DataModule(),
        TasksModule(),  # Requires DataModule
    ]
)
```

### 3. Dispatch Tasks

```python
# Basic dispatch
task_id = await send_email.send(
    to="user@example.com",
    subject="Hello",
    body="World",
)

# With options (underscore prefix)
task_id = await send_email.send(
    to="user@example.com",
    subject="Urgent",
    body="Important message",
    _priority=10,      # Higher priority = executed first
    _delay=60,         # Delay execution by 60 seconds
    _max_retries=5,    # Override default retries
)
```

### 4. Start a Worker

```bash
myfy tasks worker
```

Or with options:

```bash
myfy tasks worker --concurrency 8 --worker-id worker-1
```

## Task API

### The `@task` Decorator

```python
from myfy.tasks import task

@task
async def my_task(arg1: str, arg2: int) -> str:
    return f"{arg1}: {arg2}"

@task(max_retries=3)
async def retrying_task(data: str) -> None:
    pass
```

### Dispatch Options

When calling `.send()`, use underscore-prefixed kwargs for options:

- `_priority: int` - Higher priority tasks execute first (default: 0)
- `_delay: float` - Seconds to wait before task becomes eligible (default: 0)
- `_max_retries: int` - Override default max retries

```python
await my_task.send(
    arg1="hello",
    arg2=42,
    _priority=10,
    _delay=30,
)
```

### TaskContext

Inject `TaskContext` for progress reporting and metadata:

```python
from myfy.tasks import task, TaskContext

@task
async def long_task(items: list[str], ctx: TaskContext) -> int:
    for i, item in enumerate(items):
        # Check if cancelled
        if ctx.is_cancelled():
            return i

        # Process item
        process(item)

        # Report progress
        await ctx.update_progress(
            current=i + 1,
            total=len(items),
            message=f"Processing {item}",
        )

    return len(items)
```

TaskContext provides:
- `task_id: str` - Unique task identifier
- `attempt: int` - Current retry attempt (1-based)
- `update_progress(current, total, message)` - Report progress
- `is_cancelled()` - Check if task was cancelled

### Retrieving Results

```python
from myfy.tasks import TaskStatus

# Get result (polls until complete or timeout)
result = await my_task.get_result(task_id, timeout=30.0)

if result.status == TaskStatus.COMPLETED:
    print(f"Result: {result.value}")
elif result.status == TaskStatus.FAILED:
    print(f"Error: {result.error}")

# Check progress
if result.progress:
    current, total = result.progress
    print(f"Progress: {current}/{total}")
```

## Dependency Injection

Tasks support automatic dependency injection. Primitive types are treated as task arguments (serialized to the queue), while complex types are injected at execution time:

```python
from myfy.tasks import task

class EmailService:
    async def send(self, to: str, subject: str, body: str) -> None:
        pass

@task
async def send_notification(
    # Task arguments (serialized)
    user_id: str,
    message: str,
    # DI dependencies (injected at execution)
    email_service: EmailService,
) -> None:
    await email_service.send(user_id, "Notification", message)

# When dispatching, only pass task arguments
await send_notification.send(user_id="123", message="Hello!")
# email_service is injected by the worker
```

## Configuration

Configure via environment variables (prefix: `MYFY_TASKS_`):

```bash
export MYFY_TASKS_POLL_INTERVAL=1.0
export MYFY_TASKS_WORKER_CONCURRENCY=4
export MYFY_TASKS_DEFAULT_MAX_RETRIES=3
export MYFY_TASKS_TASK_TIMEOUT=300
```

Or via code:

```python
from myfy.tasks import TasksModule, TasksSettings

settings = TasksSettings(
    poll_interval=1.0,
    worker_concurrency=4,
    default_max_retries=3,
    task_timeout=300.0,
)

app = Application(
    modules=[
        DataModule(),
        TasksModule(settings=settings),
    ]
)
```

### Available Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `poll_interval` | 1.0 | Seconds between queue polls |
| `worker_concurrency` | 4 | Concurrent task executions |
| `worker_id` | auto | Unique worker identifier |
| `default_max_retries` | 3 | Default retry count |
| `retry_delay_seconds` | 60.0 | Delay between retries |
| `task_timeout` | 300.0 | Task execution timeout (seconds) |
| `table_name` | myfy_tasks | Database table name |
| `claim_batch_size` | 10 | Tasks claimed per poll |
| `stale_task_timeout` | 3600.0 | Timeout for stale tasks |
| `auto_create_tables` | True | Create tables on startup |

## CLI Commands

```bash
# Start a worker
myfy tasks worker
myfy tasks worker --concurrency 8
myfy tasks worker --worker-id worker-1

# List registered tasks
myfy tasks list

# Show queue statistics
myfy tasks stats

# Purge old tasks
myfy tasks purge --status completed --days 7
myfy tasks purge --status failed --days 30 --force
```

## Testing

Use the provided test utilities:

```python
import pytest
from myfy.data.testing import test_database
from myfy.tasks.testing import test_task_runner

@task
async def my_task(value: str) -> str:
    return f"processed: {value}"

@pytest.mark.asyncio
async def test_my_task():
    async with test_database() as (data_module, session_factory):
        async with test_task_runner(session_factory) as runner:
            # Dispatch task
            task_id = await my_task.send(value="test")

            # Process pending tasks (synchronous execution)
            await runner.process_pending()

            # Assertions
            assert runner.was_called(my_task)
            assert runner.call_count(my_task) == 1

            call = runner.last_call(my_task)
            assert call.args["value"] == "test"
            assert call.result == "processed: test"
```

### TestTaskRunner API

- `was_called(task)` - Check if task was executed
- `call_count(task)` - Number of executions
- `last_call(task)` - Get last TaskCall record
- `all_calls(task=None)` - Get all calls, optionally filtered
- `clear()` - Reset call records
- `process_pending(max_tasks=100)` - Process queued tasks

## Architecture

myfy-tasks uses a SQL-based polling architecture:

1. **Task Dispatch**: Tasks are serialized and inserted into the database
2. **Worker Polling**: Workers poll for pending tasks using `SELECT ... FOR UPDATE SKIP LOCKED`
3. **Task Execution**: Workers execute tasks with DI injection and TASK scope
4. **Result Storage**: Results/errors are stored back in the database

This approach provides:
- Database-agnostic operation (SQLite, PostgreSQL, MySQL)
- Reliable task persistence
- No external dependencies (no Redis/RabbitMQ required)
- Simple deployment

## Requirements

- Python 3.12+
- myfy-core
- myfy-data (for database access)
