# myfy-frontend

Frontend module for myfy with **Tailwind 4**, **DaisyUI 5**, **Vite**, and **Jinja2**.

## Features

- 🎨 **DaisyUI 5** - Complete component library
- ⚡ **Tailwind 4** - Native CSS engine, faster builds
- 🔥 **Vite** - Lightning-fast HMR and bundling
- 📝 **Jinja2** - Server-side template rendering
- 🌗 **Dark Mode** - Built-in theme switcher
- 🚀 **Zero Config** - Works out of the box

## Installation

```bash
pip install myfy-frontend
```

## Quick Start

```python
from myfy.core import Application
from myfy.web import WebModule
from myfy.frontend import FrontendModule, render_template
from myfy.web import route

# Add the frontend module
app = Application(auto_discover=False)
app.add_module(WebModule())
app.add_module(FrontendModule())

# Create a route
@route.get("/")
async def home():
    return render_template("home.html", title="Welcome")
```

## What Happens on First Run

1. Detects missing `frontend/` directory
2. Copies template files and configurations
3. Installs Node.js dependencies (Tailwind 4, DaisyUI 5, Vite)
4. Starts Vite dev server
5. Ready to use!

## Project Structure (After Init)

```
your-project/
├── frontend/
│   ├── css/
│   │   └── input.css          # Tailwind imports
│   ├── js/
│   │   ├── main.js
│   │   └── theme-switcher.js
│   ├── templates/
│   │   ├── base.html          # Base layout
│   │   └── components/        # DaisyUI macros
│   └── static/
│       └── dist/              # Built assets (gitignored)
├── package.json
├── vite.config.js
└── app.py
```

## Creating Templates

```jinja2
{% extends "base.html" %}
{% from "components/navbar.html" import navbar %}

{% block content %}
{{ navbar(logo="MyApp") }}

<div class="hero min-h-screen bg-base-200">
  <div class="hero-content text-center">
    <h1 class="text-5xl font-bold">Hello DaisyUI 5!</h1>
    <button class="btn btn-primary">Get Started</button>
  </div>
</div>
{% endblock %}
```

## Development vs Production

**Development:**
- Vite dev server on `localhost:3001`
- Hot module replacement (HMR)
- Auto-reload on template changes

**Production:**
- Optimized CSS/JS bundles
- Asset hashing for cache busting
- Gzip compression

## CLI Commands

```bash
# Initialize frontend (manual)
uv run myfy frontend init

# Build for production
uv run myfy frontend build

# Start dev server
uv run myfy frontend dev
```

## License

MIT
