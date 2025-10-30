# myfy-cli

Command-line tools for developing and managing myfy applications.

## Overview

`myfy-cli` provides a suite of commands to streamline development, debugging, and deployment of myfy applications. Built on Typer for an excellent CLI experience.

## Installation

```bash
# Install CLI tools
pip install myfy-cli

# Or with uv
uv pip install myfy-cli
```

**Dependencies:**
- `myfy-core` - Core framework
- `typer` - CLI framework
- `rich` - Terminal formatting

## Available Commands

### `myfy run`

Start the development server with auto-reload.

```bash
uv run myfy run

# Options
uv run myfy run --port 8080          # Custom port
uv run myfy run --host 0.0.0.0       # Bind to all interfaces
uv run myfy run --no-reload          # Disable auto-reload
uv run myfy run --app main:app       # Custom app location
```

**Features:**
- Hot reload on file changes
- Colored output
- Error reporting
- Auto-detects app location

**Output:**
```
🚀 Starting myfy development server...
✓ Found application in app.py
📡 Listening on http://127.0.0.1:8000
📦 Loaded 2 module(s)
🔄 Reload enabled - watching for file changes
```

### `myfy routes`

List all registered routes in your application.

```bash
uv run myfy routes

# Options
uv run myfy routes --app main:app    # Custom app location
```

**Output:**
```
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━┓
┃ Method ┃ Path            ┃ Handler      ┃ Name ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━┩
│ GET    │ /               │ home         │ -    │
│ GET    │ /users          │ list_users   │ -    │
│ GET    │ /users/{id}     │ get_user     │ -    │
│ POST   │ /users          │ create_user  │ -    │
│ PUT    │ /users/{id}     │ update_user  │ -    │
│ DELETE │ /users/{id}     │ delete_user  │ -    │
└────────┴─────────────────┴──────────────┴──────┘
```

### `myfy modules`

Show all loaded modules and their status.

```bash
uv run myfy modules

# Options
uv run myfy modules --app main:app   # Custom app location
```

**Output:**
```
┏━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Module        ┃ Status  ┃ Description              ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ WebModule     │ ✓ Ready │ HTTP/ASGI server         │
│ DataModule    │ ✓ Ready │ Database connections     │
│ CacheModule   │ ✓ Ready │ Redis cache              │
└───────────────┴─────────┴──────────────────────────┘
```

### `myfy doctor`

Validate application configuration and dependencies.

```bash
uv run myfy doctor

# Options
uv run myfy doctor --app main:app    # Custom app location
uv run myfy doctor --fix             # Auto-fix issues if possible
```

**Output:**
```
🔍 Running diagnostics...

Configuration:
  ✓ Settings loaded from .env
  ✓ All required settings present
  ⚠ DEBUG=true (disable in production)

Dependency Injection:
  ✓ No circular dependencies
  ✓ All providers registered
  ✓ All scopes valid

Modules:
  ✓ 3 modules loaded
  ✓ No conflicts detected

Routes:
  ✓ 12 routes registered
  ⚠ 2 routes missing type hints

Summary: 2 warnings, 0 errors
```

### `myfy frontend init`

Initialize frontend assets (Tailwind, Vite, templates).

```bash
uv run myfy frontend init

# Options
uv run myfy frontend init --force    # Overwrite existing files
```

**What it does:**
1. Creates `frontend/` directory structure
2. Copies template files
3. Generates `package.json` and `vite.config.js`
4. Installs Node.js dependencies
5. Starts Vite dev server

**Output:**
```
🎨 Initializing myfy frontend...
✓ Created frontend/ directory
✓ Copied template files
✓ Generated package.json
✓ Installed dependencies
✓ Vite dev server started on http://localhost:3001
```

### `myfy frontend build`

Build frontend assets for production.

```bash
uv run myfy frontend build
```

**Output:**
```
📦 Building frontend for production...
✓ Optimized CSS (23kb → 8kb)
✓ Minified JavaScript
✓ Generated asset manifest
✓ Build complete: frontend/static/dist/
```

### `myfy frontend dev`

Start Vite development server.

```bash
uv run myfy frontend dev
```

**Output:**
```
⚡ Starting Vite dev server...
✓ Server running at http://localhost:3001
🔥 Hot module replacement enabled
```

## Usage Examples

### Development Workflow

```bash
# 1. Start development server
uv run myfy run

# 2. In another terminal, check routes
uv run myfy routes

# 3. Validate configuration
uv run myfy doctor

# 4. If using frontend
uv run myfy frontend init
```

### Production Deployment

```bash
# 1. Build frontend assets
uv run myfy frontend build

# 2. Validate everything
uv run myfy doctor

# 3. Run with production settings
MYFY_PROFILE=prod uv run myfy run --no-reload
```

### Debugging

```bash
# List all routes to verify registration
uv run myfy routes

# Check module loading
uv run myfy modules

# Validate DI configuration
uv run myfy doctor
```

## Configuration

### App Location

By default, CLI tools look for `app` or `application` in `app.py`, `main.py`, or `server.py`.

**Custom app location:**
```bash
# Via flag
uv run myfy run --app my_app:application

# Via environment variable
export MYFY_APP=my_app:application
uv run myfy run
```

### Environment Profiles

Set the profile before running commands:

```bash
# Development
export MYFY_PROFILE=dev
uv run myfy run

# Production
export MYFY_PROFILE=prod
uv run myfy run --no-reload
```

## Command Options

### Global Options

Available for all commands:

```bash
--app TEXT          # Application path (module:variable)
--help             # Show help message
```

### `run` Options

```bash
--host TEXT        # Bind address (default: 127.0.0.1)
--port INTEGER     # Port number (default: 8000)
--reload          # Enable auto-reload (default: true in dev)
--no-reload       # Disable auto-reload
--log-level TEXT  # Log level (debug, info, warning, error)
```

### `doctor` Options

```bash
--fix             # Attempt to auto-fix issues
--verbose         # Show detailed diagnostics
```

### `frontend init` Options

```bash
--force           # Overwrite existing files
--no-install      # Skip npm install
```

## Integrating with CI/CD

### Validation in CI

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e .

      - name: Validate configuration
        run: uv run myfy doctor

      - name: Check routes
        run: uv run myfy routes
```

### Production Build

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install uv && uv pip install .

# Copy application
COPY . .

# Build frontend
RUN uv run myfy frontend build

# Validate
RUN uv run myfy doctor

# Run
CMD ["uv", "run", "myfy", "run", "--host", "0.0.0.0", "--no-reload"]
```

## Creating Custom Commands

Extend the CLI with your own commands:

```python
# commands.py
import typer
from myfy.cli import app as cli_app

@cli_app.command()
def custom_command(name: str):
    """My custom command."""
    typer.echo(f"Hello {name}!")

# Usage: uv run myfy custom-command John
```

## Troubleshooting

### App Not Found

```bash
# Error: Could not find application

# Solution 1: Specify app location
uv run myfy run --app my_module:app

# Solution 2: Use standard naming
# Rename your app variable to 'app' or 'application'
```

### Module Import Errors

```bash
# Error: No module named 'xyz'

# Solution: Ensure you're in the right directory
cd /path/to/your/project

# And dependencies are installed
uv pip install -e .
```

### Port Already in Use

```bash
# Error: Address already in use

# Solution: Use different port
uv run myfy run --port 8001

# Or kill the process using the port
lsof -ti:8000 | xargs kill
```

## API Reference

For detailed API documentation, see:

- [CLI API Reference](../api-reference/cli.md)

## Best Practices

### Use Profiles

```bash
# ✓ Good - Explicit profiles
export MYFY_PROFILE=dev
uv run myfy run

# ✗ Bad - No profile specified
uv run myfy run  # Uses default .env
```

### Validate Before Deploy

```bash
# ✓ Good - Check everything first
uv run myfy doctor
uv run myfy routes
uv run myfy frontend build

# ✗ Bad - Deploy without checking
uv run myfy run --no-reload
```

### Use `--no-reload` in Production

```bash
# ✓ Good - No reload in production
MYFY_PROFILE=prod uv run myfy run --no-reload

# ✗ Bad - Auto-reload in production
MYFY_PROFILE=prod uv run myfy run
```

## Next Steps

- **Learn Core**: Read [`myfy-core`](core.md) documentation
- **Add Web Routes**: Install [`myfy-web`](web.md)
- **Add Frontend**: Install [`myfy-frontend`](frontend.md)
- **Deployment**: Learn how to deploy to production
