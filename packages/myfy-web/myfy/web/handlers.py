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

    from myfy.web.auth.registry import ProtectedTypesRegistry
    from myfy.web.ratelimit.store import RateLimitStore

from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from myfy.core.config import CoreSettings

from .context import RequestContext, get_request_context
from .exceptions import WebError
from .params import QueryParam
from .ratelimit.decorator import get_rate_limit_config
from .ratelimit.keys import RateLimitKey
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
        self._protected_registry: ProtectedTypesRegistry | None = None
        self._protected_registry_checked = False
        self._rate_limit_store: RateLimitStore | None = None
        self._rate_limit_store_checked = False

    def _get_protected_registry(self) -> "ProtectedTypesRegistry | None":
        """
        Lazy load protected types registry.

        Returns None if AuthModule is not configured.
        """
        if not self._protected_registry_checked:
            self._protected_registry_checked = True
            try:
                from myfy.web.auth.registry import ProtectedTypesRegistry

                self._protected_registry = self.container.get(ProtectedTypesRegistry)
            except Exception:
                pass  # No AuthModule configured
        return self._protected_registry

    def _get_rate_limit_store(self) -> "RateLimitStore | None":
        """
        Lazy load rate limit store.

        Returns None if RateLimitModule is not configured.
        """
        if not self._rate_limit_store_checked:
            self._rate_limit_store_checked = True
            try:
                from myfy.web.ratelimit.store import RateLimitStore  # noqa: PLC0415

                self._rate_limit_store = self.container.get(RateLimitStore)
            except Exception:
                pass  # No RateLimitModule configured
        return self._rate_limit_store

    async def _check_rate_limit(
        self,
        request: Request,
        rate_limit_config: Any,
        route_path: str,
    ) -> Response | None:
        """
        Check per-route rate limit if configured.

        Returns a 429 response if rate limit exceeded, None otherwise.
        """
        store = self._get_rate_limit_store()
        if store is None:
            return None

        # Build rate limit key
        client_key = self._get_client_key(request, rate_limit_config.key)
        scope = rate_limit_config.scope or route_path
        rate_key = f"route:{scope}:{client_key}"

        result = await store.check_and_increment(
            rate_key,
            rate_limit_config.requests,
            rate_limit_config.window_seconds,
        )

        if not result.allowed:
            return self._rate_limit_response(result)
        return None

    def compile_route(self, route: Route) -> None:
        """
        Compile an execution plan for a route.

        Analyzes the handler signature and builds a fast execution path.
        """
        hints = get_type_hints(route.handler)

        # Get rate limit config if decorated
        rate_limit_config = get_rate_limit_config(route.handler)

        # Build execution plan
        async def execute(  # noqa: PLR0911
            request: Request, path_params: dict[str, Any]
        ) -> Response:
            kwargs = {}

            # 0. Check per-route rate limit if configured
            if rate_limit_config is not None:
                rate_limit_response = await self._check_rate_limit(
                    request, rate_limit_config, route.path
                )
                if rate_limit_response is not None:
                    return rate_limit_response

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
                            value = self.container.get(param_type)

                            # Check if protected type returned None
                            if value is None:
                                registry = self._get_protected_registry()
                                if registry:
                                    status_code = registry.get_status_code(param_type)
                                    if status_code:
                                        return JSONResponse(
                                            {"detail": registry.get_error_detail(status_code)},
                                            status_code=status_code,
                                        )

                            kwargs[param_name] = value
                    except HTTPException:
                        raise  # Let HTTP exceptions bubble up
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

    def _get_client_key(self, request: Request, key_strategy: RateLimitKey | str) -> str:
        """
        Extract client identifier from request based on key strategy.

        Args:
            request: The incoming request
            key_strategy: Strategy for identifying the client

        Returns:
            Client identifier string
        """
        client_ip = self._get_client_ip(request)

        # Handle string keys (static bucket)
        if isinstance(key_strategy, str):
            return key_strategy

        # Handle special key strategies
        if key_strategy == RateLimitKey.GLOBAL:
            return "global"

        if key_strategy == RateLimitKey.ENDPOINT:
            return f"endpoint:{client_ip}:{request.url.path}"

        if key_strategy == RateLimitKey.API_KEY:
            api_key = request.headers.get("X-API-Key", "")
            return f"api:{api_key}" if api_key else client_ip

        if key_strategy == RateLimitKey.SESSION:
            session_id = request.cookies.get("session_id", "")
            return f"session:{session_id}" if session_id else client_ip

        # Default: IP-based (also fallback for USER which requires auth context)
        return client_ip

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting proxy headers."""
        # Check X-Forwarded-For header (set by proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header (nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fallback to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _rate_limit_response(self, result: Any) -> JSONResponse:
        """Create rate limit exceeded response."""
        return JSONResponse(
            content={
                "type": "rate_limit_exceeded",
                "title": "Rate Limit Exceeded",
                "status": 429,
                "detail": "Too many requests. Please slow down.",
                "retry_after": result.retry_after,
            },
            status_code=429,
            headers=result.headers,
        )
