# myfy Website

The official landing page and website for the myfy Python web framework.

## Overview

This is a modern, plant-themed website showcasing myfy's features with:
- Beautiful landing page with hero, features, and quickstart sections
- Newsletter signup functionality with PostgreSQL database
- Responsive design using Tailwind CSS 4 + DaisyUI 5
- Animated decorative elements with organic, growth-focused aesthetics

## Project Structure

```
website/
├── app.py                      # Main application with routes
├── database.py                 # Database module with DI integration
├── models.py                   # Newsletter subscriber model
├── newsletter_service.py       # Business logic layer
├── alembic/                    # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini                 # Alembic configuration
├── frontend/                   # Frontend assets and templates
│   ├── templates/
│   │   ├── landing.html       # Main landing page
│   │   ├── newsletter.html    # Newsletter signup page
│   │   ├── base.html          # Base template
│   │   └── components/        # Reusable components
│   │       ├── navbar.html
│   │       ├── hero.html
│   │       ├── features.html
│   │       ├── quickstart.html
│   │       └── footer.html
│   ├── css/
│   │   └── input.css          # Custom plant-themed styles
│   ├── js/
│   │   ├── main.js
│   │   ├── animations.js      # Scroll & parallax effects
│   │   └── copy-code.js       # Copy to clipboard
│   └── static/
│       └── images/            # Logo and decorative SVGs
├── docker-compose.yml          # PostgreSQL database
├── Dockerfile                  # Production build
├── .dockerignore
├── .env.example                # Environment variables template
├── package.json                # Node dependencies
├── package-lock.json
└── vite.config.js             # Vite bundler config
```

## Tech Stack

- **Backend**: Python 3.12+, myfy framework
- **Database**: PostgreSQL 16 with asyncpg + SQLAlchemy
- **Frontend**: Tailwind CSS 4, DaisyUI 5, Vite 7
- **Templates**: Jinja2
- **Migrations**: Alembic

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- uv package manager

### Installation

1. **Install Python dependencies** (from repository root):
   ```bash
   uv sync
   ```

2. **Install Node dependencies**:
   ```bash
   cd website
   npm install
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env if needed
   ```

### Running Locally

1. **Start PostgreSQL database**:
   ```bash
   docker-compose up -d
   ```

2. **Run database migrations**:
   ```bash
   uv run alembic upgrade head
   ```

3. **Start the development server**:
   ```bash
   uv run myfy run
   # or directly with Python:
   uv run python app.py
   ```

   **Note**: The app must be run from within the `website/` directory as it uses relative paths for templates and static files.

4. **Visit the website**:
   - Landing page: http://localhost:8000
   - Newsletter: http://localhost:8000/newsletter

### Development

The frontend module automatically starts a Vite dev server with hot module replacement (HMR) for CSS and JavaScript changes.

- Templates: Edit `frontend/templates/*.html`
- Styles: Edit `frontend/css/input.css`
- JavaScript: Edit `frontend/js/*.js`

Changes to templates require a page refresh, but CSS/JS updates are instant.

## Design System

### Color Palette

- **Primary**: #10B981 (Emerald green)
- **Secondary**: #34D399 (Light emerald)
- **Accent**: #059669 (Dark emerald)
- **Neutral**: #111827 (Rich gray-black)
- **Background**: #F5F3EE (Cream/beige from logo)

### Key Features

- **Plant Theme**: Floating leaf animations, organic shapes, natural color palette
- **Responsive**: Mobile-first design with breakpoints for tablet and desktop
- **Accessible**: Semantic HTML, ARIA labels, keyboard navigation
- **Modern**: Smooth animations, glassmorphism effects, clean typography

## Database

The website uses PostgreSQL to store newsletter subscribers with the following schema:

```sql
CREATE TABLE newsletter_subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    subscribed_at TIMESTAMP DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE
);
```

### Managing Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Rollback last migration
uv run alembic downgrade -1

# View migration history
uv run alembic history
```

## Deployment

### Building for Production

1. **Build frontend assets**:
   ```bash
   npm run build
   ```

2. **Build Docker image**:
   ```bash
   docker build -t myfy-website .
   ```

3. **Run with Docker Compose**:
   ```bash
   # Update docker-compose.yml for production settings
   docker-compose up -d
   ```

### Environment Variables

Required environment variables for production:

- `DATABASE_URL`: PostgreSQL connection string
- `MYFY_FRONTEND_ENVIRONMENT`: Set to `production`

See `.env.example` for full list.

## Routes

- `GET /` - Landing page
- `GET /newsletter` - Newsletter signup form
- `POST /newsletter` - Handle newsletter subscription

## Contributing

When making changes:

1. Follow the existing code style
2. Test locally with development server
3. Ensure database migrations are created if schema changes
4. Build frontend assets before committing (`npm run build`)

## License

Part of the myfy framework project.
