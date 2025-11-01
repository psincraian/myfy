# myfy

**Build Python applications that feel like they wrote themselves.**

---

## Why Another Framework?

You've built enough Python apps to know: FastAPI is brilliant for APIs but barebones for real apps. Django's too heavy and too coupled. Flask feels like duct tape.

What if you could have:
- **FastAPI's ergonomics** (decorators, type hints, async-first)
- **Enterprise-grade architecture** (DI container, module system, lifecycle)
- **Sensible defaults** (no config files until you need them)

myfy is that framework. Opinionated where it matters, flexible everywhere else.

---

## Three Things That Make myfy Different

### 1. **Modules That Actually Work**

Not "blueprint" modules. Real, composable modules with their own lifecycle:

```python
class DataModule(BaseModule):
    async def start(self):
        await self.db.connect()

    async def stop(self):
        await self.db.disconnect()

app.add_module(DataModule())
app.add_module(WebModule())
# Modules start in order, stop in reverse
# Add community modules via pip install myfy-auth
```

### 2. **Dependency Injection Without Magic**

Type-based DI that's fast (zero reflection on hot path) and safe (compile-time validation):

```python
@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return Database(settings.db_url)

@route.post("/users")
async def create_user(body: CreateUserDTO, db: Database):
    # db automatically injected, body automatically parsed
    return await db.create_user(body)
```

No decorating classes. No magic. Just functions and types.

### 3. **Defaults That Make Sense**

One file. No config. Just run:

```python
from myfy.core import Application
from myfy.web import route, WebModule

@route.get("/hello/{name}")
async def hello(name: str) -> dict:
    return {"message": f"Hello {name}!"}

app = Application(auto_discover=False)
app.add_module(WebModule())
```

Save as `app.py`, run `uv run myfy run`. That's it.

---

## 60-Second Example

**Build a real API with DI, validation, and clean architecture:**

```python
from myfy.core import Application, provider, SINGLETON, BaseSettings
from myfy.web import route, WebModule
from pydantic import Field

# 1. Settings (auto-loads from .env)
class Settings(BaseSettings):
    app_name: str = Field(default="My App")
    api_key: str

# 2. Services (constructor-injected)
class UserService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def greet(self, name: str) -> str:
        return f"Hello {name} from {self.settings.app_name}!"

@provider(scope=SINGLETON)
def user_service(settings: Settings) -> UserService:
    return UserService(settings)

# 3. Routes (DI + path params + type conversion)
@route.get("/greet/{name}")
async def greet_user(name: str, service: UserService) -> dict:
    return {"message": service.greet(name)}

# 4. Run
app = Application(settings_class=Settings, auto_discover=False)
app.add_module(WebModule())

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
```

**Run it:**
```bash
echo "API_KEY=secret123" > .env
uv run myfy run
```

Visit http://127.0.0.1:8000/greet/World

**That's it.** Settings, DI, validation, routing, and ASGI server. In 30 lines.

---

## Install + Quickstart

### Installation

```bash
# Install with uv (recommended)
uv pip install myfy-core myfy-web myfy-cli

# Or with pip
pip install myfy-core myfy-web myfy-cli
```

### Create Your First App

```python
# app.py
from myfy.core import Application
from myfy.web import route, WebModule

@route.get("/")
async def home() -> dict:
    return {"message": "Welcome to myfy!"}

app = Application(auto_discover=False)
app.add_module(WebModule())

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
```

### Run It

```bash
uv run myfy run
# Server running at http://127.0.0.1:8000
```

### Next Steps

- **[Full Tutorial](https://psincraian.github.io/myfy/getting-started/tutorial/)** - Build a complete app step-by-step
- **[Core Concepts](https://psincraian.github.io/myfy/core-concepts/dependency-injection/)** - Understand DI, modules, and lifecycle
- **[Examples](examples/)** - See working applications

---

## What You Get

### Clean Module System
```python
app.add_module(WebModule())      # HTTP routing
app.add_module(DataModule())     # Database
app.add_module(AuthModule())     # JWT, sessions
# Modules have lifecycle, DI integration, and clean boundaries
```

### Type-Safe DI
```python
@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return Database(settings.db_url)

@provider(scope=REQUEST)
def unit_of_work(db: Database) -> UnitOfWork:
    return UnitOfWork(db)
```

**Scopes:** `SINGLETON` (one per app), `REQUEST` (one per HTTP request), `TASK` (one per background task)

**Compile-time checks:** Cycle detection, missing providers, scope mismatches

### FastAPI-Style Routes
```python
@route.get("/users/{user_id}")
async def get_user(user_id: int, db: Database) -> User:
    return await db.get_user(user_id)

@route.post("/users")
async def create_user(body: CreateUserDTO, db: Database) -> User:
    return await db.create_user(body)
```

Mix DI services with path params and body parsing. Type hints do the work.

### Environment-Based Configuration
```python
class Settings(BaseSettings):
    db_url: str
    debug: bool = False

# MYFY_PROFILE=dev → loads .env.dev
# MYFY_PROFILE=prod → loads .env.prod
```

### CLI Tools
```bash
uv run myfy run       # Start server (auto-reload in dev)
uv run myfy routes    # List all routes
uv run myfy modules   # Show loaded modules
uv run myfy doctor    # Validate configuration
```

---

## Architecture

### Namespace Package Structure

```
myfy/
├── packages/
│   ├── myfy-core/      # DI, config, lifecycle, kernel
│   ├── myfy-web/       # ASGI, routing, HTTP handlers
│   ├── myfy-cli/       # CLI tools (run, routes, etc.)
│   └── myfy/           # Meta-package (installs all)
└── examples/
    └── hello/          # Working example app
```

Install what you need:
```bash
pip install myfy-core              # Just the kernel
pip install myfy-core myfy-web     # Add web support
pip install myfy                   # Everything
```

### How It Works

**Compile-time DI resolution:**
1. Parse type hints at startup (once)
2. Build injection plans per handler
3. Cache plans in dict (O(1) lookup)
4. Request time = dict lookup + function call

**No reflection during requests.** All analysis happens at startup.

**Request scopes via contextvars:**
```python
@route.get("/data")
async def handler(service: RequestScopedService):
    # service created once per request, shared across DI calls
    # automatically cleaned up when request completes
    pass
```

---

## Why myfy?

### Opinionated, Not Rigid
Strong defaults (JSON, auto-DI, ASGI) but swap anything (router, serializer, container).

### Pythonic, Not Ceremonial
Type hints, decorators, async/await. No XML. No boilerplate classes.

### Modular by Design
Tiny kernel (`myfy-core`). Add modules as you need them. Build your own.

### Typed, Validated, Safe
Pydantic everywhere. Compile-time DI validation. Type-safe routing.

### Zero Heavy Reflection on Hot Path
All introspection at startup. Hot path is just function calls.

---

## Principles

Read our full design philosophy in **[PRINCIPLES.md](PRINCIPLES.md)**.

Highlights:
- **Defaults by default** - Zero config to start, infinite config to scale
- **Sugar with substance** - Decorators compile to explicit code
- **Predictable lifecycle** - Clear init → start → stop, deterministic order
- **Replace anything** - Swap routers, ORMs, DI providers without breaking core
- **Profiles over env chaos** - dev/test/prod with layered config
- **Dependency injection with scopes** - Singleton, request, task

---

## Roadmap

Future modules (following the same architecture):
- **myfy-sqlalchemy** - ORM integration, migrations
- **myfy-auth** - JWT, OAuth, session management
- **myfy-telemetry** - Structured logging, tracing, metrics
- **myfy-tasks** - Background jobs, scheduling
- **myfy-cache** - Redis, in-memory caching
- **myfy-events** - Event bus, pub/sub

All as separate `myfy-*` packages, installable independently.

---

## Documentation

**[📖 Read the Full Documentation →](https://psincraian.github.io/myfy/)**

- **[Getting Started](https://psincraian.github.io/myfy/getting-started/installation/)** - Installation, tutorial, quick reference
- **[Core Concepts](https://psincraian.github.io/myfy/core-concepts/dependency-injection/)** - DI, modules, configuration deep dive
- **[Guides](https://psincraian.github.io/myfy/guides/building-modules/)** - Building modules, testing, deployment
- **[API Reference](https://psincraian.github.io/myfy/api-reference/core/)** - Complete API docs

---

## Examples

See `examples/hello/` for a complete working application:
- Settings with Pydantic
- Singleton and request-scoped services
- Multiple route types (GET, POST)
- Path parameters and body parsing
- Dependency injection in handlers

**Run it:**
```bash
cd examples/hello
uv run --with ../../packages/myfy-core --with ../../packages/myfy-web python app.py
```

---

## Development

```bash
# Clone the repo
git clone <repo-url>
cd myfy

# Install workspace
uv sync

# Run the example
uv run python examples/hello/app.py

# Test imports
uv run python -c "from myfy.core import Application; print('✓ Works!')"
```

---

## Acknowledgments

Inspired by:
- **FastAPI** - Ergonomic decorators, type-driven APIs
- **Django** - Batteries-included philosophy, module system concepts
- **Starlette** - Clean ASGI foundation

Built with:
- **Pydantic** - Settings & validation
- **Starlette** - ASGI toolkit
- **uvicorn** - ASGI server
- **typer** - CLI framework

---

## License

MIT
