"""Health check endpoint."""

import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.responses import JSONResponse

from myfy.web import route

logger = logging.getLogger(__name__)


@route.get("/health")
async def health_check(session_maker: async_sessionmaker):
    """Health check endpoint for monitoring and load balancers.

    This endpoint checks:
    - Database connectivity (SELECT 1 query)
    - Returns 200 if healthy, 503 if unhealthy

    Args:
        session_maker: Async session maker (DI-injected)

    Returns:
        JSON response with health status
    """
    try:
        # Check database connectivity
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
