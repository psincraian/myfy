---
name: scaffold-task
description: Create background tasks with TaskContext
---

# Task Scaffolding Agent

You help create myfy background tasks.

## Process

1. **Gather Requirements**
   - Task name and purpose
   - Input parameters
   - Progress reporting needs
   - Retry behavior
   - Return value

2. **Generate Task**

### Basic Task

```python
from myfy.tasks import task

@task
async def send_welcome_email(user_id: int, email: str) -> None:
    """
    Send welcome email to new user.

    Args:
        user_id: The user's ID
        email: The user's email address
    """
    await email_service.send(
        to=email,
        template="welcome",
        context={"user_id": user_id},
    )
```

### Task with Progress Reporting

```python
from myfy.tasks import task, TaskContext

@task
async def process_batch(items: list[str], ctx: TaskContext) -> int:
    """
    Process a batch of items with progress reporting.

    Args:
        items: List of items to process
        ctx: Task context for progress updates

    Returns:
        Number of successfully processed items
    """
    processed = 0

    for i, item in enumerate(items):
        # Check for cancellation
        if ctx.is_cancelled:
            return processed

        # Process item
        await process_item(item)
        processed += 1

        # Report progress
        await ctx.update_progress(
            current=i + 1,
            total=len(items),
            message=f"Processing {item}",
        )

    return processed
```

### Task with Retry Configuration

```python
@task(max_retries=5, retry_on=[ConnectionError, TimeoutError])
async def fetch_external_data(url: str) -> dict:
    """
    Fetch data from external API with retry support.

    Automatically retries up to 5 times on connection errors.

    Args:
        url: The URL to fetch

    Returns:
        The fetched data as dict
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

### Task with Custom Name

```python
@task(name="emails.send_bulk")
async def send_bulk_emails(
    recipients: list[str],
    subject: str,
    body: str,
    ctx: TaskContext,
) -> dict:
    """
    Send emails to multiple recipients.

    Custom name allows better organization in task monitoring.
    """
    sent = 0
    failed = 0

    for i, email in enumerate(recipients):
        try:
            await send_email(email, subject, body)
            sent += 1
        except Exception:
            failed += 1

        await ctx.update_progress(
            current=i + 1,
            total=len(recipients),
        )

    return {"sent": sent, "failed": failed}
```

### Task with DI Dependencies

Tasks support dependency injection using the TASK scope:

```python
from myfy.core import provider, TASK
from myfy.tasks import task, TaskContext

@provider(scope=TASK)
def task_logger(ctx: TaskContext) -> TaskLogger:
    return TaskLogger(task_id=ctx.task_id)

@task
async def process_order(
    order_id: int,
    logger: TaskLogger,  # Injected per-task
) -> None:
    """Process an order with task-scoped logger."""
    logger.info(f"Processing order {order_id}")
    # ... process order
    logger.info("Order processed successfully")
```

## Dispatching Tasks

```python
# Dispatch and get task ID (non-blocking)
task_id = await send_welcome_email.send(user_id=123, email="user@example.com")

# Dispatch and wait for result (blocking)
result = await process_batch.send_and_wait(items=["a", "b", "c"])

# Get result later by task ID
result = await send_welcome_email.get_result(task_id)
```

## Module Setup

```python
from myfy.core import Application
from myfy.data import DataModule
from myfy.tasks import TasksModule

app = Application()
app.add_module(DataModule())
app.add_module(TasksModule(auto_create_tables=True))
```

## Running Workers

```bash
# Start worker with default concurrency
myfy tasks worker

# Start worker with custom concurrency
myfy tasks worker --concurrency 4
```

## Task Options

| Option | Type | Description |
|--------|------|-------------|
| `name` | `str` | Custom task name (default: module.qualname) |
| `max_retries` | `int` | Override default max retries |
| `retry_on` | `list[Exception]` | Exception types that trigger retry |

## TaskContext Methods

| Method | Description |
|--------|-------------|
| `ctx.task_id` | Get the current task ID |
| `ctx.is_cancelled` | Check if task was cancelled |
| `ctx.update_progress(current, total, message)` | Report progress |

## Guidelines

- Always use async functions
- Add type hints for all parameters
- Use TaskContext for long-running tasks
- Handle cancellation gracefully
- Add retry logic for network operations
- Keep tasks idempotent when possible
