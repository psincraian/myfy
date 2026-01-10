"""
End-to-end tests for CLI commands module.

These tests verify the complete flow:
- Command definition with @cli.command decorator
- Integration with myfy Application
- Full lifecycle: initialize -> start -> execute -> stop
- DI injection in command handlers
- Command groups
- Async and sync command execution
"""

from typing import cast

import pytest
from myfy.core.di import SINGLETON, Container
from myfy.core.kernel import Application, Module

from myfy.commands import (
    CliModule,
    CliRouter,
    CommandExecutionError,
    CommandRegistry,
)

pytestmark = pytest.mark.e2e


# =============================================================================
# Test Services (simulate real dependencies)
# =============================================================================


class UserRepository:
    """Repository for user data."""

    def __init__(self):
        self._users: list[dict] = []

    def add(self, email: str) -> dict:
        user = {"id": len(self._users) + 1, "email": email}
        self._users.append(user)
        return user

    def get_all(self) -> list[dict]:
        return self._users.copy()

    def count(self) -> int:
        return len(self._users)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.sent_emails: list[dict] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent_emails.append({"to": to, "subject": subject, "body": body})


class DatabaseService:
    """Database connection service."""

    def __init__(self):
        self.connected = False
        self.operations: list[str] = []

    async def connect(self) -> None:
        self.connected = True
        self.operations.append("connect")

    async def disconnect(self) -> None:
        self.connected = False
        self.operations.append("disconnect")

    async def seed(self, table: str, count: int) -> int:
        self.operations.append(f"seed:{table}:{count}")
        return count


# =============================================================================
# Test Module (provides services)
# =============================================================================


class MockServicesModule:
    """Module that provides test services for DI."""

    def __init__(self):
        self.user_repo = UserRepository()
        self.email_service = EmailService()
        self.db_service = DatabaseService()

    @property
    def name(self) -> str:
        return "test-services"

    def configure(self, container: Container) -> None:
        container.register(
            type_=UserRepository,
            factory=lambda: self.user_repo,
            scope=SINGLETON,
        )
        container.register(
            type_=EmailService,
            factory=lambda: self.email_service,
            scope=SINGLETON,
        )
        container.register(
            type_=DatabaseService,
            factory=lambda: self.db_service,
            scope=SINGLETON,
        )

    async def start(self) -> None:
        await self.db_service.connect()

    async def stop(self) -> None:
        await self.db_service.disconnect()


def as_module(obj: object) -> Module:
    """Cast test module to Module protocol for type checker."""
    return cast("Module", obj)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset command registry before each test."""
    CommandRegistry.reset_instance()
    yield
    CommandRegistry.reset_instance()


@pytest.fixture
def services_module():
    """Create test services module."""
    return MockServicesModule()


@pytest.fixture
def cli_router():
    """Create a fresh CLI router for each test."""
    return CliRouter()


# =============================================================================
# Basic Command Execution Tests
# =============================================================================


class TestBasicCommandExecution:
    """Test basic command definition and execution."""

    @pytest.mark.asyncio
    async def test_simple_command_with_di(self, services_module, cli_router):
        """Test a simple command with DI injection."""
        execution_log: list[str] = []

        @cli_router.command()
        async def list_users(user_repo: UserRepository):
            """List all users."""
            users = user_repo.get_all()
            execution_log.append(f"listed:{len(users)}")
            return users

        # Set up application
        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        # Add some users to repo
        services_module.user_repo.add("alice@example.com")
        services_module.user_repo.add("bob@example.com")

        # Execute command
        cli_module = app.get_module(CliModule)
        command = cli_module.get_registry().get("list-users")
        result = await cli_module.get_executor().execute_async(command, {})

        assert len(result) == 2  # noqa: PLR2004
        assert result[0]["email"] == "alice@example.com"
        assert "listed:2" in execution_log

    @pytest.mark.asyncio
    async def test_command_with_cli_args_and_di(self, services_module, cli_router):
        """Test command with both CLI arguments and DI injection."""

        @cli_router.command()
        async def create_users(user_repo: UserRepository, count: int = 5):
            """Create test users."""
            created = []
            for i in range(count):
                user = user_repo.add(f"user{i}@example.com")
                created.append(user)
            return created

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        cli_module = app.get_module(CliModule)
        command = cli_module.get_registry().get("create-users")

        # Execute with custom count
        result = await cli_module.get_executor().execute_async(command, {"count": 3})

        assert len(result) == 3  # noqa: PLR2004
        assert services_module.user_repo.count() == 3  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_sync_command_execution(self, services_module, cli_router):
        """Test synchronous command execution."""

        @cli_router.command()
        def get_user_count(user_repo: UserRepository) -> int:
            """Get total user count."""
            return user_repo.count()

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        # Add users
        services_module.user_repo.add("test@example.com")

        cli_module = app.get_module(CliModule)
        command = cli_module.get_registry().get("get-user-count")

        # Sync commands work via async executor too
        result = await cli_module.get_executor().execute_async(command, {})

        assert result == 1


# =============================================================================
# Command Groups Tests
# =============================================================================


class TestCommandGroups:
    """Test command groups functionality."""

    @pytest.mark.asyncio
    async def test_grouped_commands(self, services_module, cli_router):
        """Test commands in groups."""
        db = cli_router.group("db")

        @db.command()
        async def seed(db_service: DatabaseService, table: str = "users"):
            """Seed database table."""
            count = await db_service.seed(table, 100)  # noqa: PLR2004
            return f"Seeded {count} rows in {table}"

        @db.command()
        async def status(db_service: DatabaseService):
            """Check database status."""
            return {"connected": db_service.connected, "ops": len(db_service.operations)}

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        # Start the app to connect DB
        await app.start()

        try:
            cli_module = app.get_module(CliModule)
            registry = cli_module.get_registry()

            # Verify commands are registered with group prefix
            assert "db:seed" in registry
            assert "db:status" in registry

            # Execute db:seed
            seed_cmd = registry.get("db:seed")
            result = await cli_module.get_executor().execute_async(seed_cmd, {"table": "products"})
            assert "products" in result

            # Execute db:status
            status_cmd = registry.get("db:status")
            status = await cli_module.get_executor().execute_async(status_cmd, {})
            assert status["connected"] is True
        finally:
            await app.stop()


# =============================================================================
# Full Lifecycle Tests
# =============================================================================


class TestFullLifecycle:
    """Test commands with full application lifecycle."""

    @pytest.mark.asyncio
    async def test_command_with_full_lifecycle(self, services_module, cli_router):
        """Test command execution with start/stop lifecycle."""

        @cli_router.command()
        async def db_operation(db_service: DatabaseService):
            """Perform database operation."""
            # This should only work when DB is connected
            if not db_service.connected:
                return "ERROR: Not connected"
            await db_service.seed("test", 10)  # noqa: PLR2004
            return "OK"

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        cli_module = app.get_module(CliModule)
        command = cli_module.get_registry().get("db-operation")

        # Without start, DB is not connected
        result_before = await cli_module.get_executor().execute_async(command, {})
        assert "Not connected" in result_before

        # With proper lifecycle
        await app.start()
        try:
            result_after = await cli_module.get_executor().execute_async(command, {})
            assert result_after == "OK"
            assert services_module.db_service.connected
        finally:
            await app.stop()

        # After stop, DB should be disconnected
        assert not services_module.db_service.connected

    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self, services_module, cli_router):
        """Test command execution within lifespan context."""

        @cli_router.command()
        async def check_db(db_service: DatabaseService) -> bool:
            """Check if DB is connected."""
            return db_service.connected

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        cli_module = app.get_module(CliModule)
        command = cli_module.get_registry().get("check-db")

        lifespan = app.create_lifespan()
        async with lifespan(None):
            result = await cli_module.get_executor().execute_async(command, {})
            assert result is True

        # After context, should be disconnected
        assert not services_module.db_service.connected


# =============================================================================
# Multiple Dependencies Tests
# =============================================================================


class TestMultipleDependencies:
    """Test commands with multiple DI dependencies."""

    @pytest.mark.asyncio
    async def test_command_with_multiple_services(self, services_module, cli_router):
        """Test command that uses multiple services."""

        @cli_router.command()
        async def create_and_notify(
            user_repo: UserRepository,
            email_service: EmailService,
            count: int = 1,
        ):
            """Create users and send welcome emails."""
            created = []
            for i in range(count):
                email = f"newuser{i}@example.com"
                user = user_repo.add(email)
                email_service.send(to=email, subject="Welcome!", body=f"Hello user {user['id']}!")
                created.append(user)
            return {"users": len(created), "emails": len(email_service.sent_emails)}

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        cli_module = app.get_module(CliModule)
        command = cli_module.get_registry().get("create-and-notify")

        result = await cli_module.get_executor().execute_async(command, {"count": 3})

        assert result["users"] == 3  # noqa: PLR2004
        assert result["emails"] == 3  # noqa: PLR2004
        assert len(services_module.email_service.sent_emails) == 3  # noqa: PLR2004


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in command execution."""

    @pytest.mark.asyncio
    async def test_command_exception_is_wrapped(self, services_module, cli_router):
        """Test that command exceptions are properly wrapped."""

        @cli_router.command()
        async def failing_command():
            """A command that fails."""
            raise ValueError("Intentional failure")

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        cli_module = app.get_module(CliModule)
        command = cli_module.get_registry().get("failing-command")

        with pytest.raises(CommandExecutionError) as exc_info:
            await cli_module.get_executor().execute_async(command, {})

        assert "Intentional failure" in str(exc_info.value.cause)


# =============================================================================
# Registry Integration Tests
# =============================================================================


class TestRegistryIntegration:
    """Test command registry integration with application."""

    def test_commands_registered_after_init(self, services_module, cli_router):
        """Test that commands are available in registry after app init."""

        @cli_router.command()
        async def cmd_one():
            pass

        @cli_router.command()
        async def cmd_two():
            pass

        @cli_router.command(name="custom-name")
        async def cmd_three():
            pass

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        cli_module = app.get_module(CliModule)
        registry = cli_module.get_registry()

        assert "cmd-one" in registry
        assert "cmd-two" in registry
        assert "custom-name" in registry
        assert len(registry) == 3  # noqa: PLR2004

    def test_commands_compiled_after_finalize(self, services_module, cli_router):
        """Test that all commands are compiled after finalize phase."""

        @cli_router.command()
        async def test_cmd():
            pass

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        cli_module = app.get_module(CliModule)
        executor = cli_module.get_executor()

        # Command should be compiled
        assert executor.is_compiled("test-cmd")


# =============================================================================
# Real-world Scenario Tests
# =============================================================================


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_data_seeding_workflow(self, services_module, cli_router):
        """Test a realistic data seeding workflow."""
        db = cli_router.group("db")

        @db.command()
        async def seed_all(
            user_repo: UserRepository,
            db_service: DatabaseService,
            users: int = 10,
            products: int = 50,
        ):
            """Seed all database tables."""
            results = []

            # Seed users
            for i in range(users):
                user_repo.add(f"seed_user_{i}@example.com")
            results.append(f"Created {users} users")

            # Seed products via DB service
            await db_service.seed("products", products)
            results.append(f"Seeded {products} products")

            return results

        @db.command()
        async def reset(db_service: DatabaseService, force: bool = False):
            """Reset database."""
            if not force:
                return "Use --force to confirm reset"
            db_service.operations.append("reset")
            return "Database reset complete"

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        await app.start()
        try:
            cli_module = app.get_module(CliModule)

            # Run seed command
            seed_cmd = cli_module.get_registry().get("db:seed-all")
            result = await cli_module.get_executor().execute_async(
                seed_cmd, {"users": 5, "products": 20}
            )

            assert "Created 5 users" in result
            assert "Seeded 20 products" in result
            assert services_module.user_repo.count() == 5  # noqa: PLR2004

            # Run reset without force
            reset_cmd = cli_module.get_registry().get("db:reset")
            result = await cli_module.get_executor().execute_async(reset_cmd, {})
            assert "--force" in result

            # Run reset with force
            result = await cli_module.get_executor().execute_async(reset_cmd, {"force": True})
            assert "complete" in result
        finally:
            await app.stop()

    @pytest.mark.asyncio
    async def test_admin_operations(self, services_module, cli_router):
        """Test admin CLI operations."""
        admin = cli_router.group("admin")

        @admin.command()
        async def create_admin(
            user_repo: UserRepository,
            email_service: EmailService,
            email: str = "admin@example.com",
        ):
            """Create an admin user."""
            user = user_repo.add(email)
            email_service.send(
                to=email,
                subject="Admin Account Created",
                body=f"Your admin account (ID: {user['id']}) has been created.",
            )
            return user

        @admin.command()
        async def list_admins(user_repo: UserRepository):
            """List all admin users."""
            return user_repo.get_all()

        app = Application(auto_discover=False)
        app.add_module(as_module(services_module))
        app.add_module(as_module(CliModule()))
        app.initialize()

        cli_module = app.get_module(CliModule)

        # Create admin
        create_cmd = cli_module.get_registry().get("admin:create-admin")
        admin_user = await cli_module.get_executor().execute_async(
            create_cmd, {"email": "super@admin.com"}
        )

        assert admin_user["email"] == "super@admin.com"
        assert len(services_module.email_service.sent_emails) == 1

        # List admins
        list_cmd = cli_module.get_registry().get("admin:list-admins")
        admins = await cli_module.get_executor().execute_async(list_cmd, {})

        assert len(admins) == 1
        assert admins[0]["email"] == "super@admin.com"
