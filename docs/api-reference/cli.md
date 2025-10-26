# CLI API Reference

API reference for `myfy-cli` package.

---

## Commands

The `myfy` CLI provides the following commands:

### run

Start the development server.

```bash
myfy run [OPTIONS]
```

**Options:**
- `--host TEXT`: Server host (default: 127.0.0.1)
- `--port INTEGER`: Server port (default: 8000)
- `--reload / --no-reload`: Enable auto-reload (default: True)
- `--app-path TEXT`: Path to app (e.g., main:app)

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
