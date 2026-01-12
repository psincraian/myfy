---
name: data-module
description: myfy DataModule for database access with async SQLAlchemy. Use when working with DataModule, AsyncSession, database connections, connection pooling, migrations, or SQLAlchemy models.
---

# DataModule - Database Access

DataModule provides async SQLAlchemy integration with connection pooling and REQUEST-scoped sessions.

## Quick Start

```python
from myfy.core import Application
from myfy.data import DataModule, AsyncSession
from myfy.web import route

app = Application()
app.add_module(DataModule())

@route.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession) -> dict:
    # session is auto-injected (REQUEST scope)
    result = await session.execute(select(User).where(User.id == user_id))
    return {"user": result.scalar_one_or_none()}
```

## Configuration

Environment variables use the `MYFY_DATA_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `MYFY_DATA_DATABASE_URL` | `sqlite+aiosqlite:///./myfy.db` | Database connection URL |
| `MYFY_DATA_POOL_SIZE` | `5` | Number of connections in pool |
| `MYFY_DATA_MAX_OVERFLOW` | `10` | Extra connections beyond pool_size |
| `MYFY_DATA_POOL_TIMEOUT` | `30.0` | Seconds to wait for connection |
| `MYFY_DATA_POOL_RECYCLE` | `3600` | Seconds before connection recycled |
| `MYFY_DATA_POOL_PRE_PING` | `True` | Test connections before use |
| `MYFY_DATA_ECHO` | `False` | Log all SQL statements |
| `MYFY_DATA_ENVIRONMENT` | `development` | Environment (blocks auto_create in production) |

## Supported Databases

```python
# SQLite (development)
MYFY_DATA_DATABASE_URL="sqlite+aiosqlite:///./app.db"

# PostgreSQL (production)
MYFY_DATA_DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db"

# MySQL
MYFY_DATA_DATABASE_URL="mysql+aiomysql://user:pass@localhost/db"
```

## Defining Models

```python
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))
```

## Auto-Create Tables (Development Only)

```python
from myfy.data import DataModule

app.add_module(DataModule(
    auto_create_tables=True,  # Only in development!
    metadata=Base.metadata,
))
```

Raises `AutoCreateTablesProductionError` if `MYFY_DATA_ENVIRONMENT=production`.

## Using Sessions in Routes

Sessions are REQUEST-scoped (one per HTTP request):

```python
from myfy.data import AsyncSession
from sqlalchemy import select

@route.get("/users")
async def list_users(session: AsyncSession) -> list[dict]:
    result = await session.execute(select(User))
    users = result.scalars().all()
    return [{"id": u.id, "name": u.name} for u in users]

@route.post("/users", status_code=201)
async def create_user(body: UserCreate, session: AsyncSession) -> dict:
    user = User(**body.model_dump())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return {"id": user.id}
```

## Using Sessions in Providers

```python
from myfy.core import provider, REQUEST
from myfy.data import AsyncSession

@provider(scope=REQUEST)
def user_repository(session: AsyncSession) -> UserRepository:
    return UserRepository(session)
```

## Transactions

Sessions auto-commit on success, rollback on exception:

```python
@route.post("/transfer")
async def transfer(body: TransferRequest, session: AsyncSession) -> dict:
    # Both updates succeed or both rollback
    sender = await session.get(Account, body.sender_id)
    receiver = await session.get(Account, body.receiver_id)

    sender.balance -= body.amount
    receiver.balance += body.amount

    await session.commit()  # Explicit commit
    return {"success": True}
```

## Using SessionFactory Directly

For background jobs or manual session management:

```python
from myfy.data import SessionFactory

@provider(scope=SINGLETON)
def background_service(factory: SessionFactory) -> BackgroundService:
    return BackgroundService(factory)

class BackgroundService:
    async def process(self):
        async with self.factory.session_context() as session:
            # Manual session management
            await self.do_work(session)
```

## Alembic Migrations

Initialize Alembic:

```bash
alembic init migrations
```

Configure `alembic.ini`:

```ini
sqlalchemy.url = driver://user:pass@localhost/dbname
```

Configure `migrations/env.py`:

```python
from app.models import Base
target_metadata = Base.metadata
```

Create and run migrations:

```bash
alembic revision --autogenerate -m "Add users table"
alembic upgrade head
```

## Best Practices

1. **Use async drivers** - `asyncpg` for PostgreSQL, `aiosqlite` for SQLite
2. **Never share sessions** - Sessions are REQUEST-scoped for a reason
3. **Use migrations in production** - Don't use `auto_create_tables` in production
4. **Configure pool size** - Match to expected concurrent connections
5. **Enable pool_pre_ping** - Detects stale connections before use
6. **Use transactions** - Group related operations in a single commit
