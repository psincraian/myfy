# myfy-data

Database/ORM module for myfy with async SQLAlchemy and REQUEST-scoped sessions.

## Overview

`myfy-data` provides seamless database integration built on SQLAlchemy 2.0+, with async/await support, automatic session management, and deep integration with myfy's dependency injection system.

## Installation

```bash
# Install data module
pip install myfy-data

# Or with uv
uv pip install myfy-data
```

**Dependencies:**

- `myfy-core` - Core framework
- `sqlalchemy[asyncio]` - SQLAlchemy with async support
- `aiosqlite` - Async SQLite driver (default)
- `alembic` - Database migrations

## Key Features

### Async SQLAlchemy 2.0+

Modern async/await database operations:

```python
from myfy.data import DataModule
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

@route.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession) -> dict:
    # session automatically injected
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    return {"id": user.id, "name": user.name}
```

### REQUEST-Scoped Sessions

Each HTTP request automatically gets its own database session:

```python
@route.post("/users")
async def create_user(body: CreateUserDTO, session: AsyncSession) -> User:
    user = User(**body.dict())
    session.add(user)
    await session.commit()
    return user
    # session automatically closed after response
```

### Connection Pooling

Production-ready connection management with configurable pooling:

```python
from myfy.data import DatabaseSettings

settings = DatabaseSettings(
    database_url="postgresql+asyncpg://user:pass@localhost/db",
    pool_size=10,
    max_overflow=20,
    pool_timeout=30.0
)
```

### Zero Configuration

Works out-of-the-box with SQLite:

```python
from myfy.core import Application
from myfy.data import DataModule

app = Application(auto_discover=False)
app.add_module(DataModule())  # Uses SQLite by default!
```

### Auto Table Creation (Development)

Automatically create tables from your models in development:

```python
from myfy.data import DataModule, Base
from sqlalchemy import Column, Integer, String

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

app.add_module(DataModule(
    auto_create_tables=True,  # Creates tables on startup
    metadata=Base.metadata,
))
```

**Note**: `auto_create_tables` is blocked in production environments. Use Alembic migrations for production deployments.

## Quick Start

### Basic Application

```python
from myfy.core import Application
from myfy.data import DataModule, Base
from myfy.web import route, WebModule
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from starlette.exceptions import HTTPException

# Define model
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(100))

# Define routes
@route.get("/users")
async def list_users(session: AsyncSession) -> list[dict]:
    result = await session.execute(select(User))
    users = result.scalars().all()
    return [{"id": u.id, "name": u.name, "email": u.email} for u in users]

@route.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession) -> dict:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)
    return {"id": user.id, "name": user.name, "email": user.email}

# Create application with auto table creation (development only)
app = Application(auto_discover=False)
app.add_module(DataModule(
    auto_create_tables=True,  # Auto-creates tables on startup
    metadata=Base.metadata,
))
app.add_module(WebModule())

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
```

Run with:
```bash
uv run myfy run
```

### PostgreSQL Application

```python
from myfy.core import Application
from myfy.data import DataModule, DatabaseSettings

# Configure PostgreSQL
settings = DatabaseSettings(
    database_url="postgresql+asyncpg://user:password@localhost/mydb"
)

app = Application(auto_discover=False)
app.add_module(DataModule(settings=settings))
app.add_module(WebModule())
```

## Database Configuration

### DatabaseSettings

Configure database connection and pooling:

```python
from myfy.data import DatabaseSettings

settings = DatabaseSettings(
    # Connection
    database_url="postgresql+asyncpg://user:pass@localhost/db",

    # Connection Pool
    pool_size=5,              # Number of persistent connections
    max_overflow=10,          # Additional connections allowed
    pool_timeout=30.0,        # Timeout for getting connection
    pool_recycle=3600,        # Recycle connections after 1 hour
    pool_pre_ping=True,       # Test connections before use

    # Debugging
    echo=False,               # Log SQL statements
    echo_pool=False,          # Log pool checkout/checkin

    # SQLite-specific
    sqlite_check_same_thread=False  # Required for async SQLite
)
```

### Environment Variables

Configure via environment variables with `MYFY_DATA_` prefix:

```bash
# .env
MYFY_DATA_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
MYFY_DATA_POOL_SIZE=10
MYFY_DATA_MAX_OVERFLOW=20
MYFY_DATA_ECHO=true
```

### Supported Databases

**SQLite** (default):
```python
database_url="sqlite+aiosqlite:///./myfy.db"  # File
database_url="sqlite+aiosqlite:///:memory:"   # In-memory
```

**PostgreSQL**:
```python
database_url="postgresql+asyncpg://user:pass@localhost/db"
```

**MySQL**:
```python
database_url="mysql+aiomysql://user:pass@localhost/db"
```

**Note**: Install appropriate async driver:
- SQLite: `aiosqlite` (included)
- PostgreSQL: `asyncpg`
- MySQL: `aiomysql`

## Models

### Defining Models

Use SQLAlchemy's declarative base:

```python
from myfy.data import Base, Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    age = Column(Integer)
```

### Relationships

Define relationships between models:

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    user_id = Column(Integer, ForeignKey("users.id"))

    # Relationship
    user = relationship("User", back_populates="posts")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    # Relationship
    posts = relationship("Post", back_populates="user")
```

## CRUD Operations

### Create

```python
@route.post("/users")
async def create_user(body: CreateUserDTO, session: AsyncSession) -> dict:
    user = User(name=body.name, email=body.email)
    session.add(user)
    await session.commit()
    await session.refresh(user)  # Get generated ID
    return {"id": user.id, "name": user.name}
```

### Read

```python
from sqlalchemy import select

@route.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession) -> dict:
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)
    return {"id": user.id, "name": user.name}
```

### Update

```python
@route.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserDTO,
    session: AsyncSession
) -> dict:
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)

    user.name = body.name
    user.email = body.email
    await session.commit()
    return {"id": user.id, "name": user.name}
```

### Delete

```python
@route.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, session: AsyncSession) -> None:
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)

    await session.delete(user)
    await session.commit()
```

## Queries

### Filtering

```python
from sqlalchemy import select, and_, or_

# Simple filter
result = await session.execute(
    select(User).where(User.age >= 18)
)

# Multiple conditions (AND)
result = await session.execute(
    select(User).where(
        and_(
            User.age >= 18,
            User.email.like("%@example.com")
        )
    )
)

# OR conditions
result = await session.execute(
    select(User).where(
        or_(
            User.age < 18,
            User.age > 65
        )
    )
)
```

### Ordering

```python
from sqlalchemy import desc

# Ascending
result = await session.execute(
    select(User).order_by(User.name)
)

# Descending
result = await session.execute(
    select(User).order_by(desc(User.created_at))
)
```

### Pagination

```python
@route.get("/users")
async def list_users(
    page: int = 1,
    per_page: int = 20,
    session: AsyncSession = None
) -> dict:
    offset = (page - 1) * per_page

    result = await session.execute(
        select(User)
        .offset(offset)
        .limit(per_page)
    )
    users = result.scalars().all()

    # Get total count
    total_result = await session.execute(
        select(func.count()).select_from(User)
    )
    total = total_result.scalar()

    return {
        "items": users,
        "page": page,
        "per_page": per_page,
        "total": total
    }
```

### Joins

```python
from sqlalchemy import join

# Explicit join
result = await session.execute(
    select(User, Post)
    .join(Post, User.id == Post.user_id)
    .where(Post.published == True)
)

# Using relationship
result = await session.execute(
    select(User)
    .join(User.posts)
    .where(Post.published == True)
)
```

## Transactions

### Explicit Transactions

```python
@route.post("/transfer")
async def transfer_money(
    from_id: int,
    to_id: int,
    amount: float,
    session: AsyncSession
) -> dict:
    async with session.begin_nested():
        # Deduct from sender
        sender = await session.get(Account, from_id)
        sender.balance -= amount

        # Add to receiver
        receiver = await session.get(Account, to_id)
        receiver.balance += amount

        # Commit happens automatically on context exit

    await session.commit()
    return {"status": "success"}
```

### Rollback on Error

```python
@route.post("/create-user-with-profile")
async def create_user_with_profile(
    body: CreateUserDTO,
    session: AsyncSession
) -> dict:
    try:
        # Create user
        user = User(**body.dict())
        session.add(user)
        await session.flush()  # Get user.id without committing

        # Create profile
        profile = UserProfile(user_id=user.id, bio="...")
        session.add(profile)

        await session.commit()
        return {"id": user.id}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
```

## Migrations

### Initialize Alembic

```python
from myfy.data import MigrationManager

manager = MigrationManager()
manager.init()  # Creates alembic.ini and alembic/ directory
```

### Create Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add users table"

# Or use MigrationManager
manager = MigrationManager()
manager.revision("Add users table", autogenerate=True)
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Or use MigrationManager
manager = MigrationManager()
manager.upgrade()
```

### Configure Alembic

Update `alembic/env.py` to use your models:

```python
from myfy.data import data_module, Base
from myapp.models import User, Post  # Import all models

# Set target_metadata to your Base
target_metadata = Base.metadata

# Get database URL from settings
config.set_main_option(
    "sqlalchemy.url",
    data_module._settings.database_url
)
```

## Session Management

### Manual Session Creation

```python
from myfy.data import SessionFactory

async def some_background_task(session_factory: SessionFactory):
    async with session_factory.session_context() as session:
        # Use session
        user = User(name="Alice")
        session.add(user)
        # Automatically commits on exit
```

### Direct Engine Access

```python
from myfy.data import data_module

engine = data_module.get_engine()

async with engine.connect() as conn:
    result = await conn.execute("SELECT 1")
    print(result.scalar())
```

## Best Practices

### Use REQUEST-Scoped Sessions

```python
# ✓ Good - Automatic session management
@route.get("/users")
async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User))
    return result.scalars().all()

# ✗ Bad - Manual session creation in routes
@route.get("/users")
async def list_users(session_factory: SessionFactory) -> list[User]:
    async with session_factory.session_context() as session:
        result = await session.execute(select(User))
        return result.scalars().all()
```

### Always Use async/await

```python
# ✓ Good - Async operations
result = await session.execute(select(User))
users = result.scalars().all()

# ✗ Bad - Synchronous operations
# session.query(User).all()  # Don't use sync query() API
```

### Use Type Hints

```python
# ✓ Good - Type hints for IDE support
from sqlalchemy.ext.asyncio import AsyncSession

@route.get("/users")
async def list_users(session: AsyncSession) -> list[dict]:
    ...

# ✗ Bad - No type hints
@route.get("/users")
async def list_users(session):
    ...
```

### Initialize Tables on Startup

```python
# ✓ Good - Use auto_create_tables for development
app.add_module(DataModule(
    auto_create_tables=True,
    metadata=Base.metadata,
))

# ✓ Good - Use Alembic migrations for production
# alembic upgrade head

# ✗ Bad - Manual table creation scripts
```

### Use Migrations for Schema Changes

```python
# ✓ Good - Version control schema changes
# alembic revision --autogenerate -m "Add email column"
# alembic upgrade head

# ✗ Bad - Manual schema modifications
# ALTER TABLE users ADD COLUMN email VARCHAR(100);
```

## Common Patterns

### Repository Pattern

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[User]:
        result = await self.session.execute(select(User))
        return result.scalars().all()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

@route.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession) -> dict:
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return {"id": user.id, "name": user.name}
```

### Service Layer

```python
from myfy.core import provider, SINGLETON

class UserService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_user(self, user_id: int, session: AsyncSession) -> User:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user

@provider(scope=SINGLETON)
def user_service(settings: Settings) -> UserService:
    return UserService(settings)

@route.get("/users/{user_id}")
async def get_user(
    user_id: int,
    service: UserService,
    session: AsyncSession
) -> dict:
    user = await service.get_user(user_id, session)
    return {"id": user.id, "name": user.name}
```

## Examples

Complete example in [`examples/frontend-demo/`](../../examples/frontend-demo/) with:
- Todo CRUD operations
- SQLAlchemy models
- REQUEST-scoped sessions
- Database initialization

## API Reference

### DataModule

```python
class DataModule:
    def __init__(
        self,
        settings: DatabaseSettings | None = None,
        auto_create_tables: bool = False,
        metadata: MetaData | None = None,
    )
    """
    Args:
        settings: Custom database settings (defaults to environment)
        auto_create_tables: Create tables on startup (dev/test only)
        metadata: SQLAlchemy MetaData for auto_create_tables
    """

    @property
    def name(self) -> str  # Returns "data"

    @property
    def requires(self) -> list[type]  # Returns []

    @property
    def provides(self) -> list[type]  # Returns [IDataProvider]

    def configure(self, container: Container) -> None
    def extend(self, container: Container) -> None
    def finalize(self, container: Container) -> None
    async def start(self) -> None  # Creates tables if auto_create_tables=True
    async def stop(self) -> None

    def get_engine(self) -> AsyncEngine
    def get_session_factory(self) -> SessionFactory
```

### DatabaseSettings

```python
class DatabaseSettings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./myfy.db"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: float = 30.0
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False
    echo_pool: bool = False
    sqlite_check_same_thread: bool = False
    environment: str = "development"  # "development", "test", or "production"
```

Environment variables use `MYFY_DATA_` prefix (e.g., `MYFY_DATA_ENVIRONMENT=production`).

### SessionFactory

```python
class SessionFactory:
    def create_session(self) -> AsyncSession

    @asynccontextmanager
    async def session_context(self) -> AsyncIterator[AsyncSession]
```

## Next Steps

- **Add Authentication**: Install `myfy-auth` for user authentication
- **Add Testing**: Learn how to test database operations
- **Performance**: Optimize queries with indexes and eager loading
- **Monitoring**: Add query logging and performance tracking
