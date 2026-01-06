# ADR-0010: CLI Module Design

## Status

Proposed

## Context

The myfy framework currently provides a CLI tool (`myfy`) for framework operations:
- `myfy run` - Start development server
- `myfy start` - Start production server
- `myfy routes`, `myfy modules`, `myfy doctor` - Introspection
- `myfy data *`, `myfy frontend *`, `myfy tasks *` - Module-specific operations

However, application developers need a way to define their own CLI commands for application-specific tasks:
- Database seeding and data management
- Administrative operations (create admin users, reset data)
- Scheduled task runners
- Development utilities (generate fixtures, clear caches)
- Deployment scripts and health checks

The challenge is designing a CliModule that:
1. Provides excellent developer experience (DX)
2. Integrates with myfy's DI system for accessing services
3. Coexists cleanly with the framework CLI
4. Follows the ergonomic patterns established by Typer
5. Adheres to myfy principles: "Sugar with substance", "Pythonic over ceremonial"

### Key Design Questions

1. **How should framework CLI and app CLI coexist?**
   - Should they be the same command (`myfy <command>`)?
   - Should app commands be a subcommand group (`myfy app <command>`)?
   - Should apps define their own entry point entirely?

2. **How should commands be defined?**
   - Decorator-based (like `@task`, `@route.get`)?
   - Class-based (like Django management commands)?
   - Function-based with registration?

3. **How should DI integration work?**
   - Should commands have access to the full DI container?
   - How do we handle async commands?
   - What about command-specific scopes?

## Decision

We will implement a CliModule with the following design:

### 1. Separation of Framework CLI and Application CLI

**Framework CLI (`myfy`)**: Remains unchanged for framework operations.

**Application CLI (`myfy app`)**: New subcommand group for application-defined commands. The `myfy app` namespace will:
- Auto-discover the application (like `myfy run` does)
- Initialize the application and DI container
- Execute commands registered via CliModule

**Custom Entry Point**: Applications can optionally define their own entry point for a cleaner CLI experience (e.g., `myapp seed-db` instead of `myfy app seed-db`).

### 2. Command Definition API

Commands are defined using a decorator-based approach inspired by Typer, but with DI integration:

```python
from myfy.cli import command, CliModule

# Simple command
@command
def greet(name: str) -> None:
    """Greet a user by name."""
    print(f"Hello, {name}!")

# Command with options
@command
def seed_db(
    count: int = 100,
    clear: bool = False,
) -> None:
    """Seed the database with test data."""
    if clear:
        print("Clearing existing data...")
    print(f"Creating {count} records...")

# Async command with DI
@command
async def create_admin(
    email: str,
    password: str,
    user_service: UserService,  # Injected from DI
) -> None:
    """Create an admin user."""
    await user_service.create_admin(email, password)
    print(f"Created admin: {email}")

# Command with explicit configuration
@command(name="run-migrations", help="Apply pending database migrations")
async def run_migrations(db: Database) -> None:
    """Run all pending migrations."""
    await db.migrate()
```

### 3. Parameter Resolution

Command parameters are resolved in this order:

1. **CLI Arguments/Options**: Standard Typer parameter parsing
   - Positional arguments → required CLI arguments
   - Parameters with defaults → optional CLI options
   - `bool` parameters → flags (--clear/--no-clear)

2. **DI Dependencies**: Parameters with type hints that match DI registrations
   - Resolved from the compiled DI container
   - Async commands run within proper scopes

3. **Special Parameters**:
   - `Application` → The myfy Application instance
   - `Container` → The DI container
   - `Console` → Rich Console for output

### 4. Module Architecture

```python
class CliModule:
    """
    CLI module - provides command-line command support.

    Lifecycle (per ADR-0005):
    - configure(): Register CommandRegistry in DI container
    - extend(): No-op
    - finalize(): Collect commands from all modules
    - start(): No-op (CLI is invoked separately)
    - stop(): No-op
    """

    @property
    def name(self) -> str:
        return "cli"

    @property
    def requires(self) -> list[type]:
        return []  # No hard dependencies

    @property
    def provides(self) -> list[type]:
        return [ICommandProvider]
```

### 5. Command Registry

```python
class CommandRegistry:
    """Global registry for CLI commands."""

    _instance: ClassVar[CommandRegistry | None] = None

    def __init__(self):
        self._commands: dict[str, Command] = {}

    @classmethod
    def get_instance(cls) -> CommandRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, command: Command) -> None:
        """Register a command."""
        self._commands[command.name] = command

    def get_commands(self) -> list[Command]:
        """Get all registered commands."""
        return list(self._commands.values())
```

### 6. Integration with Framework CLI

The framework CLI adds an `app` subcommand group:

```python
# In myfy_cli/main.py
from myfy_cli.commands.app import app_commands

app.add_typer(app_commands, name="app")
```

```python
# In myfy_cli/commands/app.py
app_commands = typer.Typer(help="Application-defined commands")

@app_commands.callback(invoke_without_command=True)
def app_callback(ctx: typer.Context):
    """Run application commands."""
    if ctx.invoked_subcommand is None:
        # List available commands
        list_commands()

def _build_typer_app() -> typer.Typer:
    """Build Typer app from registered commands."""
    # Discover application
    application, _, _ = find_application()
    application.initialize()

    # Get command registry
    registry = application.container.get(CommandRegistry)

    # Build Typer commands dynamically
    typer_app = typer.Typer()
    for cmd in registry.get_commands():
        typer_app.command(name=cmd.name, help=cmd.help)(
            _create_cli_wrapper(cmd, application)
        )

    return typer_app
```

### 7. Custom Entry Point Support

Applications can create their own CLI entry point:

```python
# myapp/cli.py
from myfy.cli import create_cli
from myapp import app

# Create a standalone Typer app with all registered commands
cli = create_cli(app)

if __name__ == "__main__":
    cli()
```

```toml
# pyproject.toml
[project.scripts]
myapp = "myapp.cli:cli"
```

### 8. Command Groups

Commands can be organized into groups:

```python
from myfy.cli import command, group

@group(name="users", help="User management commands")
class UserCommands:
    @command
    async def create(self, email: str, user_service: UserService) -> None:
        """Create a new user."""
        await user_service.create(email)

    @command
    async def delete(self, email: str, user_service: UserService) -> None:
        """Delete a user."""
        await user_service.delete(email)

# Usage: myfy app users create user@example.com
```

Or using sub-modules:

```python
# commands/users.py
from myfy.cli import command

@command(group="users")
async def create(email: str, user_service: UserService) -> None:
    """Create a new user."""
    ...
```

## Consequences

### Positive

- **Clean Separation**: Framework CLI and app CLI are clearly separated (`myfy` vs `myfy app`)
- **Familiar DX**: Follows Typer patterns that developers already know
- **DI Integration**: Commands have full access to application services
- **Flexible**: Can use `myfy app` or create custom entry point
- **Type-Safe**: Full type hints for parameters and DI
- **Async-First**: Native support for async commands
- **Discoverable**: `myfy app --help` lists all available commands

### Neutral

- **Learning Curve**: Developers need to understand DI parameter vs CLI parameter distinction
- **Initialization**: Application must be initialized before commands can run (slight startup overhead)

### Negative

- **Complexity**: More moving parts than a simple Typer app
- **Discovery Latency**: `myfy app` needs to import and initialize the app to discover commands
- **Testing**: Commands need the application context, making isolated testing slightly harder

## Alternatives Considered

### 1. Unified CLI (All commands under `myfy`)

```bash
myfy run          # Framework
myfy seed-db      # App command (mixed)
```

**Rejected** because:
- Namespace collisions between framework and app commands
- Confusing which commands are framework vs app-specific
- Framework commands should be stable; app commands are user-defined

### 2. Class-Based Commands (Django-style)

```python
class SeedDatabaseCommand(BaseCommand):
    name = "seed-db"
    help = "Seed the database"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100)

    def handle(self, count: int, db: Database):
        ...
```

**Rejected** because:
- More boilerplate than decorator approach
- Less Pythonic (violates principle #5)
- Doesn't match existing patterns (`@task`, `@route.get`)

### 3. Separate CLI Package (No Integration)

```python
# Developers write pure Typer apps
import typer
app = typer.Typer()

@app.command()
def seed_db():
    # Manually initialize myfy app
    from myapp import app
    app.initialize()
    db = app.container.get(Database)
    ...
```

**Rejected** because:
- Lots of boilerplate for DI access
- No integration with myfy lifecycle
- Every command needs manual initialization

### 4. Plugin-Based Discovery (Entry Points)

```toml
[project.entry-points."myfy.commands"]
seed-db = "myapp.commands:seed_db"
```

**Rejected** because:
- Requires modifying pyproject.toml for each command
- More friction than decorators
- Less intuitive for developers

## References

- [Typer Documentation](https://typer.tiangolo.com/)
- [Django Management Commands](https://docs.djangoproject.com/en/4.2/howto/custom-management-commands/)
- [Flask CLI](https://flask.palletsprojects.com/en/2.3.x/cli/)
- ADR-0005: Module Extension Points & Lifecycle Phases
- ADR-0009: Task Processing Module (similar decorator pattern)
