# Contributing to myfy

Thank you for your interest in contributing to myfy! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Conventional Commits](#conventional-commits)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Code Style](#code-style)
- [Project Structure](#project-structure)

## Code of Conduct

Be respectful and inclusive. We're here to build great software together.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/myfy.git`
3. Add upstream remote: `git remote add upstream https://github.com/ORIGINAL-OWNER/myfy.git`
4. Create a feature branch: `git checkout -b feat/my-feature`

## Development Setup

myfy uses `uv` for dependency management and workspace coordination.

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

### Setup Development Environment

```bash
# Navigate to the project
cd myfy

# Install all dependencies (including dev dependencies)
uv sync --all-extras --dev

# Install git hooks
./scripts/install-hooks.sh

# Verify installation
uv run python -c "import myfy.core; print('✓ Setup complete!')"
```

### Workspace Structure

myfy is a monorepo with 5 packages:

```
myfy/
├── packages/
│   ├── myfy-core/      # Core DI, config, modules
│   ├── myfy-web/       # Web/ASGI framework
│   ├── myfy-cli/       # CLI tools
│   ├── myfy-frontend/  # Frontend integration
│   └── myfy/           # Meta-package
├── docs/               # Documentation
└── tests/              # Workspace-level tests
```

### Running in Development Mode

```bash
# Run tests
uv run pytest

# Run specific test file
uv run pytest packages/myfy-core/tests/test_di.py

# Run linting
uv run ruff check packages/

# Auto-fix linting issues
uv run ruff check --fix packages/

# Format code
uv run ruff format packages/

# Type checking
uv run ty check packages/

# Run the CLI in development
uv run myfy --help
```

## Conventional Commits

We use **Conventional Commits** for clear, semantic commit messages. This enables:
- Automatic changelog generation
- Semantic versioning
- Clear project history

### Commit Message Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Types

| Type | Description | Semver Impact |
|------|-------------|---------------|
| `feat` | New feature | MINOR |
| `fix` | Bug fix | PATCH |
| `docs` | Documentation only | - |
| `style` | Code style (formatting, etc.) | - |
| `refactor` | Code refactoring | PATCH |
| `perf` | Performance improvement | PATCH |
| `test` | Add/update tests | - |
| `build` | Build system or dependencies | - |
| `ci` | CI/CD changes | - |
| `chore` | Other changes | - |
| `revert` | Revert previous commit | - |

### Scopes

Use these scopes to indicate which package is affected:

- `core` - myfy-core package
- `web` - myfy-web package
- `cli` - myfy-cli package
- `frontend` - myfy-frontend package
- `meta` - myfy meta-package
- `workspace` - Monorepo/workspace changes
- `docs` - Documentation
- `ci` - CI/CD workflows

### Examples

**Feature:**
```bash
git commit -m "feat(core): add async context manager support for DI container"
```

**Bug fix:**
```bash
git commit -m "fix(web): resolve middleware execution order issue"
```

**Documentation:**
```bash
git commit -m "docs(workspace): update contributing guidelines"
```

**Breaking change:**
```bash
git commit -m "feat(core)!: remove deprecated provider API

BREAKING CHANGE: The old `@inject` decorator has been removed.
Use `@provider` instead."
```

**Multi-line commit:**
```bash
git commit -m "feat(web): add support for WebSocket connections

- Implement WebSocket routing
- Add connection lifecycle hooks
- Update documentation

Closes #123"
```

### Using Commitizen

We provide commitizen for interactive commit creation:

```bash
# Install commitizen
uv pip install commitizen

# Create a commit interactively
cz commit

# Or use the shorthand
cz c
```

This will guide you through creating a properly formatted commit.

### Pre-commit Hook

If you installed the git hooks, conventional commit validation runs automatically:

```bash
# Install hooks (if not already done)
./scripts/install-hooks.sh

# Now all commits are validated
git commit -m "invalid message"  # ❌ Will fail

git commit -m "feat(core): valid message"  # ✅ Will pass
```

## Pull Request Process

### Before Submitting

1. **Update from upstream:**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all checks:**
   ```bash
   # Lint
   uv run ruff check packages/

   # Format
   uv run ruff format packages/

   # Type check
   uv run ty check packages/

   # Test
   uv run pytest
   ```

3. **Update documentation** if you changed APIs

4. **Add tests** for new features

5. **Update CHANGELOG.md** if making a significant change (optional, we auto-generate)

### Submitting a Pull Request

1. Push your branch: `git push origin feat/my-feature`

2. Create a Pull Request on GitHub

3. Fill out the PR template with:
   - Clear description of changes
   - Motivation and context
   - Related issues (if any)
   - Screenshots (for UI changes)

4. Link related issues: `Closes #123`

5. Request review from maintainers

### PR Title Format

Use conventional commit format for PR titles:

```
feat(core): add new feature
fix(web): resolve bug
docs: update contributing guide
```

### Review Process

- Maintainers will review your code
- Address any feedback or requested changes
- Once approved, a maintainer will merge your PR
- Your contribution will be included in the next release!

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=packages --cov-report=html

# Run specific package tests
uv run pytest packages/myfy-core/tests/

# Run specific test
uv run pytest packages/myfy-core/tests/test_di.py::test_singleton_scope

# Run with verbose output
uv run pytest -v

# Run and stop on first failure
uv run pytest -x
```

### Writing Tests

We use pytest for testing. Place tests in the appropriate package:

```
packages/myfy-core/tests/
    test_di.py
    test_config.py
    test_kernel.py
```

**Example test:**

```python
import pytest
from myfy.core import Container, provider, SINGLETON


def test_singleton_provider():
    """Test that singleton providers return the same instance."""

    @provider(scope=SINGLETON)
    def get_service() -> str:
        return "service"

    container = Container()
    container.register(get_service)

    # Both calls should return the same instance
    service1 = container.resolve(str)
    service2 = container.resolve(str)

    assert service1 is service2


@pytest.mark.asyncio
async def test_async_provider():
    """Test async provider resolution."""

    @provider(scope=SINGLETON)
    async def get_async_service() -> str:
        return "async service"

    container = Container()
    container.register(get_async_service)

    service = await container.resolve_async(str)
    assert service == "async service"
```

### Test Coverage

We aim for high test coverage:
- Core functionality: >90%
- New features: 100%
- Bug fixes: Include regression tests

## Code Style

### Formatting

We use **Ruff** for linting and formatting:

```bash
# Check formatting
uv run ruff format --check packages/

# Auto-format
uv run ruff format packages/

# Lint
uv run ruff check packages/

# Lint with auto-fix
uv run ruff check --fix packages/
```

### Style Guidelines

- **Line length:** 100 characters
- **Quotes:** Double quotes `"` for strings
- **Imports:** Sorted with isort (via ruff)
- **Type hints:** Use type hints for all public APIs
- **Docstrings:** Use Google-style docstrings

**Example:**

```python
from typing import Optional

from myfy.core import Container, provider, SINGLETON


@provider(scope=SINGLETON)
def create_database(config: DatabaseConfig) -> Database:
    """Create a database connection.

    Args:
        config: Database configuration settings.

    Returns:
        Configured database instance.

    Raises:
        ConnectionError: If database connection fails.
    """
    return Database(config.url)
```

### Type Checking

We use `ty` for type checking:

```bash
# Check types
uv run ty check packages/

# Check specific package
uv run ty check packages/myfy-core/
```

## Project Structure

### Package Layout

Each package follows this structure:

```
packages/myfy-core/
├── myfy/
│   └── core/
│       ├── __init__.py      # Public API exports
│       ├── version.py       # Version info
│       ├── di.py            # DI container
│       ├── config.py        # Configuration
│       └── kernel.py        # Application kernel
├── tests/
│   ├── __init__.py
│   ├── test_di.py
│   └── test_config.py
├── pyproject.toml           # Package metadata
├── README.md                # Package documentation
└── CHANGELOG.md             # Package changelog
```

### Adding a New Module

To add a new module to an existing package:

1. Create the module file: `packages/myfy-core/myfy/core/new_module.py`
2. Implement your functionality
3. Add to `__init__.py` exports
4. Write tests: `packages/myfy-core/tests/test_new_module.py`
5. Update documentation
6. Submit PR

### Adding a New Package

To add a new package to the monorepo:

1. Create package directory: `mkdir -p packages/myfy-newpackage/myfy/newpackage`
2. Add `pyproject.toml`
3. Add to workspace in root `pyproject.toml`:
   ```toml
   [tool.uv.workspace]
   members = [
       "packages/myfy-core",
       "packages/myfy-web",
       "packages/myfy-cli",
       "packages/myfy-frontend",
       "packages/myfy",
       "packages/myfy-newpackage",  # New package
   ]
   ```
4. Add workspace source
5. Create version.py
6. Create __init__.py
7. Write tests
8. Update documentation
9. Submit PR

## Documentation

Documentation is built with MkDocs and hosted on GitHub Pages.

### Running Docs Locally

```bash
# Install docs dependencies
uv sync --group docs

# Serve docs locally
uv run mkdocs serve

# View at http://localhost:8000
```

### Writing Documentation

- Add documentation to `docs/` directory
- Use Markdown format
- Include code examples
- Update `mkdocs.yml` navigation if adding new pages

### API Documentation

API docs are auto-generated from docstrings:

```python
def my_function(param: str) -> int:
    """Short description.

    Longer description with more details about what this function does.

    Args:
        param: Description of parameter.

    Returns:
        Description of return value.

    Raises:
        ValueError: When parameter is invalid.

    Examples:
        >>> my_function("test")
        42
    """
    return 42
```

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Check existing issues before creating new ones

## License

By contributing to myfy, you agree that your contributions will be licensed under the project's license.

---

Thank you for contributing to myfy! 🚀
