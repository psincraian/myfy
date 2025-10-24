# Hello World Example

A simple myfy application demonstrating core features.

## Features Demonstrated

- **Configuration**: Type-safe settings with Pydantic
- **Dependency Injection**: Constructor injection with `@provider`
- **Scopes**: Singleton and request-scoped services
- **Web Routes**: FastAPI-like routing with `@route` decorators
- **Auto-injection**: Path params, request body, and DI services

## Running

From the repo root:

```bash
# Using the CLI (from examples/hello/)
cd examples/hello
uv run --package myfy-cli myfy run

# Or directly with Python
uv run --package examples/hello python app.py
```

## Try It

Once running, open http://127.0.0.1:8000 or try:

```bash
# List routes
uv run --package myfy-cli myfy routes

# Root endpoint
curl http://127.0.0.1:8000/

# Greet endpoint (demonstrates singleton DI)
curl http://127.0.0.1:8000/greet/World

# Counter endpoint (demonstrates request scope)
curl http://127.0.0.1:8000/count

# Echo endpoint (demonstrates POST body parsing)
curl -X POST http://127.0.0.1:8000/echo \
  -H "Content-Type: application/json" \
  -d '{"foo": "bar", "nested": {"key": "value"}}'

# Health check
curl http://127.0.0.1:8000/health
```

## Code Structure

```python
# 1. Define settings
class AppSettings(BaseSettings):
    app_name: str = "Hello myfy"

# 2. Create services with DI
@provider(scope=SINGLETON)
def greeting_service(settings: AppSettings) -> GreetingService:
    return GreetingService(settings)

# 3. Create routes
@route.get("/greet/{name}")
async def greet(name: str, service: GreetingService) -> dict:
    return {"greeting": service.greet(name)}

# 4. Wire it up
app = Application(settings_class=AppSettings)
app.add_module(WebModule())
```

## Principles in Action

- ✅ **Opinionated, not rigid**: Strong defaults (JSON responses, auto DI) but customizable
- ✅ **Defaults by default**: No config needed to get started
- ✅ **Sugar with substance**: `@route` and `@provider` compile to explicit DI
- ✅ **Pythonic**: Type hints drive injection, no XML/annotations
- ✅ **Predictable lifecycle**: Clear init → start → stop
- ✅ **Typed, validated, safe**: Pydantic settings with validation
- ✅ **Async-native**: All handlers async by default
- ✅ **Zero reflection on hot path**: Routes compiled at startup
