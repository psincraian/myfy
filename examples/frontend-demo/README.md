# Frontend Demo

Example application showcasing myfy's FrontendModule with Tailwind 4 and DaisyUI 5.

## Quick Start

```bash
# From the examples/frontend-demo directory
cd examples/frontend-demo

# Option 1: Using virtualenv (recommended)
# Create virtualenv if not already created
uv venv .venv
source .venv/bin/activate
uv pip install -e ../../packages/myfy-core -e ../../packages/myfy-web -e ../../packages/myfy-frontend -e ../../packages/myfy-cli

# Run the app (will auto-scaffold frontend on first run)
myfy run

# Option 2: Direct invocation without activating
.venv/bin/myfy run
```

Note: `uv run --with` doesn't work reliably with local interdependent packages. Use the virtualenv approach above instead.

The first run will:
1. Create `frontend/` directory structure
2. Copy template files
3. Install Node.js dependencies (Tailwind 4, DaisyUI 5, Vite)
4. Start Vite dev server
5. Launch the application

Visit: http://localhost:8001

## What's Included

- **Home page** - Hero section with DaisyUI components
- **About page** - Example of card layouts
- **Components page** - Showcase of DaisyUI components

## File Structure

```
frontend-demo/
├── app.py                    # Main application
├── frontend/                 # Auto-generated
│   ├── css/
│   │   └── input.css        # Tailwind imports
│   ├── js/
│   │   ├── main.js
│   │   └── theme-switcher.js
│   ├── templates/
│   │   ├── base.html        # Base layout
│   │   ├── home.html        # Custom pages
│   │   ├── about.html
│   │   └── components.html
│   └── static/dist/         # Built assets
├── package.json             # Node dependencies
└── vite.config.js           # Vite configuration
```

## Development

**Hot Reload:**
- Edit templates in `frontend/templates/` - auto-reload
- Edit CSS in `frontend/css/input.css` - HMR
- Edit JS in `frontend/js/` - HMR

**Vite Logs:**
By default, Vite runs in the background without showing logs. To see Vite output:
```bash
# Set in .env file (already configured in this demo)
FRONTEND_SHOW_VITE_LOGS=true

# Or set as environment variable
FRONTEND_SHOW_VITE_LOGS=true uv run myfy run
```

**Theme Toggle:**
Click the moon/sun icon in the navbar to switch themes.

## Production Build

```bash
# Build optimized assets
npm run build

# Run in production mode
FRONTEND_ENVIRONMENT=production python app.py
```

## Customization

**Change theme colors:**
Edit `frontend/css/input.css`:
```css
@theme {
  --color-primary: #your-color;
}
```

**Add components:**
Create macros in `frontend/templates/components/` and import them.

**Add routes:**
Add more `@route.get()` handlers in `app.py`.
