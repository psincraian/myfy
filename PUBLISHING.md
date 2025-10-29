# Publishing Guide

This document explains how to publish the myfy packages to PyPI.

## Table of Contents

- [Overview](#overview)
- [Versioning Strategy](#versioning-strategy)
- [Publishing Workflows](#publishing-workflows)
- [PyPI Trusted Publishing Setup](#pypi-trusted-publishing-setup)
- [Manual Release Process](#manual-release-process)
- [Troubleshooting](#troubleshooting)

## Overview

The myfy monorepo contains 5 publishable packages:

1. **myfy-core** - Core dependency injection, configuration, and module system
2. **myfy-web** - Web/ASGI module with routing
3. **myfy-cli** - CLI tools for running applications
4. **myfy-frontend** - Frontend integration with Tailwind 4, DaisyUI 5, and Vite
5. **myfy** - Meta-package for convenient installation

All packages use **synchronized versioning**, meaning they all share the same version number.

## Versioning Strategy

### Synchronized Versions

All packages are released together with matching versions. This simplifies:
- Dependency management between packages
- User understanding of compatibility
- Release coordination

### Version Patterns

We use two versioning approaches:

#### 1. Alpha Releases (Automatic)

**Format:** `{major}.{minor}.{patch}a{commit_count}`
**Example:** `0.1.0a123`

- Auto-published on every push to `main` that modifies `packages/**`
- Version is calculated from total commit count
- Used for continuous deployment and testing
- Available immediately on PyPI

**Trigger:** Automatic on push to main

#### 2. Stable Releases (Manual)

**Format:** `{major}.{minor}.{patch}` or `{major}.{minor}.{patch}{prerelease}`
**Examples:** `1.0.0`, `1.2.0b1`, `2.0.0rc1`

- Manually triggered via GitHub Actions
- Uses commitizen for version bumping and changelog generation
- Creates GitHub releases with release notes
- Tagged in git with `v{version}`

**Trigger:** Manual workflow dispatch

### Dependency Constraints

Internal dependencies use **different constraints** based on release type:

**For stable releases** (`~=` - compatible release):
```toml
# Example: myfy-web depends on myfy-core
dependencies = [
    "myfy-core~=1.0.0",  # Allows 1.0.x but not 1.1.0
]
```

**For pre-releases** (`==` - exact version):
```toml
# Example: alpha versions
dependencies = [
    "myfy-core==0.1.0a15",  # Exact match required
]
```

**Why different constraints?**
- **Pre-releases (alpha/beta/rc)**: Use exact version (`==`) because `~=` doesn't work with pre-release versions in pip
- **Stable releases**: Use compatible release (`~=`) to allow patch updates while preventing breaking changes

This ensures:
- Alpha versions install together correctly
- Stable releases allow automatic patch updates
- Users get compatible package versions

## Publishing Workflows

### Automatic Alpha Publishing

**Workflow:** `.github/workflows/publish.yml`
**Trigger:** Push to `main` with changes to `packages/**`

**Process:**
1. Runs tests across Python 3.12 and 3.13
2. Lints code with ruff
3. Type checks with ty
4. Calculates alpha version: `{base_version}a{commit_count}`
5. Updates all version files
6. Builds all 5 packages in dependency order
7. Publishes to PyPI using trusted publishing
8. Validates installation across Python versions

**Publishing Order:**
1. myfy-core (no internal dependencies)
2. myfy-web & myfy-cli (parallel, both depend on core)
3. myfy-frontend (depends on core + web)
4. myfy (meta-package, depends on all)

### Manual Stable Releases

**Workflow:** `.github/workflows/release.yml`
**Trigger:** Manual workflow dispatch

**Parameters:**
- `bump_type`: `patch`, `minor`, or `major`
- `prerelease`: Optional suffix (e.g., `b1`, `rc1`)

**Process:**
1. Bumps version using commitizen
2. Generates changelog from conventional commits
3. Updates all version files and dependencies
4. Runs full test suite
5. Builds all packages
6. Creates git tag `v{version}`
7. Pushes changes and tag to repository
8. Creates GitHub release with notes
9. Publishes to PyPI
10. Validates installation

**Example Usage:**

```bash
# Patch release (e.g., 1.0.0 → 1.0.1)
Go to Actions → Release to PyPI → Run workflow
  bump_type: patch

# Minor release (e.g., 1.0.1 → 1.1.0)
Go to Actions → Release to PyPI → Run workflow
  bump_type: minor

# Beta release (e.g., 1.0.0 → 1.1.0b1)
Go to Actions → Release to PyPI → Run workflow
  bump_type: minor
  prerelease: b1
```

## PyPI Trusted Publishing Setup

We use PyPI's **Trusted Publishing** (OIDC-based) instead of API tokens.

### Prerequisites

For each package, you need to configure PyPI:

1. Go to https://pypi.org/manage/account/
2. Navigate to "Publishing" tab
3. Add a new trusted publisher for each package

### Configuration per Package

Configure these 5 trusted publishers:

#### myfy-core
- **PyPI Project:** `myfy-core`
- **Owner:** `{your-github-username-or-org}`
- **Repository:** `myfy`
- **Workflow:** `publish.yml` AND `release.yml`
- **Environment:** (leave empty)

#### myfy-web
- **PyPI Project:** `myfy-web`
- **Owner:** `{your-github-username-or-org}`
- **Repository:** `myfy`
- **Workflow:** `publish.yml` AND `release.yml`
- **Environment:** (leave empty)

#### myfy-cli
- **PyPI Project:** `myfy-cli`
- **Owner:** `{your-github-username-or-org}`
- **Repository:** `myfy`
- **Workflow:** `publish.yml` AND `release.yml`
- **Environment:** (leave empty)

#### myfy-frontend
- **PyPI Project:** `myfy-frontend`
- **Owner:** `{your-github-username-or-org}`
- **Repository:** `myfy`
- **Workflow:** `publish.yml` AND `release.yml`
- **Environment:** (leave empty)

#### myfy
- **PyPI Project:** `myfy`
- **Owner:** `{your-github-username-or-org}`
- **Repository:** `myfy`
- **Workflow:** `publish.yml` AND `release.yml`
- **Environment:** (leave empty)

### First-Time Setup

If the packages don't exist on PyPI yet:

1. Create an account on https://pypi.org/
2. Manually upload the first version of each package (one-time only):

```bash
# Install build tools
uv pip install build twine

# Build and upload myfy-core first
cd packages/myfy-core
uv build
twine upload dist/*

# Then myfy-web
cd ../myfy-web
uv build
twine upload dist/*

# Continue for other packages...
```

3. After the first manual upload, configure Trusted Publishing as described above
4. All subsequent releases will use the automated workflows

## Manual Release Process

### Using Commitizen Locally

You can also bump versions locally:

```bash
# Install commitizen
uv pip install commitizen

# Bump version (patch/minor/major)
cz bump --increment patch

# Or use interactive mode
cz bump

# Push changes
git push origin main --tags
```

### Manual Package Build

To build packages locally without publishing:

```bash
# Build all packages
cd packages/myfy-core && uv build && cd ../..
cd packages/myfy-web && uv build && cd ../..
cd packages/myfy-cli && uv build && cd ../..
cd packages/myfy-frontend && uv build && cd ../..
cd packages/myfy && uv build && cd ../..

# Packages are in packages/*/dist/
```

### Testing Before Release

Test packages locally before publishing:

```bash
# Install in development mode
uv sync --all-extras --dev

# Run tests
uv run pytest

# Run linters
uv run ruff check packages/
uv run ruff format --check packages/

# Run type checking
uv run ty check packages/

# Test install from built packages
pip install packages/myfy-core/dist/myfy_core-*.whl
python -c "import myfy.core; print(myfy.core.__version__)"
```

## Troubleshooting

### Version Mismatch Errors

If you get version mismatch errors during installation:

```python
# This error:
ERROR: Cannot install myfy-web because these package versions have conflicting dependencies.
```

**Solution:** Ensure all packages were published with the same version. Check:

```bash
# View versions on PyPI
pip index versions myfy-core
pip index versions myfy-web
pip index versions myfy-cli
pip index versions myfy-frontend
pip index versions myfy
```

### Publishing Failures

**Trusted Publishing not configured:**
```
Error: Trusted publisher configuration not found
```

**Solution:** Configure trusted publishers on PyPI as described above.

**Package already exists:**
```
Error: File already exists
```

**Solution:** You cannot overwrite existing versions. Bump the version and try again.

### Test Failures

If tests fail during the workflow:

1. Check the GitHub Actions logs for the specific failure
2. Run tests locally: `uv run pytest -v`
3. Fix the issue and push a new commit
4. The workflow will run again automatically

### Import Errors After Installation

If imports fail after installing from PyPI:

```python
ModuleNotFoundError: No module named 'myfy.core'
```

**Solution:** Check that the package was built correctly:

```bash
# Download and inspect the package
pip download myfy-core --no-deps
tar -tzf myfy_core-*.tar.gz

# Should show:
# myfy_core-X.Y.Z/myfy/
# myfy_core-X.Y.Z/myfy/core/
# myfy_core-X.Y.Z/myfy/core/__init__.py
# etc.
```

### Dependency Resolution Issues

If `uv` or `pip` cannot resolve dependencies:

1. Clear the cache: `uv cache clean` or `pip cache purge`
2. Try installing in a fresh virtual environment
3. Check that internal version constraints are correct in all `pyproject.toml` files

## Changelog Management

Changelogs are managed using conventional commits and commitizen:

### Conventional Commit Format

Use this format for all commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions/changes
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Other changes

**Scopes:**
- `core`: myfy-core package
- `web`: myfy-web package
- `cli`: myfy-cli package
- `frontend`: myfy-frontend package
- `meta`: myfy meta-package
- `workspace`: monorepo changes
- `docs`: documentation
- `ci`: CI/CD

**Examples:**

```bash
git commit -m "feat(core): add support for async providers"
git commit -m "fix(web): resolve middleware ordering issue"
git commit -m "docs(workspace): update publishing guide"
```

### Generating Changelog

Changelogs are automatically generated during releases from conventional commits.

To generate manually:

```bash
cz changelog
```

This updates all `CHANGELOG.md` files based on commits since the last release.

## Resources

- [PyPI Trusted Publishing Guide](https://docs.pypi.org/trusted-publishers/)
- [Commitizen Documentation](https://commitizen-tools.github.io/commitizen/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [UV Documentation](https://docs.astral.sh/uv/)
- [GitHub Actions](https://docs.github.com/en/actions)
