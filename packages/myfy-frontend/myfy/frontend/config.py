"""Frontend module configuration."""

from pydantic import Field

from myfy.core.config import BaseSettings


class FrontendSettings(BaseSettings):
    """
    Frontend module settings.

    Configure via environment variables with MYFY_FRONTEND_ prefix:
    - MYFY_FRONTEND_ENVIRONMENT=production
    - MYFY_FRONTEND_TEMPLATES_DIR=frontend/templates
    - MYFY_FRONTEND_VITE_DEV_SERVER=http://localhost:3001
    """

    # Environment
    environment: str = Field(default="development")

    # Paths
    templates_dir: str = Field(default="frontend/templates")
    static_dir: str = Field(default="frontend/static")
    static_url_prefix: str = Field(default="/static")

    # Vite dev server
    vite_dev_server: str = Field(default="http://localhost:3001")
    enable_vite_dev: bool = Field(default=True)
    show_vite_logs: bool = Field(default=False)  # Show Vite output in console

    # Production settings
    cache_static_assets: bool = Field(default=True)
    cache_max_age: int = Field(default=31536000)  # 1 year

    # Template settings
    auto_escape: bool = Field(default=True)
    auto_reload: bool = Field(default=True)  # Dev only

    class Config:
        env_prefix = "MYFY_FRONTEND_"
