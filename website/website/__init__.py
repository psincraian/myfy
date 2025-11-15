"""myfy Website - A modern Python web application built with myfy framework.

This package contains the complete website application with clear separation of concerns:
- config: Application configuration and settings
- models: Database models
- services: Business logic layer
- modules: myfy framework modules
- endpoints: HTTP route handlers
"""

__version__ = "0.1.0"

# Export main components for convenient imports
from .config import AppSettings, DatabaseSettings, SecuritySettings
from .models import Base, NewsletterSubscriber
from .modules import DatabaseModule, SecurityModule
from .services import NewsletterService

__all__ = [
    # Version
    "__version__",
    # Configuration
    "AppSettings",
    "DatabaseSettings",
    "SecuritySettings",
    # Models
    "Base",
    "NewsletterSubscriber",
    # Modules
    "DatabaseModule",
    "SecurityModule",
    # Services
    "NewsletterService",
]
