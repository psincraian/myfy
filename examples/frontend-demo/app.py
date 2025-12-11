"""
Frontend Demo - myfy with Tailwind 4 + DaisyUI 5 + Database

This example demonstrates the FrontendModule with:
- Server-side rendering using Jinja2
- DaisyUI 5 components
- Tailwind 4 styling
- Vite for asset bundling
- Theme switcher (light/dark mode)
- SQLAlchemy database integration with Todo CRUD
"""

from sqlalchemy import Boolean, Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from myfy.core import Application
from myfy.data import DataModule
from myfy.frontend import FrontendModule, render_template
from myfy.web import WebModule, route

# Database model
Base = declarative_base()


class Todo(Base):
    """Todo item model."""

    __tablename__ = "todos"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    completed = Column(Boolean, default=False)


# Todo CRUD routes
@route.get("/todos")
async def todos_list(request: Request, templates: Jinja2Templates, session: AsyncSession):
    """List all todos."""
    result = await session.execute(select(Todo).order_by(Todo.id))
    todos = result.scalars().all()
    return render_template(
        "todos.html",
        request=request,
        templates=templates,
        title="Todos",
        todos=todos,
    )


@route.post("/todos")
async def todos_create(request: Request, session: AsyncSession):
    """Create a new todo."""
    form = await request.form()
    title = form.get("title", "").strip()

    if title:
        todo = Todo(title=title)
        session.add(todo)
        await session.commit()

    return RedirectResponse(url="/todos", status_code=303)


@route.post("/todos/{todo_id}/toggle")
async def todos_toggle(todo_id: int, session: AsyncSession):
    """Toggle todo completion."""
    result = await session.execute(select(Todo).where(Todo.id == todo_id))
    todo = result.scalar_one_or_none()

    if todo:
        todo.completed = not todo.completed
        await session.commit()

    return RedirectResponse(url="/todos", status_code=303)


@route.post("/todos/{todo_id}/delete")
async def todos_delete(todo_id: int, session: AsyncSession):
    """Delete a todo."""
    result = await session.execute(select(Todo).where(Todo.id == todo_id))
    todo = result.scalar_one_or_none()

    if todo:
        await session.delete(todo)
        await session.commit()

    return RedirectResponse(url="/todos", status_code=303)


# Create routes with DI injection of templates
@route.get("/")
async def home(request: Request, templates: Jinja2Templates):
    """Home page with DaisyUI components."""
    return render_template(
        "home.html",
        request=request,
        templates=templates,
        title="Frontend Demo",
        description="Built with myfy, Tailwind 4, DaisyUI 5, and Database",
    )


@route.get("/about")
async def about(request: Request, templates: Jinja2Templates):
    """About page."""
    return render_template(
        "about.html",
        request=request,
        templates=templates,
        title="About",
    )


@route.get("/components")
async def components(request: Request, templates: Jinja2Templates):
    """Component showcase page."""
    return render_template(
        "components.html",
        request=request,
        templates=templates,
        title="Components",
    )


# Create application
app = Application(auto_discover=False)
app.add_module(
    DataModule(
        auto_create_tables=True,  # Creates tables on startup
        metadata=Base.metadata,
    )
)
app.add_module(WebModule())
app.add_module(FrontendModule(auto_init=True))  # Auto-scaffolds on first run!


if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
