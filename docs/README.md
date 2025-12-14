# myfy Documentation

This directory contains the source files for myfy's documentation.

## Building Locally

### Install Dependencies

```bash
uv sync --group docs
uv pip install -e packages/myfy-core -e packages/myfy-web -e packages/myfy-cli
```

### Serve Documentation

```bash
# Start local server with hot reload
uv run mkdocs serve

# View at http://localhost:8000
```

### Build Static Site

```bash
# Build to site/ directory
uv run mkdocs build
```

## Deploying to GitHub Pages

### First Time Setup

```bash
# Deploy manually
uv run mkdocs gh-deploy
```

### Automatic Deployment

The documentation automatically deploys to GitHub Pages on every push to `main` that modifies:
- `docs/**` files
- `mkdocs.yml`
- Package source code (for API reference)

See `.github/workflows/docs.yml` for the deployment workflow.

## Documentation Structure

```
docs/
├── index.md                  # Landing page
├── getting-started/          # Installation & tutorials
│   ├── installation.md
│   ├── tutorial.md
│   └── quick-reference.md
├── core-concepts/            # Deep dives
│   ├── dependency-injection.md
│   ├── modules.md
│   ├── configuration.md
│   └── lifecycle.md
├── modules/                  # Module documentation
│   ├── core.md
│   ├── web.md
│   ├── cli.md
│   ├── data.md
│   └── frontend.md
├── adr/                      # Architecture Decision Records
│   └── *.md
├── deployment.md             # Deployment guide
└── contributing.md           # Contribution guide
```

## Writing Documentation

### Style Guide

- Use clear, simple language
- Include code examples for every concept
- Add TL;DR boxes for experienced developers
- Use comparison tables where helpful
- Keep paragraphs short and scannable

### Code Examples

Always include complete, runnable code examples:

```python
from myfy.core import Application
from myfy.web import route, WebModule

@route.get("/")
async def index() -> dict:
    return {"message": "Hello!"}

app = Application(settings_class=Settings, auto_discover=False)
app.add_module(WebModule())
```

### Admonitions

Use admonitions for important notes:

```markdown
!!! tip "Performance Tip"
    Use connection pooling for database connections.

!!! warning "Security Warning"
    Never commit secrets to version control.

!!! note
    This feature requires myfy-web 0.2.0+
```

## Technology

- **MkDocs**: Static site generator
- **Material for MkDocs**: Theme
- **mkdocstrings**: API reference generation from docstrings
- **GitHub Pages**: Hosting

## Links

- [Live Documentation](https://myfy.dev)
- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
