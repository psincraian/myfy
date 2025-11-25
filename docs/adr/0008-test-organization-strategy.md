# ADR-0008: Test Organization Strategy

## Status

Accepted

## Context

The myfy framework is a monorepo containing multiple packages (myfy-core, myfy-web, myfy-cli, myfy-frontend, and the myfy meta-package). We need to establish a consistent testing strategy that addresses:

1. **Test Organization**: Where to place tests in a monorepo structure
2. **Test Categories**: How to categorize tests by scope and purpose
3. **Parallel Execution**: Ensuring tests can run in parallel without interference
4. **Developer Experience**: Making it easy to run tests for a specific package or the entire project
5. **CI Integration**: Running tests automatically on every pull request and push

Key constraints and tensions:

- **Isolation vs. Integration**: Unit tests need isolation, but e2e tests need the full stack
- **Speed vs. Coverage**: Comprehensive tests take longer to run
- **Package Independence vs. Cross-Package Testing**: Packages should be testable independently, but we also need to verify they work together
- **Fixture Sharing**: Common fixtures should be reusable, but package-specific fixtures shouldn't leak

## Decision

We will implement a **distributed test structure** with **three test tiers** and **package-local fixtures**:

### 1. Three-Tier Test Taxonomy

**Unit Tests** (`packages/*/tests/unit/`)
- Test isolated components, edge cases, and difficult-to-test scenarios
- Mock all external dependencies
- Fast execution (< 100ms per test)
- Examples: circular dependency detection, scope context isolation, provider decorator mechanics

**Integration Tests** (`packages/*/tests/integration/`)
- Test a single module with all its classes working together
- May use real implementations within the module
- Moderate execution time
- Examples: full DI resolution chains, route registration and handler execution, CLI command parsing

**E2E Tests** (`tests/e2e/`)
- Test complete application workflows across multiple packages
- Use the full stack with minimal mocking
- Located in root `tests/` folder (cross-package)
- Examples: HTTP request/response cycles, application lifecycle, multi-module interactions

### 2. Distributed Test Structure

Tests are co-located with their packages, not in a central location:

```
myfy/
├── tests/                              # E2E tests only (cross-package)
│   ├── conftest.py                     # E2E-specific fixtures
│   └── e2e/
│       └── test_full_application.py
│
├── packages/
│   ├── myfy-core/
│   │   └── tests/
│   │       ├── conftest.py             # Core package fixtures
│   │       ├── unit/
│   │       │   ├── test_container_edge_cases.py
│   │       │   ├── test_scope_context.py
│   │       │   └── test_provider_decorator.py
│   │       └── integration/
│   │           ├── test_core_di_integration.py
│   │           └── test_core_application.py
│   │
│   ├── myfy-web/
│   │   └── tests/
│   │       ├── conftest.py             # Web package fixtures
│   │       └── integration/
│   │           ├── test_web_routing.py
│   │           └── test_web_handlers.py
│   │
│   ├── myfy-cli/
│   │   └── tests/
│   │       ├── conftest.py             # CLI package fixtures
│   │       └── integration/
│   │           └── test_cli_commands.py
│   │
│   └── myfy-frontend/
│       └── tests/
│           ├── conftest.py             # Frontend package fixtures
│           └── integration/
│               └── test_frontend_assets.py
```

**Rationale:**
- Tests live close to the code they test
- Each package can be tested independently
- Package-specific fixtures don't leak to other packages
- Clear ownership of tests

### 3. Package-Local Fixtures

Each package has its own `conftest.py` with fixtures specific to that package:

- **myfy-core**: Container fixtures, scope context fixtures, mock modules
- **myfy-web**: Service containers, mock request factories, debug containers
- **myfy-cli**: CLI runner, temporary app directories
- **myfy-frontend**: Frontend settings, temporary static directories with manifests

Fixtures are not shared across packages to ensure test isolation and prevent fixture conflicts.

### 4. Parallel Execution Support

All tests are designed to run in parallel using pytest-xdist:

- No shared mutable state between tests
- Each test creates its own container instance
- Scope contexts are cleaned up after each test via autouse fixtures
- Provider registrations are cleared between tests

```bash
# Run all tests in parallel
pytest -n auto

# Run specific package tests
pytest packages/myfy-core/tests -n auto
```

### 5. Test Markers

Tests are marked with pytest markers for selective execution:

```python
pytestmark = pytest.mark.unit        # For unit tests
pytestmark = pytest.mark.integration  # For integration tests
pytestmark = pytest.mark.e2e         # For e2e tests
pytestmark = pytest.mark.slow        # For slow-running tests
```

Run specific categories:
```bash
pytest -m unit           # Run only unit tests
pytest -m integration    # Run only integration tests
pytest -m e2e            # Run only e2e tests
pytest -m "not slow"     # Skip slow tests
```

### 6. Pytest Configuration

Centralized configuration in `pytest.ini`:

```ini
[pytest]
testpaths =
    tests
    packages/myfy-core/tests
    packages/myfy-web/tests
    packages/myfy-cli/tests
    packages/myfy-frontend/tests

asyncio_mode = auto
asyncio_default_fixture_loop_scope = function

markers =
    unit: Unit tests for isolated logic and edge cases
    integration: Integration tests for module interactions
    e2e: End-to-end tests for full application workflows
    slow: Tests that take longer to execute
```

### 7. CI Integration

Tests run automatically in GitHub Actions CI:

- On every push to `main`
- On every pull request
- Tests run on Python 3.12 and 3.13
- Both sequential and parallel execution verified

```yaml
- name: Run all tests
  run: uv run pytest -v --tb=short

- name: Run tests in parallel
  run: uv run pytest -n auto --tb=short -q
```

## Consequences

### Positive

1. **Clear Ownership**: Each package owns its tests
2. **Fast Feedback**: Unit tests run in milliseconds
3. **Parallel Safe**: Tests don't interfere with each other
4. **Selective Execution**: Run only what's needed
5. **CI/CD Ready**: Automated testing on every change
6. **Scalable Structure**: Easy to add tests as packages grow
7. **Good Coverage**: 211 tests covering edge cases, integration, and e2e
8. **Documentation**: Tests serve as executable documentation

### Negative

1. **Fixture Duplication**: Some fixtures are similar across packages (by design for isolation)
2. **Navigation**: Tests are spread across multiple directories
3. **Initial Setup**: Each package needs its own conftest.py
4. **Cross-Package Testing**: E2E tests are separate from package tests

### Neutral

1. **No __init__.py**: Test directories don't have `__init__.py` to avoid import conflicts
2. **Marker Discipline**: Developers must remember to mark tests appropriately
3. **Two Test Locations**: Package tests vs e2e tests in different places

## Alternatives Considered

### Alternative 1: Centralized Test Directory

All tests in a single `tests/` directory at the root:

```
tests/
├── unit/
│   └── core/
│   └── web/
├── integration/
└── e2e/
```

**Pros:**
- Single location for all tests
- Easier to find tests
- Simpler pytest configuration

**Cons:**
- Tests far from the code they test
- Hard to run package-specific tests
- Fixture management becomes complex
- Doesn't scale well with monorepo

**Rejected because:** Doesn't align with monorepo package independence.

### Alternative 2: Tests Inside Package Source

Tests inside the package source directory:

```
packages/myfy-core/myfy/core/tests/
```

**Pros:**
- Tests maximally close to code
- Tests shipped with package

**Cons:**
- Tests included in published packages
- Increases package size
- May confuse users

**Rejected because:** Tests shouldn't be distributed to end users.


## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-xdist](https://pytest-xdist.readthedocs.io/) - Parallel test execution
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) - Async test support
- [ADR-0006: Monorepo Versioning](0006-monorepo-versioning-and-publishing.md) - Package structure
- `.github/workflows/ci.yml` - CI workflow configuration
- `pytest.ini` - Pytest configuration


### Running Tests

```bash
# All tests
uv run pytest

# All tests in parallel
uv run pytest -n auto

# Specific package
uv run pytest packages/myfy-core/tests

# Specific category
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m e2e

# With coverage
uv run pytest --cov=myfy --cov-report=html
```

## Decision Log

- **2025-11-25**: ADR created and accepted
- **Decision maker**: Project maintainers
