---
name: myfy-patterns
description: Core myfy patterns and conventions for building applications. Use when working with myfy.core, Application, WebModule, DataModule, FrontendModule, TasksModule, or @route decorators.
---

# myfy Framework Patterns

You are assisting a developer building an application with the myfy Python framework.

## Core Principles

1. **Opinionated, not rigid** - Strong defaults, full configurability
2. **Modular by design** - Features are modules (web, data, tasks, frontend)
3. **Type-safe DI** - Constructor injection with compile-time validation
4. **Async-native** - Built on ASGI and AnyIO with contextvars
5. **Zero-config defaults** - Convention over configuration

## Imports

Always import from the public API:

```python
# Core
from myfy.core import Application, provider, SINGLETON, REQUEST, TASK
from myfy.core import BaseSettings, BaseModule

# Web
from myfy.web import WebModule, route, Query, abort, errors
from myfy.web import Authenticated, Anonymous, AuthModule

# Data
from myfy.data import DataModule, AsyncSession

# Tasks
from myfy.tasks import TasksModule, task, TaskContext

# Frontend
from myfy.frontend import FrontendModule, render_template

# User
from myfy.user import UserModule
```

## Application Structure

```python
from myfy.core import Application
from myfy.web import WebModule, route
from myfy.data import DataModule

app = Application(
    settings_class=AppSettings,  # Optional custom settings
    auto_discover=False,          # Disable auto-discovery for explicit control
)

# Add modules in dependency order
app.add_module(DataModule())
app.add_module(WebModule())
```

## Module Categories

| Module | Package | Purpose |
|--------|---------|---------|
| WebModule | myfy-web | HTTP routing, ASGI, FastAPI-like decorators |
| DataModule | myfy-data | SQLAlchemy async, migrations, sessions |
| FrontendModule | myfy-frontend | Jinja2, Tailwind 4, DaisyUI 5, Vite |
| TasksModule | myfy-tasks | Background jobs, SQL-based task queue |
| UserModule | myfy-user | Auth, OAuth, user management |
| CliModule | myfy-commands | Custom CLI commands |

## Key Conventions

1. **File naming**: `app.py`, `main.py`, or `application.py` for entry point
2. **Settings**: Extend `BaseSettings` from `myfy.core`
3. **Routes**: Use global `route` decorator from `myfy.web`
4. **Providers**: Use `@provider(scope=...)` decorator from `myfy.core`
5. **Tasks**: Use `@task` decorator for background jobs

## Common Patterns

### Creating a Route with DI

```python
from myfy.web import route
from myfy.data import AsyncSession

@route.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession) -> dict:
    # session is auto-injected (REQUEST scope)
    result = await session.execute(select(User).where(User.id == user_id))
    return {"user": result.scalar_one_or_none()}
```

### Creating a Provider

```python
from myfy.core import provider, SINGLETON

@provider(scope=SINGLETON)
def email_service(settings: AppSettings) -> EmailService:
    return EmailService(api_key=settings.email_api_key)
```

### Settings Class

```python
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from myfy.core import BaseSettings

class AppSettings(BaseSettings):
    app_name: str = Field(default="my-app")
    debug: bool = Field(default=False)
    database_url: str = Field(default="sqlite+aiosqlite:///./app.db")

    model_config = SettingsConfigDict(
        env_prefix="MYFY_",
        env_file=".env",
    )
```

## Error Handling

```python
from myfy.web import abort, errors

# Quick abort
abort(404, "User not found")

# Typed errors
raise errors.NotFound("User not found")
raise errors.BadRequest("Invalid email", field="email")
```

## When Generating Code

Always:
- Use type hints for all function parameters and return types
- Use async/await for all handlers
- Import from `myfy.*` not internal modules
- Follow existing project structure
- Use Pydantic models for request/response bodies
