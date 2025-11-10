# Testing Guide

This directory contains integration tests for the myfy framework. Package-specific unit tests are located in each package's `tests/` directory.

## Running Tests

### Run All Tests

```bash
# From repository root
uv run pytest
```

### Run Package-Specific Tests

```bash
# myfy-core
cd packages/myfy-core && uv run pytest tests/ -v

# myfy-web
cd packages/myfy-web && uv run pytest tests/ -v

# myfy-frontend
cd packages/myfy-frontend && uv run pytest tests/ -v

# myfy-cli
cd packages/myfy-cli && uv run pytest tests/ -v
```

### Run Integration Tests Only

```bash
uv run pytest tests/integration/ -v
```

## Coverage Reports

### Generate Coverage for All Packages

```bash
# Run tests with coverage
uv run pytest --cov=myfy --cov=myfy_cli --cov-report=html --cov-report=term

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Package-Specific Coverage

```bash
# myfy-core coverage
cd packages/myfy-core
uv run pytest tests/ --cov=myfy.core --cov-report=html --cov-report=term

# myfy-web coverage
cd packages/myfy-web
uv run pytest tests/ --cov=myfy.web --cov-report=html --cov-report=term
```

## Test Organization

```
myfy/
├── packages/
│   ├── myfy-core/tests/          # Core DI and config tests
│   ├── myfy-web/tests/            # Web routing and handler tests
│   ├── myfy-frontend/tests/       # Frontend template and asset tests
│   └── myfy-cli/tests/            # CLI command tests
└── tests/
    └── integration/               # Full-stack integration tests
```

## Writing Tests

### Test Structure

```python
class TestFeatureName:
    """Test feature description."""

    def test_specific_behavior(self):
        """Should do something specific."""
        # Arrange
        ...

        # Act
        ...

        # Assert
        ...
```

### Async Tests

```python
import pytest

class TestAsyncFeature:
    @pytest.mark.asyncio
    async def test_async_behavior(self):
        """Should handle async operations."""
        result = await async_function()
        assert result is not None
```

### Test Markers

```python
# Slow test
@pytest.mark.slow
def test_slow_operation():
    ...

# Integration test
@pytest.mark.integration
def test_full_stack():
    ...
```

Run with markers:
```bash
# Skip slow tests
uv run pytest -m "not slow"

# Run only integration tests
uv run pytest -m integration
```

## Coverage Goals

- **Overall**: >80% coverage
- **Core modules** (DI, config): >90% coverage
- **Web handlers**: >85% coverage
- **CLI commands**: >75% coverage
- **Frontend** (templates, assets): >80% coverage

## CI/CD

Tests run automatically on:
- Push to `main` or `develop`
- Pull requests
- Python 3.12 and 3.13

Coverage reports are uploaded to Codecov.
