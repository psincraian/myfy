---
description: Run myfy doctor and validate the application
allowed-tools: Bash, Read, Grep
---

# myfy Check Command

Validate the myfy application configuration and run health checks.

## Process

1. **Run myfy doctor**

```bash
uv run myfy doctor
```

This checks:
- Application can be discovered and loaded
- All modules are properly configured
- DI container compiles successfully
- Settings are valid

2. **Run linting**

```bash
uv run ruff check .
```

3. **Run type checking** (if ty is available)

```bash
uv run ty check .
```

4. **Run tests**

```bash
uv run pytest
```

5. **Report results**

Summarize:
- Doctor check: PASS/FAIL
- Linting: PASS/FAIL (with issue count)
- Type checking: PASS/FAIL
- Tests: PASS/FAIL (with test count)

If any checks fail, provide guidance on how to fix the issues.

## Quick Mode

If the user just wants a quick check:

```bash
uv run myfy doctor && uv run ruff check . && uv run pytest -x
```

## Arguments

- `--quick` - Only run myfy doctor
- `--fix` - Auto-fix linting issues with `ruff check --fix`
- `--verbose` - Show detailed output
