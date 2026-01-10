"""CLI command modules for myfy."""

from myfy_cli.commands.data import data_app
from myfy_cli.commands.frontend import frontend_app
from myfy_cli.commands.tasks import tasks_app
from myfy_cli.commands.user import user_app

__all__ = ["data_app", "frontend_app", "tasks_app", "user_app"]
