"""
Configuration system with profiles and validation.

Usage:
    from myfy.core.config import BaseSettings, Profile, load_settings

    class AppSettings(BaseSettings):
        db_url: str
        api_key: str

    settings = load_settings(AppSettings)
"""

from .override import override
from .settings import BaseSettings, CoreSettings, Profile, load_settings

__all__ = [
    "BaseSettings",
    "CoreSettings",
    "Profile",
    "load_settings",
    "override",
]
