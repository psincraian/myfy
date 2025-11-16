"""
Web module configuration.

Each module defines its own settings for modularity.
"""

from pydantic import Field

from myfy.core.config import BaseSettings


class WebSettings(BaseSettings):
    """
    Web module settings.

    Configure HTTP server, CORS, and request handling.
    """

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # CORS configuration
    cors_enabled: bool = Field(default=False, description="Enable CORS middleware")
    cors_allowed_origins: list[str] = Field(
        default_factory=list,
        description="Allowed CORS origins (e.g., ['https://example.com']). Empty list = CORS disabled.",
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    cors_allowed_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH"],
        description="Allowed HTTP methods for CORS",
    )
    cors_allowed_headers: list[str] = Field(
        default_factory=lambda: ["Content-Type", "Authorization"],
        description="Allowed headers for CORS",
    )

    # Request limits
    max_request_body_size: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        description="Maximum request body size in bytes",
    )

    class Config:
        env_prefix = "MYFY_WEB_"
