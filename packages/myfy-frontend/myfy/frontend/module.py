"""Frontend module for myfy."""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from starlette.templating import Jinja2Templates

from myfy.core.config import load_settings
from myfy.core.di import SINGLETON

from .assets import AssetResolver
from .config import FrontendSettings
from .process import ProcessManager
from .scaffold import check_frontend_initialized, scaffold_frontend
from .static_files import CachedStaticFiles
from .templates import create_templates_instance

if TYPE_CHECKING:
    from myfy.core.di import Container

logger = logging.getLogger(__name__)


class FrontendModule:
    """
    Frontend module - DaisyUI + Tailwind 4 + Vite + Jinja2.

    Features:
    - Server-side rendering with Jinja2
    - DaisyUI 5 component library
    - Tailwind 4 with native CSS engine
    - Vite for asset bundling with HMR
    - Auto-scaffolding on first run
    - Theme switcher (light/dark mode)

    Example:
        >>> from myfy.core import Application
        >>> from myfy.web import WebModule
        >>> from myfy.frontend import FrontendModule
        >>>
        >>> app = Application(auto_discover=False)
        >>> app.add_module(WebModule())
        >>> app.add_module(FrontendModule())  # Auto-scaffolds!
    """

    def __init__(
        self,
        templates_dir: str = "frontend/templates",
        static_dir: str = "frontend/static",
        auto_init: bool = False,
    ):
        """
        Initialize frontend module.

        Args:
            templates_dir: Path to templates directory
            static_dir: Path to static files directory
            auto_init: Auto-scaffold if directories don't exist (default: False)
        """
        self.templates_dir = templates_dir
        self.static_dir = static_dir
        self.auto_init = auto_init
        self._vite_manager = ProcessManager(name="Vite")
        self.templates: Jinja2Templates | None = None
        self._container: Container | None = None

    @property
    def name(self) -> str:
        """Module name."""
        return "frontend"

    @property
    def requires(self) -> list[type]:
        """
        FrontendModule requires WebModule for ASGI app.

        This ensures WebModule is loaded and initialized before FrontendModule.
        """
        from myfy.web import WebModule  # noqa: PLC0415

        return [WebModule]

    @property
    def provides(self) -> list[type]:
        """
        FrontendModule implements IWebExtension protocol.

        This allows it to extend the ASGI application during finalization.
        """
        from myfy.web import IWebExtension  # noqa: PLC0415

        return [IWebExtension]

    def configure(self, container: "Container") -> None:
        """
        Configure frontend module in DI container.

        Registers:
        - FrontendSettings
        - AssetResolver
        - Jinja2Templates

        Note: In nested settings pattern (ADR-0007), FrontendSettings is registered
        by Application. Otherwise, load standalone FrontendSettings.
        """
        from myfy.core.di.types import ProviderKey  # noqa: PLC0415

        # Store container reference for start()
        self._container = container

        # Check if FrontendSettings already registered (from nested app settings)
        key = ProviderKey(FrontendSettings)
        if key not in container._providers:
            # Load standalone FrontendSettings
            settings = load_settings(FrontendSettings)
            container.register(
                type_=FrontendSettings,
                factory=lambda: settings,
                scope=SINGLETON,
            )

        # Load settings for use in this method (before container is compiled)
        settings = load_settings(FrontendSettings)

        # Scaffold if needed
        if self.auto_init and not check_frontend_initialized(self.templates_dir):
            logger.info("Frontend not initialized, scaffolding...")
            scaffold_frontend(
                _templates_dir=self.templates_dir,
                _static_dir=self.static_dir,
            )

        # Verify templates directory exists
        templates_path = Path(self.templates_dir)
        if not templates_path.exists():
            logger.error(f"Templates directory not found: {self.templates_dir}")
            logger.error("")
            logger.error("To initialize frontend, either:")
            logger.error("  1. Set auto_init=True: FrontendModule(auto_init=True)")
            logger.error("  2. Or manually create frontend structure")
            sys.exit(1)

        # Register asset resolver
        asset_resolver = AssetResolver(
            static_dir=self.static_dir,
            settings=settings,
        )
        container.register(
            type_=AssetResolver,
            factory=lambda: asset_resolver,
            scope=SINGLETON,
        )

        # Create and register templates in DI container
        templates = create_templates_instance(
            directory=self.templates_dir,
            settings=settings,
            asset_resolver=asset_resolver,
        )

        # Register templates as singleton in DI container
        container.register(
            type_=Jinja2Templates,
            factory=lambda: templates,
            scope=SINGLETON,
        )

        # Store templates as instance attribute for convenience access
        self.templates = templates

    def finalize(self, container: "Container") -> None:
        """
        Finalize frontend module after container compilation.

        Called after container is compiled in normal application flow.
        Mounts static files to the ASGI app.

        Note: In CLI/factory contexts, extend_asgi_app() is used instead.
        """
        from myfy.web import ASGIApp  # noqa: PLC0415

        asgi_app = container.get(ASGIApp)
        self._mount_static_files(asgi_app.app, container)

    def extend_asgi_app(self, app, container: "Container") -> None:
        """
        Extend ASGI app for CLI/factory contexts.

        This is called by the factory pattern when creating ASGI apps
        with lifespan, where the normal finalize() flow doesn't apply.

        Args:
            app: Starlette application to extend
            container: DI container for accessing settings
        """
        self._mount_static_files(app, container)

    def _mount_static_files(self, app, container: "Container") -> None:
        """
        Mount static files to the ASGI app.

        Shared logic used by both finalize() and extend_asgi_app().

        Args:
            app: Starlette application to mount static files to
            container: DI container for accessing settings
        """
        settings = container.get(FrontendSettings)

        static_path = Path(self.static_dir) / "dist"
        if static_path.exists():
            app.mount(
                settings.static_url_prefix,
                CachedStaticFiles(
                    directory=str(static_path),
                    cache_max_age=settings.cache_max_age,
                    enable_caching=settings.cache_static_assets,
                ),
                name="static",
            )
            cache_status = "enabled" if settings.cache_static_assets else "disabled"
            logger.info(
                f"✅ Static files mounted at {settings.static_url_prefix} "
                f"(caching {cache_status}, max-age={settings.cache_max_age}s)"
            )
        else:
            logger.debug(f"Static files directory not found: {static_path}")

        # Production: verify manifest exists
        if settings.environment != "development":
            manifest_path = static_path / ".vite" / "manifest.json"
            if not manifest_path.exists():
                logger.warning(
                    f"Vite manifest not found: {manifest_path}\n"
                    "Run 'npm run build' to build production assets"
                )

    async def start(self) -> None:
        """
        Start frontend module (runtime services).

        In development:
        - Starts Vite dev server in background
        - Enables HMR
        """
        settings = load_settings(FrontendSettings)

        if settings.environment == "development" and settings.enable_vite_dev:
            await self._start_vite_dev_server()

    async def stop(self) -> None:
        """Stop frontend module (terminate Vite dev server)."""
        await self._vite_manager.stop(timeout=5.0)

    def _check_npm_available(self) -> bool:
        """
        Check if npm is installed and available.

        Returns:
            True if npm is available, False otherwise
        """
        import shutil  # noqa: PLC0415

        return shutil.which("npm") is not None

    async def _check_vite_health(self, url: str, max_wait: float = 10.0) -> bool:
        """
        Check if Vite dev server is responding.

        Args:
            url: Vite dev server URL
            max_wait: Maximum time to wait for server to be ready

        Returns:
            True if server is healthy, False otherwise
        """
        import time  # noqa: PLC0415
        from urllib.parse import urlparse  # noqa: PLC0415

        start_time = time.time()
        attempt = 0

        # Parse URL properly
        try:
            parsed = urlparse(url)
            host = parsed.hostname or "localhost"
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except Exception as e:
            logger.error(f"Failed to parse Vite URL '{url}': {e}")
            return False

        logger.debug(f"Health checking Vite server at {host}:{port}")

        while time.time() - start_time < max_wait:
            attempt += 1
            try:
                # Use asyncio to connect (non-blocking)
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=1.0
                )

                # Send a simple HTTP GET request to check if Vite is responding
                writer.write(b"GET / HTTP/1.1\r\n")
                writer.write(f"Host: {host}:{port}\r\n".encode())
                writer.write(b"Connection: close\r\n\r\n")
                await writer.drain()

                # Read the response (just the status line)
                response = await asyncio.wait_for(reader.readline(), timeout=1.0)
                writer.close()
                await writer.wait_closed()

                # Check if we got an HTTP response
                if response.startswith(b"HTTP/"):
                    logger.debug(f"Vite server health check passed (attempt {attempt})")
                    return True

                logger.debug(f"Vite health check got non-HTTP response (attempt {attempt})")

            except (TimeoutError, ConnectionRefusedError, OSError) as e:
                logger.debug(f"Vite health check failed (attempt {attempt}): {type(e).__name__}")
            except Exception as e:
                logger.debug(f"Vite health check failed (attempt {attempt}): {e}")

            # Wait a bit before retrying
            await asyncio.sleep(0.5)

        logger.warning(f"Vite server not responding after {max_wait}s")
        return False

    async def _start_vite_dev_server(self):
        """Start Vite dev server in background."""
        settings = load_settings(FrontendSettings)

        # Check if npm is available
        if not self._check_npm_available():
            logger.error("❌ npm not found. Vite dev server requires Node.js and npm.")
            logger.error("")
            logger.error("To fix this:")
            logger.error("  1. Install Node.js from https://nodejs.org/")
            logger.error("  2. Or disable Vite dev server: set MYFY_FRONTEND_ENABLE_VITE_DEV=false")
            logger.error("  3. Or run in production mode: set MYFY_FRONTEND_ENVIRONMENT=production")
            return

        # Check if package.json exists
        package_json = Path("package.json")
        if not package_json.exists():
            logger.error("❌ package.json not found. Run scaffold to initialize frontend:")
            logger.error("  FrontendModule(auto_init=True)")
            return

        # Configure output based on settings
        stdout = None if settings.show_vite_logs else subprocess.PIPE
        stderr = None if settings.show_vite_logs else subprocess.PIPE

        # Start Vite using ProcessManager (no startup delay - we'll do health check instead)
        success = await self._vite_manager.start(
            cmd=["npm", "run", "dev"],
            stdout=stdout,
            stderr=stderr,
            startup_delay=0.0,  # No blocking delay
        )

        if not success:
            logger.error("❌ Failed to start Vite dev server")
            logger.error("  Check that 'npm install' has been run")
            logger.error("  Or disable Vite: set MYFY_FRONTEND_ENABLE_VITE_DEV=false")
            return

        # Wait for Vite to be ready with async health check
        logger.info("⏳ Waiting for Vite dev server to be ready...")
        is_healthy = await self._check_vite_health(settings.vite_dev_server, max_wait=10.0)

        if is_healthy:
            logger.info("✅ Vite dev server started (HMR enabled)")
        else:
            logger.warning("⚠️  Vite dev server started but health check failed")
            logger.warning("    Server may still be starting up...")

    def __repr__(self) -> str:
        return f"FrontendModule(templates='{self.templates_dir}')"
