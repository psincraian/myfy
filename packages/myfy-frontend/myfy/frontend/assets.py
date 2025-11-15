"""Asset management for Vite builds."""

import json
from functools import lru_cache
from pathlib import Path

from .config import FrontendSettings


class AssetResolver:
    """
    Resolves Vite assets in development and production modes.

    In development:
    - Proxies requests to Vite dev server
    - Injects Vite HMR client

    In production:
    - Reads .vite/manifest.json for hashed assets
    - Returns production URLs with cache busting
    """

    def __init__(self, static_dir: str, settings: FrontendSettings):
        self.static_dir = Path(static_dir)
        self.settings = settings
        self.manifest_path = self.static_dir / "dist" / ".vite" / "manifest.json"

    @lru_cache(maxsize=1)  # noqa: B019
    def load_manifest(self) -> dict[str, str]:
        """Load Vite manifest (cached in production)."""
        if self.manifest_path.exists():
            with self.manifest_path.open() as f:
                return json.load(f)
        return {}

    def clear_cache(self):
        """Clear manifest cache (for testing or dev reload)."""
        self.load_manifest.cache_clear()

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.settings.environment == "development"

    def get_asset_url(self, entry_name: str) -> str | None:
        """
        Get asset URL for entry (main, theme-switcher, prism-init, etc).

        Dynamically discovers entries from manifest.json (production) or
        constructs paths for Vite dev server (development).

        Args:
            entry_name: Entry name from vite.config.js

        Returns:
            Asset URL (dev server or production URL with hash)
        """
        if self.is_development() and self.settings.enable_vite_dev:
            # Development: construct path dynamically for Vite dev server
            path = f"frontend/js/{entry_name}.js"
            return f"{self.settings.vite_dev_server}/{path}"

        # Production: dynamically search manifest for matching entry
        manifest = self.load_manifest()

        # Look for entry by name in manifest
        for entry_data in manifest.values():
            # Check if this is an entry point with matching name
            if entry_data.get("isEntry") and entry_data.get("name") == entry_name:
                file_path = entry_data["file"]
                return f"{self.settings.static_url_prefix}/{file_path}"

        return None

    def get_css_url(self, entry_name: str) -> str | None:
        """
        Get CSS URL for styles entry.

        Args:
            entry_name: Usually "styles"

        Returns:
            CSS file URL
        """
        if self.is_development() and self.settings.enable_vite_dev:
            # Development: proxy to Vite server
            if entry_name == "styles":
                return f"{self.settings.vite_dev_server}/frontend/css/input.css"
        else:
            # Production: use manifest
            manifest = self.load_manifest()
            input_path = "frontend/css/input.css"
            if input_path in manifest:
                file_path = manifest[input_path]["file"]
                return f"{self.settings.static_url_prefix}/{file_path}"
        return None

    def get_vite_client_url(self) -> str | None:
        """
        Get Vite HMR client URL (development only).

        Returns:
            Vite client URL or None in production
        """
        if self.is_development() and self.settings.enable_vite_dev:
            return f"{self.settings.vite_dev_server}/@vite/client"
        return None
