"""Task processing CLI commands for myfy."""

import asyncio
import sys

import klyne
import typer
from rich.console import Console
from rich.table import Table

# Check if tasks module is available
try:
    from myfy.tasks import TaskRegistry, TasksModule, TasksSettings, TaskWorker
    from myfy.tasks.models import TaskStatus

    HAS_TASKS = True
except ImportError:
    HAS_TASKS = False

tasks_app = typer.Typer(help="Task processing commands")
console = Console()


def _show_missing_module_error() -> None:
    """Display error message when tasks module is not installed."""
    console.print("[red]Tasks module not installed[/red]")
    console.print("")
    console.print("The myfy-tasks package is required for this command.")
    console.print("")
    console.print("[green]Install it with:[/green]")
    console.print("  pip install myfy-tasks")
    console.print("")
    console.print("[green]Or install all optional modules:[/green]")
    console.print("  pip install myfy[all]")


@tasks_app.command(name="worker")
def worker(
    concurrency: int | None = typer.Option(
        None,
        "--concurrency",
        "-c",
        help="Number of concurrent task executions",
    ),
    worker_id: str | None = typer.Option(
        None,
        "--worker-id",
        "-w",
        help="Unique worker identifier",
    ),
    app_path: str | None = typer.Option(
        None,
        "--app-path",
        "-a",
        help="Path to app directory",
    ),
) -> None:
    """
    Start a task worker process.

    The worker polls the database for pending tasks and executes them.

    Examples:
        myfy tasks worker
        myfy tasks worker --concurrency 8
        myfy tasks worker --worker-id worker-1
    """
    klyne.track(
        "myfy_tasks_worker",
        {
            "concurrency": concurrency,
            "worker_id": worker_id,
        },
    )

    if not HAS_TASKS:
        _show_missing_module_error()
        sys.exit(1)

    console.print("[cyan]Starting task worker...[/cyan]")

    # Import and discover application
    from pathlib import Path

    from myfy_cli.main import find_application

    search_dir = Path(app_path) if app_path else None
    application, _, _ = find_application(search_dir=search_dir)

    # Initialize application
    if not application._initialized:
        application.initialize()

    # Check for TasksModule
    try:
        tasks_module = application.get_module(TasksModule)
    except Exception:
        console.print("[red]Error: TasksModule not found[/red]")
        console.print("Add TasksModule() to your application")
        sys.exit(1)

    # Get settings
    settings = application.container.get(TasksSettings)

    # Override settings if provided via CLI
    if concurrency is not None:
        settings = settings.model_copy(update={"worker_concurrency": concurrency})
    if worker_id is not None:
        settings = settings.model_copy(update={"worker_id": worker_id})

    # Get dependencies
    from myfy.data import SessionFactory

    session_factory = application.container.get(SessionFactory)
    queue = tasks_module.get_queue()

    # Create worker
    task_worker = TaskWorker(
        container=application.container,
        settings=settings,
        queue=queue,
        session_factory=session_factory,
        worker_id=settings.worker_id,
    )

    console.print(f"[green]Worker {task_worker.worker_id} starting[/green]")
    console.print(f"  Concurrency: {settings.worker_concurrency}")
    console.print(f"  Poll interval: {settings.poll_interval}s")
    console.print("")

    # Run worker
    async def run_worker() -> None:
        # Start application modules
        await application.start()
        try:
            task_worker.setup_signal_handlers()
            await task_worker.run()
        finally:
            await application.stop()

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        console.print("\n[yellow]Worker stopped[/yellow]")


@tasks_app.command(name="list")
def list_tasks(
    app_path: str | None = typer.Option(
        None,
        "--app-path",
        "-a",
        help="Path to app directory",
    ),
) -> None:
    """
    List all registered tasks.

    Shows tasks that have been decorated with @task.

    Examples:
        myfy tasks list
    """
    klyne.track("myfy_tasks_list", {})

    if not HAS_TASKS:
        _show_missing_module_error()
        sys.exit(1)

    # Import and discover application to load tasks
    from pathlib import Path

    from myfy_cli.main import find_application

    search_dir = Path(app_path) if app_path else None
    application, _, _ = find_application(search_dir=search_dir)

    if not application._initialized:
        application.initialize()

    registry = TaskRegistry.get_instance()
    tasks = registry.get_all()

    if not tasks:
        console.print("[yellow]No tasks registered[/yellow]")
        console.print("Define tasks with the @task decorator")
        return

    table = Table(title="Registered Tasks")
    table.add_column("Name", style="cyan")
    table.add_column("Function", style="green")
    table.add_column("Max Retries", style="yellow")
    table.add_column("Has Context", style="magenta")

    for name, task_def in tasks.items():
        func = task_def.func
        func_qualname = getattr(func, "__qualname__", None) or getattr(func, "__name__", "unknown")
        func_name = f"{func.__module__}.{func_qualname}"
        table.add_row(
            name,
            func_name,
            str(task_def.max_retries or "default"),
            "Yes" if task_def.has_context else "No",
        )

    console.print(table)
    console.print(f"\nTotal: {len(tasks)} task(s)")


@tasks_app.command(name="stats")
def stats(
    app_path: str | None = typer.Option(
        None,
        "--app-path",
        "-a",
        help="Path to app directory",
    ),
) -> None:
    """
    Show task queue statistics.

    Displays counts of tasks by status.

    Examples:
        myfy tasks stats
    """
    klyne.track("myfy_tasks_stats", {})

    if not HAS_TASKS:
        _show_missing_module_error()
        sys.exit(1)

    from pathlib import Path

    from myfy_cli.main import find_application

    search_dir = Path(app_path) if app_path else None
    application, _, _ = find_application(search_dir=search_dir)

    if not application._initialized:
        application.initialize()

    async def get_stats() -> None:
        from myfy.data import SessionFactory

        await application.start()
        try:
            # Get tasks module
            try:
                tasks_module = application.get_module(TasksModule)
            except Exception:
                console.print("[red]Error: TasksModule not found[/red]")
                console.print("Add TasksModule() to your application")
                return

            session_factory = application.container.get(SessionFactory)
            queue = tasks_module.get_queue()

            async with session_factory.session_context() as session:
                stats_data = await queue.get_stats(session)

            console.print("[cyan]Task Queue Statistics:[/cyan]")
            console.print("")

            table = Table()
            table.add_column("Status", style="cyan")
            table.add_column("Count", style="green", justify="right")

            total = 0
            for status in TaskStatus:
                count = stats_data.get(status.value, 0)
                total += count
                table.add_row(status.value.capitalize(), str(count))

            console.print(table)
            console.print(f"\nTotal: {total} task(s)")

        finally:
            await application.stop()

    asyncio.run(get_stats())


@tasks_app.command(name="purge")
def purge(
    status: str = typer.Option(
        "completed",
        "--status",
        "-s",
        help="Status of tasks to purge (completed, failed, cancelled)",
    ),
    days: int = typer.Option(
        7,
        "--days",
        "-d",
        help="Purge tasks older than this many days",
    ),
    app_path: str | None = typer.Option(
        None,
        "--app-path",
        "-a",
        help="Path to app directory",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Purge old tasks from the queue.

    Removes completed, failed, or cancelled tasks older than specified days.

    Examples:
        myfy tasks purge                    # Purge completed tasks > 7 days old
        myfy tasks purge --status failed    # Purge failed tasks
        myfy tasks purge --days 30          # Purge tasks > 30 days old
        myfy tasks purge --force            # Skip confirmation
    """
    klyne.track("myfy_tasks_purge", {"status": status, "days": days})

    if not HAS_TASKS:
        _show_missing_module_error()
        sys.exit(1)

    # Validate status
    valid_statuses = ["completed", "failed", "cancelled"]
    if status not in valid_statuses:
        console.print(f"[red]Invalid status: {status}[/red]")
        console.print(f"Valid options: {', '.join(valid_statuses)}")
        sys.exit(1)

    if not force:
        console.print(f"[yellow]This will delete all {status} tasks older than {days} days.[/yellow]")
        if not typer.confirm("Continue?", default=False):
            console.print("Cancelled.")
            raise typer.Exit(0)

    from datetime import UTC, datetime, timedelta
    from pathlib import Path

    from sqlalchemy import and_, delete

    from myfy_cli.main import find_application

    search_dir = Path(app_path) if app_path else None
    application, _, _ = find_application(search_dir=search_dir)

    if not application._initialized:
        application.initialize()

    async def do_purge() -> None:
        from myfy.data import SessionFactory
        from myfy.tasks.models import TaskRecord

        await application.start()
        try:
            session_factory = application.container.get(SessionFactory)
            cutoff = datetime.now(UTC) - timedelta(days=days)

            async with session_factory.session_context() as session:
                stmt = delete(TaskRecord).where(
                    and_(
                        TaskRecord.status == status,
                        TaskRecord.completed_at < cutoff,
                    )
                )
                result = await session.execute(stmt)
                await session.commit()

                console.print(f"[green]Purged {result.rowcount} task(s)[/green]")

        finally:
            await application.stop()

    asyncio.run(do_purge())
