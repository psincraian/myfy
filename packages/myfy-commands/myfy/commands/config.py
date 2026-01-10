"""
CLI module settings.

Provides configuration for the CLI commands module.
"""

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from myfy.core.config import BaseSettings


class CliSettings(BaseSettings):
    """
    CLI module settings.

    Environment variables use the MYFY_CLI_ prefix:
    - MYFY_CLI_VERBOSE: Enable verbose output
    - MYFY_CLI_NO_COLOR: Disable colored output
    - MYFY_CLI_TIMEOUT: Command execution timeout

    Example:
        ```bash
        export MYFY_CLI_VERBOSE=true
        export MYFY_CLI_TIMEOUT=600
        myfy app seed-users
        ```
    """

    verbose: bool = Field(
        default=False,
        description="Enable verbose output for debugging",
    )

    no_color: bool = Field(
        default=False,
        description="Disable colored output in terminal",
    )

    timeout: float = Field(
        default=300.0,
        description="Command execution timeout in seconds",
        ge=1.0,
        le=3600.0,
    )

    model_config = SettingsConfigDict(env_prefix="MYFY_CLI_")
