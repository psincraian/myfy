# Development Scripts

This directory contains helpful scripts for myfy development.

## 🪝 Git Hooks

### Installing Git Hooks

After cloning the repository, run:

```bash
./scripts/install-hooks.sh
```

This will install the pre-commit hook that automatically:
1. 🎨 **Formats code** with `ruff format`
2. 🔍 **Lints code** with `ruff check`
3. 🔬 **Type checks** with `ty check`

### Pre-commit Hook

The pre-commit hook (`scripts/hooks/pre-commit`) runs automatically before each commit.

**What it does:**
- Detects staged Python files
- Runs `ruff format` and re-stages formatted files
- Runs `ruff check` to ensure no linting issues
- Runs `ty check` to ensure no type errors
- Blocks the commit if any check fails

**Skipping the hook (not recommended):**
```bash
git commit --no-verify
```

### Manual Checks

You can run the same checks manually:

```bash
# Format code
uv run ruff format packages/ examples/

# Check linting
uv run ruff check packages/ examples/

# Auto-fix linting issues
uv run ruff check packages/ examples/ --fix

# Type check
uv run ty check packages/
```

## 📋 Requirements

- [uv](https://docs.astral.sh/uv/) package manager
- Dependencies installed: `uv sync`

## 🚀 Best Practices

1. **Always install hooks** after cloning the repository
2. **Let hooks run** - they catch issues early
3. **Fix issues before committing** - don't skip hooks unless absolutely necessary
4. **Run manual checks** if you modify the hook behavior

## 🔧 Customization

To modify the pre-commit hook:
1. Edit `scripts/hooks/pre-commit`
2. Run `./scripts/install-hooks.sh` to update `.git/hooks/pre-commit`
3. Test with a dummy commit
