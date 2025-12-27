"""
Handler execution with dependency injection.

Compiles injection plans for routes at startup.
"""

import json
import logging
import traceback
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, get_type_hints

if TYPE_CHECKING:
    from collections.abc import Callable

from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from myfy.core.config import CoreSettings

from .context import RequestContext, get_request_context
from .exceptions import WebError
from .params import QueryParam
from .routing import Route


class HandlerExecutor:
    """
    Executes route handlers with dependency injection.

    Resolves dependencies from the DI container and injects them
    along with path parameters and request body.
    """

    def __init__(self, container: Any):
        self.container = container
        self._execution_plans: dict[str, Callable] = {}
        self._logger = logging.getLogger(__name__)

    def compile_route(self, route: Route) -> None:
        """
        Compile an execution plan for a route.

        Analyzes the handler signature and builds a fast execution path.
        """
        hints = get_type_hints(route.handler)

        # Build execution plan
        async def execute(request: Request, path_params: dict[str, Any]) -> Response:
            kwargs = {}

            # 1. Inject path parameters
            for param_name in route.path_params:
                param_type = hints.get(param_name, str)
                raw_value = path_params.get(param_name)
                # Convert to appropriate type with validation
                kwargs[param_name] = self._convert_param(raw_value, param_type, param_name)

            # 2. Inject query parameters
            for query_info in route.query_params:
                query_name = query_info.query_name
                raw_value = request.query_params.get(query_name)

                # Convert and validate query parameter
                kwargs[query_info.name] = self._convert_query_param(
                    raw_value,
                    query_info.type_hint,
                    query_info.name,
                    query_info.spec,
                )

            # 3. Inject request body if needed
            if route.body_param:
                body_type = hints.get(route.body_param)
                if body_type is not None:
                    body_data = await self._parse_body(request, body_type)
                    kwargs[route.body_param] = body_data

            # 4. Inject dependencies from container
            for param_name in route.dependencies:
                param_type = hints.get(param_name)
                if param_type:
                    try:
                        # Special case: inject Request or RequestContext
                        if param_type == Request:
                            kwargs[param_name] = request
                        elif param_type == RequestContext:
                            kwargs[param_name] = get_request_context()
                        else:
                            # Resolve from DI container
                            kwargs[param_name] = self.container.get(param_type)
                    except Exception as e:
                        self._logger.exception(
                            "Dependency injection failed",
                            exc_info=e,
                            extra={"param_name": param_name, "param_type": str(param_type)},
                        )
                        return self._make_error_response(e)

            # 5. Execute handler
            try:
                if iscoroutinefunction(route.handler):
                    result = await route.handler(**kwargs)
                else:
                    result = route.handler(**kwargs)

                # Convert result to response
                return self._make_response(result, route.status_code)

            except HTTPException as e:
                # Starlette HTTP exceptions - safe to expose
                return JSONResponse(
                    {"detail": e.detail},
                    status_code=e.status_code,
                )
            except WebError as e:
                # myfy WebError exceptions - convert to Problem Details
                return JSONResponse(
                    e.to_problem_detail(),
                    status_code=e.status_code,
                )
            except Exception as e:
                # Unknown errors - sanitize based on environment
                return self._make_error_response(e)

        self._execution_plans[self._route_key(route)] = execute

    async def execute_route(
        self, route: Route, request: Request, path_params: dict[str, Any]
    ) -> Response:
        """Execute a route handler."""
        plan = self._execution_plans.get(self._route_key(route))
        if plan is None:
            raise RuntimeError(f"Route not compiled: {route}")
        return await plan(request, path_params)

    def _route_key(self, route: Route) -> str:
        """Generate a unique key for a route."""
        return f"{route.method}:{route.path}"

    def _convert_param(self, value: Any, type_hint: type, param_name: str) -> Any:
        """Convert path parameter with validation."""
        if value is None:
            return None

        try:
            if type_hint is int:
                return int(value)
            if type_hint is float:
                return float(value)
            if type_hint is bool:
                return value.lower() in ("true", "1", "yes")
            return str(value)
        except (ValueError, AttributeError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for parameter '{param_name}': expected {type_hint.__name__}, got '{value}'",
            ) from e

    def _convert_query_param(
        self,
        value: str | None,
        type_hint: type,
        param_name: str,
        spec: QueryParam,
    ) -> Any:
        """
        Convert and validate query parameter.

        Args:
            value: Raw string value from query string (None if not present)
            type_hint: Expected type of the parameter
            param_name: Parameter name for error messages
            spec: Query parameter specification with validation constraints

        Returns:
            Converted and validated value

        Raises:
            HTTPException: If value is invalid or fails validation
        """
        # Handle missing values
        if value is None:
            if spec.is_required:
                raise HTTPException(
                    status_code=400,
                    detail=f"Query parameter '{param_name}' is required",
                )
            return spec.default

        # Convert to target type
        converted: int | float | bool | str
        try:
            if type_hint is int:
                converted = int(value)
            elif type_hint is float:
                converted = float(value)
            elif type_hint is bool:
                converted = value.lower() in ("true", "1", "yes")
            else:
                converted = str(value)
        except (ValueError, AttributeError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for query parameter '{param_name}': expected {type_hint.__name__}, got '{value}'",
            ) from e

        # Apply validation constraints
        try:
            spec.validate(converted, param_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        return converted

    async def _parse_body(self, request: Request, body_type: type) -> Any:
        """Parse request body with proper error handling."""
        try:
            if body_type in (dict, dict):
                return await request.json()
            if body_type in (str,):
                body = await request.body()
                return body.decode()
            if hasattr(body_type, "model_validate"):
                # Pydantic model
                try:
                    data = await request.json()
                except json.JSONDecodeError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON: {e!s}") from e

                try:
                    # Type checker doesn't know about Pydantic's model_validate
                    return body_type.model_validate(data)  # type: ignore[attr-defined]
                except ValidationError as e:
                    # Convert validation errors to string for HTTPException
                    error_detail = json.dumps({"errors": e.errors(), "body": data})
                    raise HTTPException(status_code=422, detail=error_detail) from e
            elif hasattr(body_type, "__dataclass_fields__"):
                # Dataclass
                try:
                    data = await request.json()
                except json.JSONDecodeError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON: {e!s}") from e

                try:
                    return body_type(**data)
                except TypeError as e:
                    raise HTTPException(
                        status_code=422, detail=f"Invalid request body: {e!s}"
                    ) from e
            else:
                # Try JSON by default
                return await request.json()

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to parse request body: {e!s}"
            ) from e

    def _make_response(self, result: Any, status_code: int | None = None) -> Response:
        """Convert handler result to HTTP response.

        Args:
            result: The handler's return value
            status_code: Optional HTTP status code to use (from route decorator)
        """
        if isinstance(result, Response):
            # If a custom status code was specified and result is a Response,
            # we respect the Response's own status code
            return result
        if isinstance(result, (dict, list)):
            return JSONResponse(result, status_code=status_code or 200)
        if hasattr(result, "model_dump"):
            # Pydantic model
            return JSONResponse(result.model_dump(), status_code=status_code or 200)
        if result is None:
            # For None results, use specified status_code or default to 204
            return Response(status_code=status_code or 204)
        # Try to serialize as JSON
        try:
            return JSONResponse(result, status_code=status_code or 200)
        except (TypeError, ValueError):
            # Fallback to string
            return Response(
                content=str(result),
                media_type="text/plain",
                status_code=status_code or 200,
            )

    def _make_error_response(self, error: Exception) -> JSONResponse:
        """Create error response with appropriate detail level based on debug mode."""
        # Log the full error for debugging
        self._logger.exception("Handler execution failed", exc_info=error)

        # Get debug mode from settings if available
        debug_mode = False
        try:
            settings = self.container.get(CoreSettings)
            debug_mode = settings.debug
        except Exception:
            pass

        if debug_mode:
            # In development: show full details
            return JSONResponse(
                {
                    "type": "about:blank",
                    "title": type(error).__name__,
                    "status": 500,
                    "detail": str(error),
                    "traceback": traceback.format_exc(),
                },
                status_code=500,
            )
        # In production: hide details
        return JSONResponse(
            {
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred. Please contact support.",
            },
            status_code=500,
        )
