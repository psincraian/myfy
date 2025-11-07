# myfy

**Build Python applications with FastAPI's ergonomics and enterprise-grade architecture.**

A modern Python framework combining type-safe dependency injection, modular architecture, and sensible defaults—all in a lightweight, async-first design.

---

## Quick Start

### Installation

```bash
# Install with uv (recommended)
uv pip install myfy-core myfy-web myfy-frontend myfy-cli

# Or with pip
pip install myfy-core myfy-web myfy-frontend myfy-cli
```

### Hello World

```python
# app.py
from myfy.core import Application
from myfy.web import route, WebModule
from myfy.frontend import FrontendModule

@route.get("/api/hello/{name}")
async def hello(name: str) -> dict:
    return {"message": f"Hello {name}!"}

app = Application(auto_discover=False)
app.add_module(WebModule())
app.add_module(FrontendModule())
```

**Run it:**
```bash
uv run myfy run
# API: http://127.0.0.1:8000/api/hello/World
# Frontend: http://127.0.0.1:8000
```

---

## Key Features

- **Type-Safe Dependency Injection** - Constructor injection with compile-time validation
- **Modular Architecture** - Composable modules with lifecycle management
- **FastAPI-Style Routes** - Decorators, type hints, and async/await
- **Zero Config** - Sensible defaults, configure only what you need
- **Profile-Based Settings** - Environment-aware configuration (dev/test/prod)

---

## Documentation

**[📖 Full Documentation at myfy.dev →](https://myfy.dev)**

- [Getting Started](https://myfy.dev/getting-started/installation/) - Installation and tutorial
- [Core Concepts](https://myfy.dev/core-concepts/dependency-injection/) - DI, modules, and lifecycle
- [Guides](https://myfy.dev/guides/building-modules/) - Building modules and deployment
- [API Reference](https://myfy.dev/api-reference/core/) - Complete API docs

---

## Learn More

- [Examples](examples/) - Working applications in this repo
- [PRINCIPLES.md](PRINCIPLES.md) - Design philosophy and architecture decisions

---

## License

MIT
