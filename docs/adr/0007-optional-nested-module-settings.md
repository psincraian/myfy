# ADR-0007: Optional Nested Module Settings

## Status

Accepted

## Context

ADR-0002 established the **module-owned configuration** pattern where each module defines and manages its own settings class with its own environment variable prefix (e.g., `MYFY_WEB_*`, `MYFY_FRONTEND_*`). This provides excellent modularity and namespace isolation.

However, some developers prefer to define all settings in a **single unified settings class** for:
1. **Single source of truth** - All configuration in one place
2. **Type safety** - Full IDE autocomplete and type checking across all settings
3. **Easier testing** - Override all settings through one object
4. **Convenience** - Don't need to inject multiple settings classes

The challenge is to support this preference while:
- Maintaining ADR-0002's modularity principles
- Preserving existing environment variable conventions
- Ensuring backward compatibility
- Not forcing this pattern on users who prefer separate settings

## Decision

We will support **optional nested module settings** as an alternative pattern alongside the existing separate settings approach.

### Pattern: Nested Module Settings

Users can define module settings as nested Pydantic models within their application settings:

```python
from myfy.core import Application, BaseSettings
from myfy.web import WebModule, WebSettings
from myfy.frontend import FrontendModule, FrontendSettings
from pydantic import Field

class AppSettings(BaseSettings):
    """Unified application settings with nested module settings"""

    # App-specific settings
    app_name: str = Field(default="My App")
    greeting: str = Field(default="Hello")

    # Nested module settings
    web: WebSettings = Field(default_factory=WebSettings)
    frontend: FrontendSettings = Field(default_factory=FrontendSettings)

app = Application(settings_class=AppSettings)
app.add_module(WebModule())
app.add_module(FrontendModule())
```

### How It Works

1. **Application initialization** detects nested module settings in the user's settings class
2. **Extracts nested settings** and registers them in the DI container
3. **Modules check the container first** for their settings before loading standalone
4. **Environment variables work identically**: `MYFY_WEB_PORT=3000` sets the port in both patterns

### Environment Variable Handling

**Critical:** Existing environment variable conventions are **unchanged**:

```bash
# These work identically for both patterns
MYFY_WEB_PORT=3000
MYFY_WEB_HOST=0.0.0.0
MYFY_WEB_CORS_ENABLED=true

MYFY_FRONTEND_ENVIRONMENT=production
MYFY_FRONTEND_TEMPLATES_DIR=/app/templates
```

Pydantic automatically handles nested model loading with the existing `MYFY_WEB_*` prefix when the `env_prefix` is set on the nested model.

### Both Patterns Are Valid

**Pattern 1: Separate Settings (Current, Still Supported)**
```python
class AppSettings(BaseSettings):
    app_name: str = "My App"

app = Application(settings_class=AppSettings)
app.add_module(WebModule())  # Loads standalone WebSettings
```

**Pattern 2: Nested Settings (New, Optional)**
```python
class AppSettings(BaseSettings):
    app_name: str = "My App"
    web: WebSettings = Field(default_factory=WebSettings)

app = Application(settings_class=AppSettings)
app.add_module(WebModule())  # Uses AppSettings.web
```

Both patterns:
- Are fully type-safe
- Use the same environment variables
- Support the same functionality
- Are equally valid choices

## Implementation Details

### Application Class Changes

The `Application` class will:
1. After registering user settings, inspect it for nested module settings
2. For each nested setting that is a `BaseSettings` subclass, register it in the container
3. Use the nested instance directly (already loaded with env vars by Pydantic)

### Module Class Changes

Modules will:
1. Check if their settings class is already registered in the container
2. If found, use the existing instance (from nested app settings)
3. If not found, fall back to current behavior: `load_settings(ModuleSettings)`

This ensures zero breaking changes.

## Consequences

### Positive

- **Developer choice**: Users can choose the pattern that fits their needs
- **Type safety**: Single class provides full autocomplete and type checking
- **Zero breaking changes**: Existing code continues to work unchanged
- **Consistent env vars**: No new environment variable conventions to learn
- **Modularity preserved**: Modules remain independent and self-contained
- **Easy testing**: Can override all settings through one object

### Neutral

- **Two valid patterns**: Developers need to choose which they prefer
- **Documentation burden**: Need to document both approaches clearly

### Negative

- **Slightly more complex initialization**: Application needs to detect and register nested settings
- **Module coupling risk**: Developers might abuse nested settings to tightly couple modules (mitigated by keeping both patterns valid)

## Alternatives Considered

### 1. Settings Inheritance

```python
class AppSettings(CoreSettings, WebSettings, FrontendSettings):
    pass
```

**Rejected** because:
- Python's MRO makes this fragile
- Cannot compose settings from multiple modules cleanly
- Namespace collisions inevitable
- Violates ADR-0002's separation of concerns

### 2. Settings Registry Pattern

```python
settings_registry = {
    "app": AppSettings(),
    "web": WebSettings(),
    "frontend": FrontendSettings()
}
```

**Rejected** because:
- Loses type safety
- No IDE autocomplete
- More verbose to use
- Doesn't solve the "single class" requirement

### 3. Require Nested Settings

**Rejected** because:
- Breaking change
- Removes developer choice
- ADR-0002's separation is valuable for large projects
- Would require updating all examples and docs

### 4. New Environment Variable Convention

Using `WEB__PORT` (double underscore) for nested settings.

**Rejected** because:
- Breaking change for existing deployments
- Pydantic supports existing prefixes with nested models
- Adds cognitive overhead (two conventions to remember)
- No clear benefit over existing `MYFY_WEB_*` pattern

## Migration Guide

### For Users

**If you prefer the current pattern:**
- No changes needed
- Continue using separate settings classes
- Everything works exactly as before

**If you want nested settings:**
```python
# Before
class AppSettings(BaseSettings):
    app_name: str = "My App"

app = Application(settings_class=AppSettings)
app.add_module(WebModule())

# After
class AppSettings(BaseSettings):
    app_name: str = "My App"
    web: WebSettings = Field(default_factory=WebSettings)  # Add nested

app = Application(settings_class=AppSettings)
app.add_module(WebModule())  # No change needed!
```

Environment variables remain identical:
```bash
# Before and After - same env vars
MYFY_APP_NAME=My App
MYFY_WEB_PORT=3000
MYFY_WEB_HOST=0.0.0.0
```

### For Module Developers

Modules should update their `configure()` method to check the container first:

```python
# Before
def configure(self, container) -> None:
    web_settings = load_settings(WebSettings)
    container.register(WebSettings, lambda: web_settings, scope=SINGLETON)

# After
def configure(self, container) -> None:
    # Check if already registered (from nested app settings)
    try:
        web_settings = container.get(WebSettings)
    except Exception:
        # Not found, load standalone (backward compatibility)
        web_settings = load_settings(WebSettings)
        container.register(WebSettings, lambda: web_settings, scope=SINGLETON)
```

## References

- [ADR-0002: Modular Configuration Design](/Users/petru/workplace/myfy/docs/adr/0002-modular-configuration-design.md)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Pydantic Nested Models](https://docs.pydantic.dev/latest/concepts/models/#nested-models)

## Examples

See:
- `examples/hello/` - Current separate settings pattern
- `examples/nested-settings/` - New nested settings pattern
