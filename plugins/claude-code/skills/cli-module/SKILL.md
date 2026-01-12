---
name: cli-module
description: myfy CliModule for custom CLI commands with DI injection. Use when working with CliModule, @cli.command decorator, command groups, CLI arguments, CLI options, or myfy app commands.
---

# CliModule - Custom CLI Commands

CliModule enables custom CLI commands with full dependency injection and Typer integration.

## Quick Start

```python
from myfy.core import Application
from myfy.commands import CliModule, cli

@cli.command()
async def seed_users(user_service: UserService, count: int = 10):
    '''Seed the database with test users.'''
    for i in range(count):
        await user_service.create(f"user{i}@example.com")
    print(f"Created {count} users")

app = Application()
app.add_module(CliModule())

# Run with: myfy app seed-users --count 20
```

## Configuration

Environment variables use the `MYFY_CLI_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `MYFY_CLI_VERBOSE` | `False` | Enable verbose output |
| `MYFY_CLI_NO_COLOR` | `False` | Disable colored output |
| `MYFY_CLI_TIMEOUT` | `300` | Command timeout (seconds) |

## Defining Commands

### Basic Command

```python
from myfy.commands import cli

@cli.command()
async def hello():
    '''Say hello.'''
    print("Hello, World!")

# Run: myfy app hello
```

### With DI Injection

Services are automatically injected:

```python
from myfy.commands import cli
from myfy.data import AsyncSession

@cli.command()
async def count_users(session: AsyncSession):
    '''Count users in the database.'''
    result = await session.execute(select(func.count(User.id)))
    count = result.scalar()
    print(f"Total users: {count}")

# Run: myfy app count-users
```

### With Arguments

```python
@cli.command()
async def greet(name: str):
    '''Greet someone by name.'''
    print(f"Hello, {name}!")

# Run: myfy app greet John
```

### With Options

```python
@cli.command()
async def seed(count: int = 10, verbose: bool = False):
    '''Seed the database.'''
    for i in range(count):
        if verbose:
            print(f"Creating user {i + 1}/{count}")
        await create_user(i)
    print(f"Created {count} users")

# Run: myfy app seed --count 50 --verbose
```

## Command Groups

Organize related commands:

```python
from myfy.commands import cli

# Create a group
db = cli.group("db")

@db.command()
async def seed(session: AsyncSession):
    '''Seed the database.'''
    await seed_data(session)

@db.command()
async def reset(session: AsyncSession, force: bool = False):
    '''Reset the database.'''
    if force or confirm("Are you sure?"):
        await reset_data(session)

# Run: myfy app db:seed
#      myfy app db:reset --force
```

## Typer Integration

Use Typer for advanced CLI features:

```python
import typer
from myfy.commands import cli

@cli.command()
async def import_data(
    db: Database,  # DI injection
    file: str = typer.Argument(..., help="Path to import file"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Simulate import"),
    format: str = typer.Option("json", "--format", "-f", help="File format"),
):
    '''Import data from a file.'''
    if dry_run:
        print(f"Would import from {file} ({format} format)")
    else:
        await db.import_from_file(file, format)

# Run: myfy app import-data users.csv --format csv --dry-run
```

### Typer Features

```python
import typer

@cli.command()
async def deploy(
    # Required argument
    env: str = typer.Argument(..., help="Target environment"),
    # Optional with short form
    version: str = typer.Option(None, "--version", "-v"),
    # Boolean flag
    skip_tests: bool = typer.Option(False, "--skip-tests"),
    # Choice from enum
    region: Region = typer.Option(Region.US, "--region", "-r"),
):
    '''Deploy the application.'''
    ...

# Run: myfy app deploy production -v 1.2.3 --skip-tests --region eu
```

## Parameter Classification

Parameters are automatically classified:

| Pattern | Classification |
|---------|---------------|
| `typer.Argument(...)` | CLI positional argument |
| `typer.Option(...)` | CLI option/flag |
| Primitive with default | CLI option |
| Primitive without default | CLI argument |
| Complex type | DI dependency |

```python
@cli.command()
async def process(
    file: str,                    # CLI argument (required)
    count: int = 10,              # CLI option (--count)
    verbose: bool = False,        # CLI flag (--verbose)
    session: AsyncSession,        # DI injection
    settings: AppSettings,        # DI injection
):
    ...
```

## Custom Command Names

```python
@cli.command(name="import-users")  # Explicit name
async def import_users_handler(file: str):
    '''Import users from file.'''
    ...

# Run: myfy app import-users users.csv
```

Function name `import_users_handler` becomes command name `import-users` by default (underscores to hyphens).

## Async vs Sync

Both async and sync handlers are supported:

```python
# Async (recommended)
@cli.command()
async def async_task(session: AsyncSession):
    await session.execute(...)

# Sync (also works)
@cli.command()
def sync_task(settings: AppSettings):
    print(settings.app_name)
```

## Error Handling

```python
@cli.command()
async def risky_operation(session: AsyncSession):
    '''Perform a risky operation.'''
    try:
        await do_risky_thing(session)
    except RiskyError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
```

## Progress and Output

```python
import typer

@cli.command()
async def process_files(files: list[str]):
    '''Process multiple files.'''
    with typer.progressbar(files) as progress:
        for file in progress:
            await process_file(file)

    typer.echo(typer.style("Done!", fg=typer.colors.GREEN))
```

## Running Commands

```bash
# List available commands
myfy app --help

# Run a command
myfy app seed-users

# With options
myfy app seed-users --count 50

# Grouped command
myfy app db:reset --force

# With arguments
myfy app import users.csv
```

## Best Practices

1. **Use docstrings** - Become command help text
2. **Group related commands** - Easier to discover
3. **Use Typer for complex args** - Better help messages
4. **Handle errors gracefully** - Use `typer.Exit(1)` for failures
5. **Show progress** - Use `typer.progressbar` for long operations
6. **Inject services** - Don't create DB connections manually
7. **Keep commands focused** - One task per command
