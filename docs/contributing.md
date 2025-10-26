# Contributing to myfy

Thank you for your interest in contributing to myfy!

---

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/petru/myfy.git
cd myfy
```

### 2. Install Dependencies

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install workspace dependencies
uv sync

# Install packages in editable mode
uv pip install -e packages/myfy-core
uv pip install -e packages/myfy-web
uv pip install -e packages/myfy-cli
```

### 3. Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=myfy --cov-report=html

# Run specific test
uv run pytest tests/test_di.py
```

### 4. Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type check
uv run ty check
```

---

## Project Structure

```
myfy/
├── packages/
│   ├── myfy-core/      # Core framework
│   ├── myfy-web/       # Web module
│   └── myfy-cli/       # CLI tools
├── examples/           # Example applications
├── docs/               # Documentation
└── tests/              # Tests
```

---

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Your Changes

- Write code
- Add tests
- Update documentation

### 3. Run Checks

```bash
# Format
uv run ruff format .

# Lint
uv run ruff check .

# Test
uv run pytest

# Type check
uv run ty check
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add my feature"
```

**Commit Message Format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance

### 5. Push and Create PR

```bash
git push origin feature/my-feature
```

Then create a pull request on GitHub.

---

## Guidelines

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings (Google style)
- Keep functions focused and small

### Testing

- Write tests for new features
- Maintain >80% coverage
- Use pytest fixtures
- Test edge cases

### Documentation

- Update docs for new features
- Add examples
- Keep docs up-to-date
- Use clear, simple language

---

## Questions?

- Open an issue on GitHub
- Join our discussions

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
