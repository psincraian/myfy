# myfy-commands

CLI commands module for the myfy framework.

## Installation

```bash
pip install myfy-commands
```

## Usage

```python
from myfy.core import Application
from myfy.commands import CliModule, cli

@cli.command()
async def seed_users(user_service: UserService, count: int = 10):
    """Seed the database with test users."""
    for i in range(count):
        await user_service.create(f"user{i}@example.com")

app = Application()
app.add_module(CliModule())
```

Run commands with:

```bash
myfy app seed-users --count 20
```

## Command Groups

```python
from myfy.commands import cli

db = cli.group("db")

@db.command()
async def seed(db: Database):
    """Seed the database."""
    await db.seed()

@db.command()
async def reset(db: Database, force: bool = False):
    """Reset the database."""
    if force:
        await db.reset()
```

Run grouped commands:

```bash
myfy app db:seed
myfy app db:reset --force
```
