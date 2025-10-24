# ADR-0002: Modular Configuration Design

## Status

Accepted

## Context

The myfy framework is built around modularity (Principle #6: "Modular by design"). Each module (web, cli, data, auth) provides distinct functionality and should be independently configurable.

Traditional frameworks often suffer from:
1. **Monolithic configuration** - all settings in one massive file
2. **Tight coupling** - core framework knows about every module's settings
3. **Namespace pollution** - environment variables from different modules can conflict
4. **Poor separation of concerns** - adding a new module requires modifying core settings

For example, a centralized approach would look like:
```python
class CoreSettings:
    # Core
    app_name: str
    debug: bool
    # Web module
    host: str
    port: int
    cors_enabled: bool
    # Data module
    database_url: str
    # Auth module
    jwt_secret: str
```

This violates modularity and makes it hard to add, remove, or replace modules without touching the core.

## Decision

We will implement **module-owned configuration** where each module defines and manages its own settings class.

### Architecture

1. **Core Settings** (`myfy-core`) - minimal kernel configuration only
   - App name, debug mode, log level, shutdown timeout
   - No knowledge of module-specific settings

2. **Module Settings** (e.g., `myfy-web`, `myfy-data`) - each module defines its own
   - Module-specific configuration in module's package
   - Module-specific environment variable prefix (e.g., `MYFY_WEB_*`, `MYFY_DATA_*`)
   - Module loads and registers its own settings in `configure()`

3. **Settings Registration** - via dependency injection
   - Settings classes are registered as singletons in the DI container
   - Modules can depend on their own or other modules' settings via injection

### Implementation Pattern

```python
# myfy-web/myfy/web/config.py
class WebSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    cors_enabled: bool = False
    
    class Config:
        env_prefix = "MYFY_WEB_"  # Module-specific prefix

# myfy-web/myfy/web/module.py
class WebModule(BaseModule):
    def configure(self, container):
        # Module loads its own settings
        web_settings = load_settings(WebSettings)
        container.register(WebSettings, lambda: web_settings, scope=SINGLETON)
        
        # Use settings for other registrations
        # ...
```

### Benefits

1. **Namespace Isolation** - `MYFY_WEB_*` vs `MYFY_DATA_*` prevents conflicts
2. **Modularity** - modules are truly self-contained
3. **Dependency Inversion** - core doesn't depend on modules
4. **Discoverability** - settings defined where they're used
5. **Type Safety** - Pydantic validation + IDE autocomplete
6. **Testability** - easy to override module settings in tests

## Consequences

### Positive
- **Clean Separation**: Each module owns its configuration, no coupling to core
- **Easy Module Development**: New modules just define their settings class
- **No Conflicts**: Module-specific prefixes prevent environment variable collisions
- **Self-Documenting**: Settings are defined in the module they configure
- **Scalable**: Adding modules doesn't require changing core settings
- **Type-Safe**: Full Pydantic validation and type checking
- **Testable**: Can easily mock or override settings per module

### Neutral
- **Multiple Settings Classes**: Developers need to import the right settings class
- **Consistency Required**: Modules must follow the pattern (enforced by BaseModule)

### Negative
- **Initial Learning Curve**: Developers need to understand where each settings class lives
- **Slightly More Verbose**: Need to inject specific settings classes rather than one global config

## Alternatives Considered

### 1. Centralized Configuration
**Rejected** because:
- Violates modularity principle
- Core would need to know about all modules
- Hard to add/remove modules dynamically
- Namespace collisions inevitable
- Tight coupling between core and modules

### 2. Configuration Files per Module
**Rejected** because:
- Multiple config files are harder to manage
- 12-factor app principles favor environment variables
- Deployment complexity (multiple files to mount/manage)
- Harder to override in different environments

### 3. Dynamic Configuration Registry
**Rejected** because:
- Adds unnecessary complexity
- Type safety becomes harder
- No compile-time validation
- IDE support suffers
- Harder to test and reason about

### 4. Single Settings with Dynamic Sections
```python
class Settings:
    web: WebSettings
    data: DataSettings
```
**Rejected** because:
- Still requires core to know about all modules
- Modules can't be truly independent
- Doesn't solve namespace issues
- More complex than needed

## References

- [MODULAR_CONFIG.md](/Users/petru/workplace/myfy/MODULAR_CONFIG.md) - Detailed implementation guide
- [PRINCIPLES.md](/Users/petru/workplace/myfy/PRINCIPLES.md) - Principle #6: Modular by design
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - Settings management with Pydantic
- [12-Factor App: Config](https://12factor.net/config) - Environment-based configuration
