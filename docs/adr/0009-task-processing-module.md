# ADR-0009: Task Processing Module

## Status

Proposed

## Context

The myfy framework needs asynchronous task processing capabilities for:

- **Background jobs**: Email sending, file processing, data exports
- **Offloading work**: Long-running operations that should not block HTTP requests
- **Reliability**: Task persistence, retries, and failure handling

Traditional solutions like Celery require external message brokers (Redis, RabbitMQ), adding operational complexity. For many applications, a simpler SQL-based queue provides sufficient functionality with reduced infrastructure requirements.

### Design Constraints

1. Use existing `myfy-data` package for database access (dependency)
2. Leverage existing `TASK` scope in DI system (`/packages/myfy-core/myfy/core/di/scopes.py`)
3. Follow module lifecycle phases (ADR-0005)
4. Use polling-based SQL queue (no external broker)
5. Separate worker processes only (production-grade)
6. Focus on async task dispatch initially (no scheduled/cron tasks)

### Comparison with Existing Solutions

| Feature | Celery | Dramatiq | myfy-tasks |
|---------|--------|----------|------------|
| Broker | Redis/RabbitMQ | Redis/RabbitMQ | SQL (any database) |
| Setup complexity | High | Medium | Low |
| Throughput | High | High | Medium |
| DI integration | Manual | Manual | Native (TASK scope) |
| Type safety | Limited | Limited | Full (ParamSpec) |

## Decision

We will implement a **myfy-tasks** module that provides SQL-based asynchronous task processing.

### 1. Task Definition API

```python
from myfy.tasks import task, TaskContext

@task
async def send_email(
    # Task arguments (serialized to queue)
    to: str,
    subject: str,
    body: str,
    # DI dependencies (resolved at execution)
    email_service: EmailService,
) -> None:
    await email_service.send(to, subject, body)

@task
async def process_batch(
    items: list[str],
    ctx: TaskContext,           # Auto-injected for progress
    processor: DataProcessor,   # DI dependency
) -> int:
    for i, item in enumerate(items):
        await processor.process(item)
        await ctx.update_progress(current=i + 1, total=len(items))
    return len(items)
```

### 2. Task Dispatch

```python
# Simple dispatch
task_id = await send_email.send(
    to="user@example.com",
    subject="Hello",
    body="World",
)

# With options (underscore prefix)
task_id = await send_email.send(
    to="user@example.com",
    _priority=10,
    _max_retries=5,
    _delay=60,
)

# Result retrieval
result = await send_email.get_result(task_id)
```

### 3. Database Schema

```sql
CREATE TABLE myfy_tasks (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    args JSON NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    scheduled_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    error_traceback TEXT,
    result JSON,
    worker_id VARCHAR(255),
    progress_current INTEGER,
    progress_total INTEGER,
    progress_message VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_myfy_tasks_status_scheduled ON myfy_tasks (status, scheduled_at);
```

### 4. Worker Architecture

Workers run as separate processes:

```bash
myfy tasks worker --concurrency 4
```

Worker loop:
1. Poll database for pending tasks (`SELECT ... FOR UPDATE SKIP LOCKED`)
2. Claim tasks by setting `status='running'` and `worker_id`
3. Initialize TASK scope via `ScopeContext.init_task_scope()`
4. Resolve DI dependencies and execute task
5. Mark task completed/failed
6. Clear TASK scope via `ScopeContext.clear_task_bag()`
7. Handle retries with configurable delay
8. Graceful shutdown on SIGTERM/SIGINT

### 5. Module Integration

```python
class TasksModule:
    @property
    def requires(self) -> list[type]:
        return [DataModule]

    @property
    def provides(self) -> list[type]:
        return [ITaskProvider]
```

### 6. DX Design Principles

1. **Simple API**: `send()` instead of `send_async()` - myfy is async-native
2. **Type safety**: `ParamSpec` preserves function signatures for IDE autocomplete
3. **DI consistency**: Same pattern as web handlers (primitives = args, complex = injected)
4. **TaskContext**: For progress reporting and cancellation checks
5. **TaskResult[T]**: Typed result retrieval

## Consequences

### Positive

1. **Simple infrastructure**: No Redis/RabbitMQ required
2. **Database-agnostic**: Works with SQLite, PostgreSQL, MySQL
3. **Integrated DI**: Uses existing TASK scope, same patterns as web handlers
4. **Type-safe**: Full typing with ParamSpec for IDE support
5. **Observable**: Tasks stored in database for debugging/monitoring
6. **Familiar patterns**: Similar API to Celery/Dramatiq
7. **Progress tracking**: Built-in support via TaskContext

### Neutral

1. **Polling overhead**: Workers poll database (configurable interval)
2. **Learning curve**: Developers need to understand DI injection in tasks

### Negative

1. **Lower throughput**: SQL queue slower than dedicated brokers for high-volume
2. **Database load**: Heavy task volumes increase database writes
3. **Not distributed**: Workers must share database access
4. **No real-time**: Polling introduces latency (configurable, default 1s)

## Alternatives Considered

### 1. Redis/RabbitMQ Broker (Celery-style)

**Rejected because:**
- Adds infrastructure complexity
- Requires additional operational knowledge
- Overkill for many applications
- Can be added later as alternative backend

### 2. PostgreSQL LISTEN/NOTIFY

**Rejected because:**
- PostgreSQL-specific
- More complex implementation
- Polling is simpler and database-agnostic
- Can be added as optimization later

### 3. In-Process Task Execution

**Rejected because:**
- Not production-grade
- Tasks lost on process crash
- No horizontal scaling
- Blocks web workers

### 4. Eager Mode (Sync Execution for Tests)

**Rejected because:**
- User preference: separate worker processes only
- Tests should use real worker behavior
- Simplifies implementation

## References

- [ADR-0003](./0003-dependency-injection-with-scopes.md) - DI with scopes (TASK scope)
- [ADR-0005](./0005-module-extension-and-lifecycle-phases.md) - Module lifecycle
- [Celery](https://docs.celeryproject.org/) - Task queue inspiration
- [Dramatiq](https://dramatiq.io/) - API inspiration
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - Database access
