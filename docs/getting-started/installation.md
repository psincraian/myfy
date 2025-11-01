# Installation

Get up and running with myfy in minutes.

---

## Prerequisites

- **Python 3.12+** (myfy uses modern Python features)
- **uv** (recommended) or pip for package management

---

## Install uv (Recommended)

myfy works great with [uv](https://github.com/astral-sh/uv), the fast Python package manager:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

---

## Quick Install

### Option 1: Install All Modules (Easiest)

```bash
# With uv
uv pip install myfy

# With pip
pip install myfy
```

This installs:
- `myfy-core` - Core framework (DI, config, modules)
- `myfy-web` - Web/ASGI support
- `myfy-cli` - CLI tools

### Option 2: Install Individual Modules

```bash
# Core only (for libraries/packages)
uv pip install myfy-core

# Core + Web (for HTTP APIs)
uv pip install myfy-core myfy-web

# Core + Web + CLI
uv pip install myfy-core myfy-web myfy-cli

# Full-stack with frontend
uv pip install myfy-core myfy-web myfy-cli myfy-frontend
```

---

## Create Your First App

### 1. Create Project Directory

```bash
mkdir my-app
cd my-app
```

### 2. Create `app.py`

```python
from myfy.core import Application, BaseSettings
from myfy.web import route, WebModule


class Settings(BaseSettings):
    app_name: str = "My First App"


@route.get("/")
async def index() -> dict:
    return {"message": "Hello, myfy!"}


app = Application(settings_class=Settings, auto_discover=False)
app.add_module(WebModule())


if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
```

### 3. Create `.env` File (Optional)

```bash
# .env
APP_NAME=My Awesome API
```

### 4. Run It

```bash
# With myfy CLI (auto-reload enabled)
uv run myfy run

# Or directly with Python
uv run python app.py
```

Visit `http://127.0.0.1:8000/` - you should see:

```json
{"message": "Hello, myfy!"}
```

---

## Example: Full-Stack App with Frontend

Want to build a web app with UI? Add the frontend module:

### 1. Install with Frontend Support

```bash
uv pip install myfy-core myfy-web myfy-cli myfy-frontend
```

### 2. Create `app.py`

```python
from myfy.core import Application, BaseSettings
from myfy.web import route, WebModule
from myfy.frontend import FrontendModule, render_template


class Settings(BaseSettings):
    app_name: str = "My Web App"


@route.get("/")
async def home():
    return render_template(
        "home.html",
        title="Welcome",
        message="Hello from myfy!"
    )


@route.get("/api/hello")
async def api_hello() -> dict:
    return {"message": "Hello from API!"}


app = Application(settings_class=Settings, auto_discover=False)
app.add_module(WebModule())
app.add_module(FrontendModule())


if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
```

### 3. Initialize Frontend

```bash
# Initialize frontend (creates templates, CSS, JS)
uv run myfy frontend init
```

This creates:
```
my-app/
├── frontend/
│   ├── css/
│   │   └── input.css       # Tailwind CSS
│   ├── js/
│   │   └── main.js         # JavaScript entry
│   ├── templates/
│   │   ├── base.html       # Base layout
│   │   └── home.html       # Home page
│   └── static/
│       └── dist/           # Built assets
├── package.json            # Node dependencies
├── vite.config.js          # Vite config
└── app.py
```

### 4. Create `frontend/templates/home.html`

```jinja2
{% extends "base.html" %}

{% block title %}{{ title }}{% endblock %}

{% block content %}
<div class="hero min-h-screen bg-gradient-to-r from-primary to-secondary">
  <div class="hero-content text-center text-neutral-content">
    <div class="max-w-md">
      <h1 class="mb-5 text-5xl font-bold">{{ message }}</h1>
      <p class="mb-5">
        Build modern web apps with Python backend and beautiful UI.
      </p>
      <button class="btn btn-accent">Get Started</button>
    </div>
  </div>
</div>
{% endblock %}
```

### 5. Run Your App

```bash
uv run myfy run
```

Visit `http://127.0.0.1:8000/` to see your app with:
- **Server-side rendering** with Jinja2
- **Tailwind CSS 4** for styling
- **DaisyUI 5** components
- **Vite** for hot module replacement
- **Dark mode** built-in

---

## Project Structure

For larger applications, we recommend this structure:

```
my-app/
├── app.py              # Application entry point
├── .env                # Environment variables
├── .env.dev            # Dev profile
├── .env.prod           # Production profile
├── config.py           # Settings classes
├── services/           # Business logic
│   ├── __init__.py
│   └── users.py
├── models/             # Data models
│   ├── __init__.py
│   └── user.py
└── routes/             # HTTP handlers
    ├── __init__.py
    └── users.py
```

---

## Verify Installation

Check that everything is working:

```bash
# List available CLI commands
uv run myfy --help

# Check Python version
python --version  # Should be 3.12+

# Test imports
python -c "from myfy.core import Application; from myfy.web import route; print('✓ All good!')"
```

---

## Development Setup

For active development on myfy itself:

```bash
# Clone the repo
git clone https://github.com/psincraian/myfy.git
cd myfy

# Install with uv
uv sync

# Install packages in editable mode
uv pip install -e packages/myfy-core
uv pip install -e packages/myfy-web
uv pip install -e packages/myfy-cli

# Run example
cd examples/hello
uv run myfy run
```

---

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'myfy'`:

```bash
# Make sure you're in the right environment
which python

# Reinstall
uv pip install --force-reinstall myfy
```

### Port Already in Use

If port 8000 is busy:

```bash
# Run on different port
uv run myfy run --port 8001
```

### uv Not Found

If `uv` command not found:

```bash
# Add to PATH (macOS/Linux)
export PATH="$HOME/.cargo/bin:$PATH"

# Or use pip directly
pip install myfy
```

---

## Next Steps

- [Tutorial](tutorial.md) - Build a complete application
- [Quick Reference](quick-reference.md) - Common patterns
- [Core Concepts](../core-concepts/dependency-injection.md) - Deep dive into DI

---

## System Requirements

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.12+ |
| **OS** | Linux, macOS, Windows |
| **Memory** | 512MB+ recommended |
| **Dependencies** | pydantic, starlette, anyio |
