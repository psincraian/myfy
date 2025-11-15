# myfy Website

The official landing page and website for the myfy Python web framework.

## Overview

A modern, plant-themed website showcasing myfy's features with:
- Landing page with hero, features, and quickstart sections
- Newsletter signup with PostgreSQL database
- Clean architecture with dependency injection

## Tech Stack

- **Backend**: Python 3.14+, myfy framework
- **Database**: PostgreSQL 16 with SQLAlchemy 2.0 (async)
- **Frontend**: Tailwind CSS 4, DaisyUI 5, Vite 7
- **Security**: CSRF protection, rate limiting, security headers

## Project Structure

```
website/
├── app.py                      # Application entry point
├── website/                    # Main package
│   ├── config/                # Settings
│   ├── models/                # Database models
│   ├── services/              # Business logic
│   ├── modules/               # Infrastructure (database, security)
│   └── endpoints/             # Route handlers
├── frontend/                  # Templates, CSS, JS
├── alembic/                   # Database migrations
└── docker-compose.yml         # PostgreSQL
```

## Getting Started

### Prerequisites

- Python 3.14+
- Node.js 20+
- Docker & Docker Compose
- uv package manager

### Installation

1. Install dependencies:
   ```bash
   uv sync
   cd website && npm install
   ```

2. Set up environment:
   ```bash
   cp .env.example .env
   ```

3. Start database and run migrations:
   ```bash
   docker-compose up -d
   uv run alembic upgrade head
   ```

4. Start development server:
   ```bash
   uv run python app.py
   ```

5. Visit http://localhost:8000

## Development

### Running Code Quality Checks

```bash
# Linting
uv run ruff check --fix website

# Type checking
uv run ty check website
```

Both must pass before committing.

### Database Migrations

```bash
# Create migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head
```

## Environment Variables

**Database** (prefix: `DATABASE_`)
- `DATABASE_URL` - PostgreSQL connection string
- `DATABASE_POOL_SIZE` - Connection pool size (default: 5)

**Security** (prefix: `SECURITY_`)
- `SECURITY_SECRET_KEY` - Secret key (**required in production**)
- `SECURITY_RATE_LIMIT` - Rate limit (default: "5/minute")

**Frontend**
- `MYFY_FRONTEND_ENVIRONMENT` - Set to `production` for builds

See `.env.example` for full list.

## License

Part of the myfy framework project.
