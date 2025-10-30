# myfy-frontend

Frontend module for myfy with **Tailwind 4**, **DaisyUI 5**, **Vite**, and **Jinja2** templates.

## Overview

`myfy-frontend` provides a complete frontend solution that seamlessly integrates with myfy's web module. It combines modern frontend tooling (Vite, Tailwind 4) with server-side rendering (Jinja2) for a powerful full-stack experience.

## Installation

```bash
# Install frontend module
pip install myfy-frontend

# Or with uv
uv pip install myfy-frontend
```

**Dependencies:**
- `myfy-core` - Core framework
- `myfy-web` - Web module
- `jinja2` - Template engine
- Node.js and npm (for Vite and Tailwind)

## Key Features

### Modern CSS with Tailwind 4

- **Native CSS engine** - Faster builds, no PostCSS
- **Better performance** - Optimized output
- **Modern syntax** - CSS variables, container queries
- **Zero config** - Works out of the box

### Component Library with DaisyUI 5

- **50+ components** - Buttons, cards, modals, forms
- **Semantic themes** - Light/dark mode built-in
- **Accessibility** - WCAG compliant
- **Customizable** - Full theme control

### Lightning-Fast Dev with Vite

- **Instant HMR** - Sub-100ms hot updates
- **Optimized builds** - Tree-shaking, code splitting
- **Dev server** - Fast, reliable, zero config
- **Asset handling** - Images, fonts, icons

### Server-Side Templates with Jinja2

- **Familiar syntax** - Like Django/Flask templates
- **Template inheritance** - DRY principles
- **Macros** - Reusable components
- **Auto-reload** - Changes reflect immediately

## Quick Start

### Step 1: Initialize Frontend

Run the init command to scaffold your frontend:

```bash
uv run myfy frontend init
```

This creates:
- `app.py` - Ready-to-run application with a home route
- `frontend/templates/home.html` - Styled welcome page with DaisyUI
- `frontend/templates/base.html` - Base layout template
- `frontend/templates/components/` - Reusable component templates
- `frontend/css/` - Tailwind CSS files
- `frontend/js/` - JavaScript entry points
- `package.json` - Node dependencies (Vite, Tailwind 4, DaisyUI 5)
- `vite.config.js` - Vite configuration

**Output:**
```
🎨 Initializing myfy frontend...
✅ Created package.json
✅ Created vite.config.js
✅ Created .gitignore
✅ Created app.py
✅ Created frontend/ directory structure

📦 Installing Node dependencies...
✅ Node dependencies installed!

✨ Frontend initialized successfully!

Next steps:
  1. Run 'uv run myfy run' to start your app
  2. Edit frontend/templates/ to create your pages
  3. Customize frontend/css/input.css for your styles
```

### Step 2: Run Your App

```bash
uv run myfy run
```

Visit `http://127.0.0.1:8000` to see your styled home page!

### What You Get

The generated `app.py` contains:

```python
from myfy.core import Application
from myfy.web import WebModule, route
from myfy.frontend import FrontendModule, render_template
from starlette.requests import Request
from starlette.templating import Jinja2Templates

@route.get("/")
async def home(request: Request, templates: Jinja2Templates):
    """Home page."""
    return render_template(
        "home.html",
        request=request,
        templates=templates,
        title="Welcome to myfy",
    )

# Create application
app = Application(auto_discover=False)
app.add_module(WebModule())
app.add_module(FrontendModule())

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
```

The generated `home.html` includes:
- Welcome message with your app name
- DaisyUI buttons demonstrating component usage
- Next steps section guiding you through customization
- Responsive layout with Tailwind utilities

## Project Structure

After initialization, your project will have:

```
your-project/
├── frontend/
│   ├── css/
│   │   └── input.css              # Tailwind directives
│   ├── js/
│   │   ├── main.js                # Main JavaScript entry
│   │   └── theme-switcher.js      # Dark mode toggle
│   ├── templates/
│   │   ├── base.html              # Base layout
│   │   ├── home.html              # Homepage example
│   │   └── components/
│   │       ├── navbar.html        # Navigation component
│   │       ├── footer.html        # Footer component
│   │       └── button.html        # Button component
│   └── static/
│       └── dist/                  # Built assets (gitignored)
├── package.json                   # Node dependencies
├── vite.config.js                 # Vite configuration
└── app.py                         # Your application
```

## Creating Templates

### Basic Template

```jinja2
{# templates/home.html #}
{% extends "base.html" %}

{% block content %}
<div class="hero min-h-screen bg-base-200">
  <div class="hero-content text-center">
    <div class="max-w-md">
      <h1 class="text-5xl font-bold">Hello, myfy!</h1>
      <p class="py-6">Build Python apps with modern frontend tooling.</p>
      <button class="btn btn-primary">Get Started</button>
    </div>
  </div>
</div>
{% endblock %}
```

### Using Components

```jinja2
{# Import components #}
{% from "components/navbar.html" import navbar %}
{% from "components/footer.html" import footer %}

{% block content %}
{{ navbar(logo="MyApp", links=[
    {"text": "Home", "href": "/"},
    {"text": "About", "href": "/about"},
    {"text": "Contact", "href": "/contact"}
]) }}

<main>
  <!-- Your content -->
</main>

{{ footer(year=2025) }}
{% endblock %}
```

### Template Inheritance

```jinja2
{# Base template #}
<!DOCTYPE html>
<html data-theme="light">
<head>
    <title>{% block title %}My App{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', path='dist/style.css') }}">
</head>
<body>
    {% block content %}{% endblock %}
    <script type="module" src="{{ url_for('static', path='dist/main.js') }}"></script>
</body>
</html>
```

## Rendering Templates

### Basic Rendering

```python
from myfy.frontend import render_template
from myfy.web import route

@route.get("/")
async def home():
    return render_template("home.html")
```

### With Variables

```python
@route.get("/user/{user_id}")
async def user_profile(user_id: int, service: UserService):
    user = await service.get_user(user_id)
    return render_template(
        "user.html",
        user=user,
        title=f"{user.name}'s Profile"
    )
```

### With Complex Data

```python
@route.get("/dashboard")
async def dashboard(service: DashboardService):
    data = await service.get_dashboard_data()
    return render_template(
        "dashboard.html",
        stats=data.stats,
        recent_items=data.recent_items,
        notifications=data.notifications
    )
```

## DaisyUI Components

### Buttons

```html
<button class="btn">Button</button>
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
<button class="btn btn-accent">Accent</button>
<button class="btn btn-ghost">Ghost</button>
<button class="btn btn-link">Link</button>

<!-- Sizes -->
<button class="btn btn-lg">Large</button>
<button class="btn btn-sm">Small</button>
<button class="btn btn-xs">Tiny</button>
```

### Cards

```html
<div class="card bg-base-100 shadow-xl">
  <figure>
    <img src="/image.jpg" alt="Card image" />
  </figure>
  <div class="card-body">
    <h2 class="card-title">Card Title</h2>
    <p>Card description goes here.</p>
    <div class="card-actions justify-end">
      <button class="btn btn-primary">Action</button>
    </div>
  </div>
</div>
```

### Forms

```html
<form class="form-control w-full max-w-xs">
  <label class="label">
    <span class="label-text">Email</span>
  </label>
  <input type="email" class="input input-bordered w-full" />

  <label class="label">
    <span class="label-text">Password</span>
  </label>
  <input type="password" class="input input-bordered w-full" />

  <button type="submit" class="btn btn-primary mt-4">Submit</button>
</form>
```

### Modals

```html
<!-- Trigger -->
<button class="btn" onclick="my_modal.showModal()">Open Modal</button>

<!-- Modal -->
<dialog id="my_modal" class="modal">
  <div class="modal-box">
    <h3 class="font-bold text-lg">Hello!</h3>
    <p class="py-4">This is a modal dialog.</p>
    <div class="modal-action">
      <form method="dialog">
        <button class="btn">Close</button>
      </form>
    </div>
  </div>
</dialog>
```

### Navbar

```html
<div class="navbar bg-base-100">
  <div class="flex-1">
    <a class="btn btn-ghost text-xl">MyApp</a>
  </div>
  <div class="flex-none">
    <ul class="menu menu-horizontal px-1">
      <li><a>Home</a></li>
      <li><a>About</a></li>
      <li><a>Contact</a></li>
    </ul>
  </div>
</div>
```

## Dark Mode

### Theme Switcher

Built-in theme switcher in `js/theme-switcher.js`:

```javascript
// Automatically includes toggle button
// Saves preference to localStorage
// Syncs across tabs
```

### Using in Templates

```html
<!-- Theme toggle button -->
<label class="swap swap-rotate">
  <input type="checkbox" class="theme-controller" />
  <svg class="swap-on"><!-- Sun icon --></svg>
  <svg class="swap-off"><!-- Moon icon --></svg>
</label>
```

### Custom Themes

Edit `vite.config.js`:

```javascript
export default {
  plugins: [
    daisyui({
      themes: ["light", "dark", "cupcake", "forest"]
    })
  ]
}
```

## Vite Configuration

### Default Config

```javascript
// vite.config.js
import { defineConfig } from 'vite'

export default defineConfig({
  root: 'frontend',
  build: {
    outDir: 'static/dist',
    manifest: true,
    rollupOptions: {
      input: {
        main: 'frontend/js/main.js',
        style: 'frontend/css/input.css'
      }
    }
  },
  server: {
    port: 3001,
    cors: true
  }
})
```

### Custom Configuration

```javascript
export default defineConfig({
  // Add custom plugins
  plugins: [vue()],

  // Optimize dependencies
  optimizeDeps: {
    include: ['axios', 'lodash']
  },

  // Configure proxy
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

## Development vs Production

### Development Mode

When running `uv run myfy run`:

- Vite dev server starts automatically
- HMR (Hot Module Replacement) enabled
- Assets served from `http://localhost:3001`
- Templates reload on changes
- Source maps included

### Production Mode

Build for production:

```bash
# Build frontend assets
uv run myfy frontend build

# Run application
MYFY_PROFILE=prod uv run myfy run --no-reload
```

**Production features:**
- Minified CSS and JavaScript
- Tree-shaking for smaller bundles
- Asset hashing for cache busting
- Gzip compression
- Optimized images

## Static Files

### Serving Static Assets

```python
from myfy.web import route
from starlette.responses import FileResponse

@route.get("/images/{filename}")
async def serve_image(filename: str):
    return FileResponse(f"frontend/static/images/{filename}")
```

### URL Helpers

```jinja2
{# In templates #}
<link rel="stylesheet" href="{{ url_for('static', path='dist/style.css') }}">
<script src="{{ url_for('static', path='dist/main.js') }}"></script>
<img src="{{ url_for('static', path='images/logo.png') }}">
```

## Forms and HTMX

### Form Handling

```python
from pydantic import BaseModel

class ContactForm(BaseModel):
    name: str
    email: str
    message: str

@route.get("/contact")
async def contact_page():
    return render_template("contact.html")

@route.post("/contact")
async def submit_contact(body: ContactForm):
    # Process form
    return render_template("success.html", name=body.name)
```

### HTMX Integration

```html
<!-- Install HTMX -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>

<!-- Dynamic content -->
<button
  hx-get="/api/data"
  hx-target="#result"
  class="btn btn-primary"
>
  Load Data
</button>

<div id="result"></div>
```

## API Reference

For detailed frontend API documentation, refer to the source code in `packages/myfy-frontend/myfy/frontend/`.

Key exports:
- `FrontendModule` - Main module for frontend integration
- `render_template()` - Function to render Jinja2 templates

## Best Practices

### Use Template Components

```jinja2
{# ✓ Good - Reusable components #}
{% from "components/button.html" import button %}
{{ button(text="Submit", color="primary") }}

{# ✗ Bad - Inline HTML #}
<button class="btn btn-primary">Submit</button>
```

### Organize Templates

```
templates/
├── base.html              # Base layout
├── components/            # Reusable components
│   ├── navbar.html
│   └── footer.html
├── pages/                 # Full pages
│   ├── home.html
│   └── about.html
└── partials/             # Page sections
    └── hero.html
```

### Use Tailwind Classes Wisely

```html
<!-- ✓ Good - Use DaisyUI components -->
<button class="btn btn-primary">Click me</button>

<!-- ✗ Bad - Too many utility classes -->
<button class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
  Click me
</button>
```

### Build for Production

```bash
# ✓ Good - Build before deploying
uv run myfy frontend build

# ✗ Bad - Use dev server in production
# Don't do this!
```

## Examples

### Full Page Example

```python
# app.py
from myfy.core import Application
from myfy.web import WebModule, route
from myfy.frontend import FrontendModule, render_template

app = Application(auto_discover=False)
app.add_module(WebModule())
app.add_module(FrontendModule())

@route.get("/")
async def home():
    return render_template(
        "home.html",
        title="Welcome",
        hero_text="Build amazing apps with myfy"
    )
```

```jinja2
{# templates/home.html #}
{% extends "base.html" %}
{% from "components/navbar.html" import navbar %}

{% block title %}{{ title }}{% endblock %}

{% block content %}
{{ navbar(logo="MyApp") }}

<div class="hero min-h-screen bg-gradient-to-r from-primary to-secondary">
  <div class="hero-content text-center text-neutral-content">
    <div class="max-w-md">
      <h1 class="mb-5 text-5xl font-bold">{{ hero_text }}</h1>
      <p class="mb-5">
        Combining Python's power with modern frontend tooling.
      </p>
      <button class="btn btn-accent">Get Started</button>
    </div>
  </div>
</div>
{% endblock %}
```

## Troubleshooting

### Vite Dev Server Not Starting

```bash
# Check if Node.js is installed
node --version

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Manually start Vite
npm run dev
```

### Styles Not Loading

```bash
# Rebuild assets
uv run myfy frontend build

# Check Vite config
cat vite.config.js

# Verify CSS import in template
# Should have: <link rel="stylesheet" href="...dist/style.css">
```

### Template Not Found

```python
# Check template path
# Should be: frontend/templates/your-template.html

# Verify template is in the right location
ls frontend/templates/
```

## Next Steps

- **Learn Templates**: Study Jinja2 template syntax
- **Explore DaisyUI**: Browse [DaisyUI components](https://daisyui.com)
- **Customize Tailwind**: Learn [Tailwind customization](https://tailwindcss.com)
- **Add Interactivity**: Integrate HTMX or Alpine.js
- **Deploy**: Build and deploy your application
