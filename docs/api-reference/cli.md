# CLI API Reference

API reference for `myfy-cli` package.

---

## Commands

The `myfy` CLI provides the following commands:

### run

Start the development server with auto-reload enabled.

```bash
myfy run [OPTIONS]
```

**Options:**
- `--host TEXT`: Server host (default: 127.0.0.1)
- `--port INTEGER`: Server port (default: 8000)
- `--reload / --no-reload`: Enable auto-reload (default: True)
- `--app-path TEXT`: Path to app (e.g., main:app)

**Example:**
```bash
myfy run --host 0.0.0.0 --port 8080
```

### start

Start the production server with optimizations enabled.

```bash
myfy start [OPTIONS]
```

**Options:**
- `--host TEXT`: Server host (default: 127.0.0.1)
- `--port INTEGER`: Server port (default: 8000)
- `--workers INTEGER`: Number of worker processes (default: 1)
- `--app-path TEXT`: Path to app (e.g., main:app)

**Features:**
- Automatically sets `MYFY_FRONTEND_ENVIRONMENT=production`
- Disables auto-reload for better performance
- Verifies frontend assets are built (if FrontendModule is loaded)
- Supports multiple worker processes via gunicorn

**Example:**
```bash
# Single worker
myfy frontend build
myfy start --host 0.0.0.0 --port 8000

# Multiple workers for better performance
myfy start --host 0.0.0.0 --port 8000 --workers 4
```

**Note:** For multi-worker support, install gunicorn:
```bash
pip install gunicorn
# or
uv add gunicorn
```

### routes

List all registered routes.

```bash
myfy routes
```

### modules

Show all loaded modules.

```bash
myfy modules
```

### doctor

Validate application configuration.

```bash
myfy doctor
```

---

## Quick Links

- [Installation](../getting-started/installation.md)
- [Tutorial](../getting-started/tutorial.md)
