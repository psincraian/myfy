"""
Web + Data example application.

A complete application using WebModule + DataModule to verify:
- Database connection and session management
- REQUEST-scoped session injection in handlers
- CRUD operations through HTTP endpoints
- Transaction handling
- Foreign key relationships
"""

from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from myfy.core import Application
from myfy.core.config import BaseSettings
from myfy.data import DataModule, DatabaseSettings
from myfy.web import WebModule
from myfy.web.routing import Router

from .models import Base, Post, User


# =============================================================================
# Settings
# =============================================================================


class WebDataSettings(BaseSettings):
    """Settings for web+data test application."""

    app_name: str = "Web Data Test App"
    debug: bool = True

    model_config = {"env_prefix": "WEB_DATA_TEST_"}


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateUserRequest(BaseModel):
    """Request body for creating a user."""

    name: str
    email: str


class CreatePostRequest(BaseModel):
    """Request body for creating a post."""

    title: str
    content: str | None = None


# =============================================================================
# Application Factory
# =============================================================================


def create_app(database_url: str = "sqlite+aiosqlite:///:memory:") -> tuple[Application, Router]:
    """
    Create the web+data test application.

    Args:
        database_url: Database URL (defaults to in-memory SQLite for tests)

    Returns:
        Tuple of (Application, Router) for test access.
    """
    router = Router()

    # =============================================================================
    # Health Routes
    # =============================================================================

    @router.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    @router.get("/health/db")
    async def health_db(session: AsyncSession):
        """Database health check - verifies session injection works."""
        # Execute a simple query to verify connection
        result = await session.execute(select(1))
        value = result.scalar()
        return {"status": "ok", "db_check": value == 1}

    # =============================================================================
    # User Routes
    # =============================================================================

    @router.get("/users")
    async def list_users(session: AsyncSession):
        """List all users."""
        result = await session.execute(select(User).order_by(User.id))
        users = result.scalars().all()
        return {"users": [u.to_dict() for u in users]}

    @router.post("/users")
    async def create_user(data: CreateUserRequest, session: AsyncSession):
        """Create a new user."""
        user = User(name=data.name, email=data.email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return {"user": user.to_dict()}

    @router.get("/users/{user_id}")
    async def get_user(user_id: int, session: AsyncSession):
        """Get a user by ID."""
        user = await session.get(User, user_id)
        if user is None:
            return JSONResponse({"error": "User not found"}, status_code=404)
        return {"user": user.to_dict()}

    @router.get("/users/{user_id}/posts")
    async def get_user_posts(user_id: int, session: AsyncSession):
        """Get all posts by a user."""
        # Use selectinload for eager loading
        result = await session.execute(
            select(User).where(User.id == user_id).options(selectinload(User.posts))
        )
        user = result.scalar_one_or_none()
        if user is None:
            return JSONResponse({"error": "User not found"}, status_code=404)
        return {"posts": [p.to_dict() for p in user.posts]}

    @router.delete("/users/{user_id}")
    async def delete_user(user_id: int, session: AsyncSession):
        """Delete a user by ID."""
        user = await session.get(User, user_id)
        if user is None:
            return JSONResponse({"error": "User not found"}, status_code=404)
        await session.delete(user)
        await session.commit()
        return {"deleted": True}

    # =============================================================================
    # Post Routes
    # =============================================================================

    @router.get("/posts")
    async def list_posts(session: AsyncSession):
        """List all posts."""
        result = await session.execute(select(Post).order_by(Post.id))
        posts = result.scalars().all()
        return {"posts": [p.to_dict() for p in posts]}

    @router.post("/users/{user_id}/posts")
    async def create_post(user_id: int, data: CreatePostRequest, session: AsyncSession):
        """Create a new post for a user."""
        # Verify user exists
        user = await session.get(User, user_id)
        if user is None:
            return JSONResponse({"error": "User not found"}, status_code=404)

        post = Post(title=data.title, content=data.content, author_id=user_id)
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return {"post": post.to_dict()}

    @router.get("/posts/{post_id}")
    async def get_post(post_id: int, session: AsyncSession):
        """Get a post by ID."""
        post = await session.get(Post, post_id)
        if post is None:
            return JSONResponse({"error": "Post not found"}, status_code=404)
        return {"post": post.to_dict()}

    @router.delete("/posts/{post_id}")
    async def delete_post(post_id: int, session: AsyncSession):
        """Delete a post by ID."""
        post = await session.get(Post, post_id)
        if post is None:
            return JSONResponse({"error": "Post not found"}, status_code=404)
        await session.delete(post)
        await session.commit()
        return {"deleted": True}

    # =============================================================================
    # Transaction Test Routes
    # =============================================================================

    @router.post("/test/transaction-success")
    async def test_transaction_success(session: AsyncSession):
        """Test successful transaction with multiple operations."""
        # Create user and post in same transaction
        user = User(name="Transaction User", email="tx@example.com")
        session.add(user)
        await session.flush()  # Get user ID without committing

        post = Post(title="Transaction Post", content="Created in transaction", author_id=user.id)
        session.add(post)
        await session.commit()

        await session.refresh(user)
        await session.refresh(post)

        return {"user_id": user.id, "post_id": post.id}

    @router.post("/test/transaction-rollback")
    async def test_transaction_rollback(session: AsyncSession):
        """Test transaction rollback on error."""
        # Create a user
        user = User(name="Rollback User", email="rollback@example.com")
        session.add(user)
        await session.flush()

        # Simulate an error that should cause rollback
        raise ValueError("Intentional error to test rollback")

    # =============================================================================
    # Create Application
    # =============================================================================

    # Create database settings
    db_settings = DatabaseSettings(
        database_url=database_url,
        echo=False,
        environment="test",  # Allow auto_create_tables
    )

    app = Application(settings_class=WebDataSettings, auto_discover=False)
    app.add_module(WebModule(router=router))
    app.add_module(
        DataModule(
            settings=db_settings,
            auto_create_tables=True,
            metadata=Base.metadata,
        )
    )

    return app, router
