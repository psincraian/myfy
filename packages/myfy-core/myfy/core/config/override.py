"""
Helper for overriding nested settings defaults.

Provides config where you can override any nested property in 1 line.
"""

from typing import TypeVar

from .settings import BaseSettings

T = TypeVar("T", bound=BaseSettings)


def override[T: BaseSettings](settings_class: type[T], **overrides) -> type[T]:
    """
    Create a subclass of a settings class with overridden defaults.

    This allows one-line syntax for overriding module defaults while preserving
    environment variable precedence.

    Args:
        settings_class: The base settings class (e.g., WebSettings)
        **overrides: Field names and their new default values

    Returns:
        A subclass with overridden field defaults

    Raises:
        ValueError: If a field name doesn't exist in the base class

    Example:
        ```python
        from pydantic import Field
        from myfy.core import Application, BaseSettings, override
        from myfy.web import WebModule, WebSettings

        class AppSettings(BaseSettings):
            app_name: str = "My App"
            # Override port to 3000, but env var MYFY_WEB_PORT can still override
            web: WebSettings = Field(default_factory=override(WebSettings, port=3000))

        app = Application(settings_class=AppSettings)
        app.add_module(WebModule())
        ```

        Running the application:
        ```bash
        # Uses port 3000 (from override)
        myfy run

        # Uses port 9000 (env var takes precedence over override)
        MYFY_WEB_PORT=9000 myfy run
        ```

    Precedence Order:
        1. Environment Variables (highest)
        2. Python overrides (via this helper)
        3. Module defaults (lowest)

    Notes:
        - Supports partial overrides (only override what you need)
        - Fully type-safe with IDE autocomplete
        - Works with any BaseSettings subclass
        - Environment variables always take precedence
    """
    # Build namespace with proper type annotations
    namespace = {
        "__module__": settings_class.__module__,
        "__annotations__": {},
    }

    # Get field types from the base class
    for field_name, new_default in overrides.items():
        if field_name in settings_class.model_fields:
            field_info = settings_class.model_fields[field_name]
            # Add type annotation from base class
            namespace["__annotations__"][field_name] = field_info.annotation
            # Set new default value
            namespace[field_name] = new_default
        else:
            raise ValueError(
                f"Field '{field_name}' not found in {settings_class.__name__}. "
                f"Available fields: {', '.join(settings_class.model_fields.keys())}"
            )

    # Generate a unique class name
    override_keys = "_".join(sorted(overrides.keys()))
    class_name = f"{settings_class.__name__}_Override_{override_keys}"

    # Create and return the subclass
    return type(class_name, (settings_class,), namespace)
