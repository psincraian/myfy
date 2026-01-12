---
name: tasks-module
description: myfy TasksModule for background job processing with SQL-based queue. Use when working with TasksModule, @task decorator, background jobs, task workers, TaskContext, task retries, or async task dispatch.
---

# TasksModule - Background Jobs

TasksModule provides SQL-based async task processing with DI injection and automatic retries.

## Quick Start

```python
from myfy.core import Application
from myfy.data import DataModule
from myfy.tasks import TasksModule, task

app = Application()
app.add_module(DataModule())
app.add_module(TasksModule(auto_create_tables=True))

# Define a task
@task
async def send_email(to: str, subject: str, body: str) -> None:
    await email_service.send(to, subject, body)

# Dispatch from a route
@route.post("/notifications")
async def notify_user(body: NotifyRequest) -> dict:
    task_id = await send_email.send(
        to=body.email,
        subject="Welcome!",
        body="Thanks for signing up.",
    )
    return {"task_id": task_id}
```

## Configuration

Environment variables use the `MYFY_TASKS_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `MYFY_TASKS_DEFAULT_MAX_RETRIES` | `3` | Default retry attempts |
| `MYFY_TASKS_RETRY_DELAY_SECONDS` | `60.0` | Seconds between retries |
| `MYFY_TASKS_WORKER_CONCURRENCY` | `4` | Concurrent tasks per worker |
| `MYFY_TASKS_POLL_INTERVAL` | `1.0` | Seconds between queue polls |
| `MYFY_TASKS_TASK_TIMEOUT` | `300.0` | Max seconds per task |

## Defining Tasks

### Basic Task

```python
from myfy.tasks import task

@task
async def process_order(order_id: int) -> str:
    # Process the order
    return f"Processed order {order_id}"
```

### Task with DI Injection

Services are automatically injected at runtime:

```python
from myfy.tasks import task
from myfy.data import AsyncSession

@task
async def sync_user_data(user_id: int, session: AsyncSession) -> None:
    # session is TASK-scoped (injected per task execution)
    user = await session.get(User, user_id)
    await sync_to_external_service(user)
```

### Task with Custom Options

```python
@task(max_retries=5, retry_on=[ConnectionError, TimeoutError])
async def upload_file(file_path: str) -> str:
    # Retries up to 5 times on connection/timeout errors
    return await s3.upload(file_path)
```

## Dispatching Tasks

### Basic Dispatch

```python
# Returns immediately with task_id
task_id = await send_email.send(to="user@example.com", subject="Hi")
```

### Dispatch Options

```python
task_id = await send_email.send(
    to="user@example.com",
    subject="Hi",
    _priority=10,      # Higher priority = executes first
    _delay=60,         # Wait 60 seconds before executing
    _max_retries=5,    # Override default retries
)
```

### Getting Results

```python
result = await send_email.get_result(task_id, timeout=60)

if result.is_completed:
    print(f"Success: {result.value}")
elif result.is_failed:
    print(f"Error: {result.error}")
elif result.is_pending:
    print("Still processing...")
```

## TaskContext for Progress

Report progress from long-running tasks:

```python
from myfy.tasks import task, TaskContext

@task
async def import_users(file_path: str, ctx: TaskContext) -> int:
    users = load_users_from_file(file_path)
    total = len(users)

    for i, user in enumerate(users):
        await create_user(user)
        await ctx.update_progress(
            current=i + 1,
            total=total,
            message=f"Importing user {i + 1}/{total}",
        )

    return total
```

Check progress from caller:

```python
result = await import_users.get_result(task_id)
if result.progress:
    current, total = result.progress
    print(f"Progress: {current}/{total} - {result.progress_message}")
```

## Running Workers

Start a worker process:

```bash
myfy tasks worker
```

With options:

```bash
myfy tasks worker --concurrency 8 --poll-interval 0.5
```

Workers:
- Poll the database for pending tasks
- Execute tasks with full DI injection
- Handle retries automatically
- Report progress and results
- Gracefully shutdown on SIGTERM

## Task States

| Status | Description |
|--------|-------------|
| `pending` | Queued, waiting for worker |
| `running` | Being executed by worker |
| `completed` | Finished successfully |
| `failed` | Failed after all retries |
| `cancelled` | Manually cancelled |

## Error Handling

Tasks automatically retry on failure:

```python
@task(max_retries=3, retry_on=[APIError])
async def call_api(url: str) -> dict:
    response = await http.get(url)
    if response.status >= 500:
        raise APIError("Server error")  # Will retry
    return response.json()
```

After all retries fail:
- Task status becomes `failed`
- Error message and traceback are stored
- Can be retrieved via `get_result()`

## Parameter Classification

| Type | Behavior |
|------|----------|
| Primitives (`str`, `int`, `float`, `bool`) | Serialized as task args |
| Lists, dicts | Serialized as task args |
| TaskContext | Injected by worker |
| Services (other types) | DI injected at runtime |

```python
@task
async def complex_task(
    order_id: int,           # Serialized (primitive)
    items: list[str],        # Serialized (list)
    ctx: TaskContext,        # Injected (context)
    session: AsyncSession,   # DI injected (service)
    settings: AppSettings,   # DI injected (service)
) -> None:
    ...
```

## Best Practices

1. **Keep tasks idempotent** - Safe to retry on failure
2. **Serialize only primitives** - Complex objects should be loaded in task
3. **Use TaskContext** - Report progress for long tasks
4. **Set appropriate timeouts** - Prevent zombie tasks
5. **Monitor worker logs** - Watch for repeated failures
6. **Use priorities** - Critical tasks get processed first
7. **Handle cleanup** - TaskContext supports cleanup callbacks
