---
name: frontend-module
description: myfy FrontendModule for server-side rendering with Jinja2, Tailwind 4, DaisyUI 5, and Vite. Use when working with FrontendModule, templates, render_template, static files, Tailwind CSS, or Vite HMR.
---

# FrontendModule - Server-Side Rendering

FrontendModule provides Jinja2 templates with Tailwind 4, DaisyUI 5, and Vite bundling.

## Quick Start

```python
from myfy.core import Application
from myfy.web import WebModule, route
from myfy.frontend import FrontendModule, render_template

app = Application()
app.add_module(WebModule())
app.add_module(FrontendModule(auto_init=True))  # Auto-scaffolds!

@route.get("/")
async def home() -> str:
    return render_template("home.html", title="Welcome")
```

## Configuration

Environment variables use the `MYFY_FRONTEND_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `MYFY_FRONTEND_ENVIRONMENT` | `development` | Environment mode |
| `MYFY_FRONTEND_ENABLE_VITE_DEV` | `True` | Start Vite dev server |
| `MYFY_FRONTEND_VITE_DEV_SERVER` | `http://localhost:3001` | Vite server URL |
| `MYFY_FRONTEND_STATIC_URL_PREFIX` | `/static` | Static files URL path |
| `MYFY_FRONTEND_CACHE_STATIC_ASSETS` | `True` | Enable static caching |
| `MYFY_FRONTEND_CACHE_MAX_AGE` | `31536000` | Cache max-age (1 year) |
| `MYFY_FRONTEND_SHOW_VITE_LOGS` | `False` | Show Vite console output |

## Module Options

```python
FrontendModule(
    templates_dir="frontend/templates",  # Template directory
    static_dir="frontend/static",        # Static files directory
    auto_init=True,                      # Auto-scaffold if missing
)
```

## Auto-Scaffolding

With `auto_init=True`, FrontendModule creates:

```
frontend/
  templates/
    base.html           # Base template with Tailwind
    home.html           # Example home page
  static/
    src/
      main.js           # Entry point
      main.css          # Tailwind imports
package.json            # Node dependencies
vite.config.js          # Vite configuration
tailwind.config.js      # Tailwind configuration
```

## Template Rendering

### Basic Rendering

```python
from myfy.frontend import render_template

@route.get("/")
async def home() -> str:
    return render_template("home.html", title="Home")
```

### With Context

```python
@route.get("/users/{user_id}")
async def user_profile(user_id: int, session: AsyncSession) -> str:
    user = await session.get(User, user_id)
    return render_template("profile.html", user=user)
```

### With Request Context

```python
from starlette.requests import Request

@route.get("/dashboard")
async def dashboard(request: Request, user: User) -> str:
    return render_template(
        "dashboard.html",
        request=request,  # For url_for, CSRF, etc.
        user=user,
    )
```

## Base Template

```html
<!-- frontend/templates/base.html -->
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}My App{% endblock %}</title>
    {{ vite_assets("src/main.js") }}
</head>
<body class="min-h-screen bg-base-100">
    <div class="navbar bg-base-200">
        <a class="btn btn-ghost text-xl" href="/">My App</a>
    </div>
    <main class="container mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

## Page Template

```html
<!-- frontend/templates/home.html -->
{% extends "base.html" %}

{% block title %}{{ title }} - My App{% endblock %}

{% block content %}
<div class="hero min-h-[50vh]">
    <div class="hero-content text-center">
        <div class="max-w-md">
            <h1 class="text-5xl font-bold">Hello, World!</h1>
            <p class="py-6">Welcome to your myfy application.</p>
            <button class="btn btn-primary">Get Started</button>
        </div>
    </div>
</div>
{% endblock %}
```

## DaisyUI Components

DaisyUI 5 provides ready-to-use components:

```html
<!-- Buttons -->
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
<button class="btn btn-outline">Outline</button>

<!-- Cards -->
<div class="card bg-base-100 shadow-xl">
    <div class="card-body">
        <h2 class="card-title">Card Title</h2>
        <p>Card content here.</p>
        <div class="card-actions justify-end">
            <button class="btn btn-primary">Action</button>
        </div>
    </div>
</div>

<!-- Forms -->
<div class="form-control">
    <label class="label">
        <span class="label-text">Email</span>
    </label>
    <input type="email" class="input input-bordered" />
</div>

<!-- Alerts -->
<div class="alert alert-success">
    <span>Success! Your action was completed.</span>
</div>
```

## Theme Switching

```html
<!-- Theme toggle -->
<label class="swap swap-rotate">
    <input type="checkbox" class="theme-controller" value="dark" />
    <svg class="swap-on w-6 h-6" fill="currentColor"><!-- sun icon --></svg>
    <svg class="swap-off w-6 h-6" fill="currentColor"><!-- moon icon --></svg>
</label>
```

## Static Assets

### Vite Helper

```html
<!-- Loads JS and CSS with HMR in development -->
{{ vite_assets("src/main.js") }}
```

### Manual Asset URLs

```html
<img src="{{ asset_url('images/logo.png') }}" alt="Logo">
```

## Development Workflow

1. Start the application:
   ```bash
   myfy run
   ```
   Vite dev server starts automatically with HMR.

2. Edit templates and CSS - changes reflect instantly.

3. Build for production:
   ```bash
   npm run build
   ```
   Creates optimized assets in `frontend/static/dist/`.

## Production Build

```bash
# Build assets
npm run build

# Set production mode
export MYFY_FRONTEND_ENVIRONMENT=production
export MYFY_FRONTEND_ENABLE_VITE_DEV=false

# Run application
myfy run
```

Assets are served from the built manifest with cache headers.

## Custom Jinja Filters

```python
from myfy.frontend import FrontendModule
from starlette.templating import Jinja2Templates

# After module initialization
templates: Jinja2Templates = container.get(Jinja2Templates)
templates.env.filters["currency"] = lambda x: f"${x:.2f}"
```

Use in templates:

```html
<span>{{ price | currency }}</span>
```

## Best Practices

1. **Use auto_init for new projects** - Gets you started quickly
2. **Extend base.html** - Keep consistent layout
3. **Use DaisyUI components** - Pre-styled, accessible
4. **Enable caching in production** - Set long cache max-age
5. **Build assets before deploy** - Don't rely on Vite in production
6. **Use template inheritance** - Keep templates DRY
7. **Pass request for url_for** - Enables dynamic URL generation
