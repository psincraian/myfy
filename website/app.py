"""myfy Website - Application entry point.

This is the main entry point for the myfy website application.
It sets up logging, loads configuration, registers modules, and starts the application.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Add current directory to Python path so 'website' package can be imported
sys.path.insert(0, str(Path(__file__).parent))

# Import website package to register all endpoints
import website.endpoints  # noqa: F401
from dotenv import load_dotenv
from website.config import AppSettings
from website.modules import DatabaseModule, SecurityModule

from myfy.core import Application
from myfy.frontend import FrontendModule
from myfy.web import WebModule

# Load environment variables from .env file
load_dotenv()


def setup_logging(log_level: str = "INFO"):
    """Configure application logging with console and file handlers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create formatters
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # File handler (rotates at 10MB, keeps 5 backups)
    file_handler = RotatingFileHandler(
        log_dir / "myfy.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


# Create application with settings
settings = AppSettings()

# Set up logging based on settings
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Create application instance
app = Application(settings_class=AppSettings, auto_discover=False)

# Add core modules
app.add_module(WebModule())
app.add_module(FrontendModule())

# Add application-specific modules
app.add_module(DatabaseModule())
app.add_module(SecurityModule())

logger.info(f"Application configured: {settings.app_name}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
