# PyPI Publishing Setup - Summary

This document summarizes the complete PyPI publishing system implemented for the myfy monorepo.

## What Was Implemented

### 1. Version Management

**Synchronized Versioning:**
- All 5 packages share the same version number
- Version stored in multiple locations:
  - Each `pyproject.toml` (6 total: root + 5 packages)
  - Each `version.py` (5 packages)
  - `.cz.toml` (commitizen config)

**Version Files Created:**
- `packages/myfy-core/myfy/core/version.py`
- `packages/myfy-web/myfy/web/version.py`
- `packages/myfy-cli/myfy_cli/version.py`
- `packages/myfy-frontend/myfy/frontend/version.py`
- `packages/myfy/myfy/version.py`

**Version Exports:**
- All packages now export `__version__` in their `__init__.py`
- Accessible via: `import myfy.core; print(myfy.core.__version__)`

### 2. Dependency Management

**Updated Internal Dependencies:**
- Changed from `>=` to `~=` (compatible release)
- Example: `myfy-core~=0.1.0` allows 0.1.x but not 0.2.0
- Ensures patch updates work, prevents breaking changes

**Affected Files:**
- `packages/myfy-web/pyproject.toml`
- `packages/myfy-cli/pyproject.toml`
- `packages/myfy-frontend/pyproject.toml`
- `packages/myfy/pyproject.toml`

### 3. Commitizen Configuration

**File:** `.cz.toml`

**Features:**
- Conventional commit format enforcement
- Automatic version bumping
- Changelog generation from commits
- Interactive commit creation: `cz commit`

**Commit Types:** feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

**Scopes:** core, web, cli, frontend, meta, workspace, docs, ci

### 4. Changelog Files

**Created CHANGELOG.md for:**
- Root: `CHANGELOG.md` (monorepo-wide)
- `packages/myfy-core/CHANGELOG.md`
- `packages/myfy-web/CHANGELOG.md`
- `packages/myfy-cli/CHANGELOG.md`
- `packages/myfy-frontend/CHANGELOG.md`
- `packages/myfy/CHANGELOG.md`

**Format:** Keep a Changelog compatible, auto-updated by commitizen

### 5. GitHub Actions Workflow

#### Unified Publishing Workflow (`.github/workflows/publish.yml`)

A **single workflow** handles both alpha and stable releases through conditional logic.

**Triggers:**
- **Automatic:** Push to `main` with changes to `packages/**` (alpha mode)
- **Manual:** Workflow dispatch (alpha or stable mode)

**Manual Workflow Inputs:**
- `release_type`: `alpha` or `stable` (default: `alpha`)
- `bump_type`: `patch`, `minor`, or `major` (default: `patch`)
- `prerelease`: Optional suffix (e.g., "b1", "rc1")

**Jobs:**

1. **CI** - Runs across Python 3.12 & 3.13
   - Linting (ruff)
   - Type checking (ty)
   - Tests (pytest)

2. **Release** (conditional based on mode)
   
   **Alpha Mode:**
   - Calculates version: `{base}a{commit_count}` (e.g., `0.1.0a123`)
   - Updates all version files
   - Builds packages in dependency order
   - Publishes to PyPI via trusted publishing
   - **No git commits, tags, or GitHub releases**
   
   **Stable Mode:**
   - Bumps version with commitizen
   - Generates changelog
   - Updates all version files and dependencies
   - Runs full test suite
   - Builds all packages
   - **Creates git commit and tag**
   - **Pushes changes and tag**
   - **Creates GitHub release**
   - Publishes to PyPI

3. **Validate Release**
   - Tests installation across Python versions
   - Verifies imports and version consistency
   - Tests CLI functionality

**Publishing Order:**
1. myfy-core
2. myfy-web & myfy-cli (parallel)
3. myfy-frontend
4. myfy (meta-package)

### 6. Git Hooks

**Pre-commit Hook:** `scripts/hooks/pre-commit`
- Formats code with ruff
- Lints with ruff
- Type checks with ty
- Auto-stages formatted files

**Commit-msg Hook:** `scripts/hooks/commit-msg` (NEW)
- Validates conventional commit format
- Checks message length (10-100 chars)
- Provides helpful error messages
- Skips validation for merge/revert commits

**Installation Script:** `scripts/install-hooks.sh` (UPDATED)
- Installs both pre-commit and commit-msg hooks
- Run with: `./scripts/install-hooks.sh`

### 7. Documentation

**PUBLISHING.md** (NEW)
- Complete guide to publishing packages
- Versioning strategy explained
- Workflow documentation
- PyPI Trusted Publishing setup instructions
- Troubleshooting guide
- Changelog management

**CONTRIBUTING.md** (NEW)
- Development setup guide
- Conventional commits tutorial
- Pull request process
- Testing guidelines
- Code style rules
- Project structure overview

## File Changes Summary

### New Files Created (16)
1. `.cz.toml` - Commitizen configuration
2. `CHANGELOG.md` - Root changelog
3. `packages/myfy-core/CHANGELOG.md`
4. `packages/myfy-web/CHANGELOG.md`
5. `packages/myfy-cli/CHANGELOG.md`
6. `packages/myfy-frontend/CHANGELOG.md`
7. `packages/myfy/CHANGELOG.md`
8. `packages/myfy-core/myfy/core/version.py`
9. `packages/myfy-web/myfy/web/version.py`
10. `packages/myfy-cli/myfy_cli/version.py`
11. `packages/myfy-frontend/myfy/frontend/version.py`
12. `packages/myfy/myfy/version.py`
13. `packages/myfy/myfy/__init__.py` - Meta-package init
14. `.github/workflows/publish.yml` - Unified publishing workflow
15. `scripts/hooks/commit-msg` - Commit validation
16. `PUBLISHING.md` - Publishing guide
17. `CONTRIBUTING.md` - Contributing guide

### Modified Files (11)
1. `pyproject.toml` - Added commitizen dependency
2. `packages/myfy-core/pyproject.toml` - (version constraint ready)
3. `packages/myfy-web/pyproject.toml` - Updated to `~=`
4. `packages/myfy-cli/pyproject.toml` - Updated to `~=`
5. `packages/myfy-frontend/pyproject.toml` - Updated to `~=`
6. `packages/myfy/pyproject.toml` - Updated to `~=`
7. `packages/myfy-core/myfy/core/__init__.py` - Added `__version__` export
8. `packages/myfy-web/myfy/web/__init__.py` - Added `__version__` export
9. `packages/myfy-cli/myfy_cli/__init__.py` - Added `__version__` export
10. `packages/myfy-frontend/myfy/frontend/__init__.py` - Added `__version__` export
11. `scripts/install-hooks.sh` - Added commit-msg hook installation

## Next Steps - IMPORTANT

### 1. Set Up PyPI Trusted Publishing

Before you can publish, configure PyPI for each package:

1. Create accounts on:
   - https://pypi.org/ (production)
   - https://test.pypi.org/ (testing)

2. For first-time publishing, manually upload one version:
   ```bash
   cd packages/myfy-core
   uv build
   uv pip install twine
   twine upload dist/*
   ```
   Repeat for all 5 packages.

3. Configure Trusted Publishers on PyPI:
   - Go to each project's PyPI page
   - Navigate to "Publishing" → "Add a new publisher"
   - **Only need one trusted publisher per package** (not two)

   Example for myfy-core:
   - PyPI Project: `myfy-core`
   - Owner: `YOUR-GITHUB-USERNAME-OR-ORG`
   - Repository: `myfy`
   - Workflow: `publish.yml`
   - Environment: (leave empty)

   Repeat for: myfy-web, myfy-cli, myfy-frontend, myfy
   
   **Total:** 5 trusted publishers (one per package)

### 2. Install Git Hooks

```bash
./scripts/install-hooks.sh
```

This installs:
- Pre-commit hook (formatting, linting, type checking)
- Commit-msg hook (conventional commit validation)

### 3. Install Commitizen

```bash
uv sync --dev
# Or
uv pip install commitizen
```

Use for interactive commits:
```bash
cz commit
```

### 4. Test the Setup

**Test Locally:**
```bash
# Install dependencies
uv sync --all-extras --dev

# Run tests
uv run pytest

# Test building packages
cd packages/myfy-core && uv build && cd ../..
```

**Test Commit Hooks:**
```bash
# Make a change
echo "# Test" >> README.md

# Try invalid commit (should fail)
git add README.md
git commit -m "invalid message"  # ❌ Should fail

# Try valid commit (should pass)
git commit -m "docs: test commit hook"  # ✅ Should pass
```

**Test Workflows:**
1. Push to `main` - triggers alpha publish workflow
2. Or manually trigger workflow:
   - Go to Actions → "Publish to PyPI" → "Run workflow"

### 5. Create Your First Release

When ready for a stable release:

1. Go to GitHub Actions
2. Select "Release to PyPI" workflow
3. Click "Run workflow"
4. Choose:
   - `bump_type`: patch/minor/major
   - `prerelease`: (optional, e.g., "b1")
5. Click "Run workflow"

This will:
- Bump all package versions
- Generate changelog
- Create git tag
- Create GitHub release
- Publish to PyPI

## Versioning Examples

**Alpha releases (automatic):**
- Push to main → `0.1.0a25`
- Another push → `0.1.0a26`
- Continuous deployment

**Stable releases (manual):**
- Release workflow with "patch" → `0.1.0`
- Release workflow with "minor" → `0.2.0`
- Release workflow with "major" → `1.0.0`
- Release with "minor" + "b1" → `0.2.0b1`

## Publishing Order

Packages are always published in dependency order to prevent installation issues:

```
1. myfy-core (no dependencies)
   ↓
2. myfy-web  }  (parallel - both depend only on core)
   myfy-cli  }
   ↓
3. myfy-frontend (depends on core + web)
   ↓
4. myfy (meta-package - depends on all)
```

## Troubleshooting

**If publishing fails:**
1. Check GitHub Actions logs
2. Verify PyPI Trusted Publishing is configured
3. Ensure package names are available on PyPI
4. Check that tests pass locally

**If version mismatch:**
1. All packages must have the same version
2. Internal dependencies use `~=` constraints
3. Workflows update all version files simultaneously

**If commits are rejected:**
1. Ensure commit follows conventional format
2. Use `cz commit` for interactive help
3. Use `git commit --no-verify` to skip hooks (not recommended)

## Resources

- **Publishing Guide:** See `PUBLISHING.md`
- **Contributing Guide:** See `CONTRIBUTING.md`
- **PyPI Trusted Publishing:** https://docs.pypi.org/trusted-publishers/
- **Commitizen:** https://commitizen-tools.github.io/commitizen/
- **Conventional Commits:** https://www.conventionalcommits.org/

## Support

For issues with the publishing setup:
1. Check `PUBLISHING.md` troubleshooting section
2. Review GitHub Actions logs
3. Open an issue with details

Happy publishing! 🚀
