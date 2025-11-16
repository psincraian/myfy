# ADR-0006: Monorepo Versioning and PyPI Publishing Strategy

## Status

Accepted

## Context

The myfy framework is structured as a monorepo containing five publishable packages (myfy-core, myfy-web, myfy-cli, myfy-frontend, and myfy meta-package). We need to establish:

1. **Version Management Strategy**: How to version packages in a monorepo where packages depend on each other
2. **Release Automation**: How to automate publishing to PyPI for both development and stable releases
3. **Dependency Management**: How to express internal dependencies between packages
4. **Changelog Generation**: How to maintain changelogs across multiple packages
5. **Developer Experience**: How to enforce consistent commit messages and automate versioning

Key constraints and tensions:

- **Complexity vs. Simplicity**: Independent versioning per package provides granularity but increases cognitive load for users
- **Compatibility**: Internal dependencies must remain compatible across versions
- **Automation vs. Control**: Automated releases increase velocity but may sacrifice control
- **Developer Friction**: Strict commit message requirements could slow down development
- **Publishing Order**: Packages must be published in dependency order to avoid installation failures

## Decision

We will implement a **synchronized versioning** strategy with **dual-track publishing**:

### 1. Synchronized Versioning

All five packages share the same version number at all times. When any package is released, all packages are released together.

**Rationale:**
- Simplifies user understanding of compatibility ("all 0.2.0 packages work together")
- Reduces complexity in dependency management
- Aligns with the cohesive nature of the framework
- Easier to communicate and document

**Implementation:**
- Single source of truth for version in root `pyproject.toml`
- Each package has a `version.py` file for runtime version access
- All packages export `__version__` for introspection
- Commitizen manages version bumping across all files simultaneously

### 2. Single Workflow, Dual-Mode Publishing

A unified workflow (`.github/workflows/publish.yml`) handles both alpha and stable releases through conditional logic:

**Alpha Release Mode (Automatic)**
- Format: `{major}.{minor}.{patch}a{commit_count}` (e.g., `0.1.0a123`)
- Trigger: Automatic on every push to `main` that modifies `packages/**`
- Purpose: Continuous deployment for testing and early adoption
- No git commits, tags, or GitHub releases created

**Stable Release Mode (Manual)**
- Format: `{major}.{minor}.{patch}` or with prerelease suffix (e.g., `1.0.0`, `1.2.0b1`)
- Trigger: Manual workflow dispatch with `release_type: stable`
- Purpose: Production-ready releases with full changelog and GitHub release
- Creates git commits, tags, and GitHub releases

### 3. Compatible Release Constraints (`~=`)

Internal dependencies use the compatible release operator:

```toml
dependencies = [
    "myfy-core~=0.1.0",  # Allows 0.1.x, blocks 0.2.0+
]
```

**Rationale:**
- Ensures patch updates are automatically compatible
- Prevents accidentally installing mismatched major/minor versions
- Balances flexibility with safety
- Standard practice in Python packaging (PEP 440)

### 4. Conventional Commits + Commitizen

We enforce conventional commit format for all commits:

```
<type>(<scope>): <subject>

[optional body]
[optional footer]
```

**Implementation:**
- `.cz.toml` configuration for commitizen
- `commit-msg` git hook for validation
- Interactive commit creation via `cz commit`
- Automatic changelog generation from commit history

**Types:** feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

**Scopes:** core, web, cli, frontend, meta, workspace, docs, ci

### 5. Publishing Order

Packages are always published in dependency order:

1. `myfy-core` (no internal dependencies)
2. `myfy-web` & `myfy-cli` (parallel - both depend only on core)
3. `myfy-frontend` (depends on core + web)
4. `myfy` (meta-package - depends on all)

### 6. PyPI Trusted Publishing

Use OIDC-based trusted publishing instead of API tokens:

- No secrets stored in GitHub
- GitHub Actions authenticates directly with PyPI
- Per-package trusted publisher configuration
- More secure and maintainable

## Consequences

### Positive

1. **User Simplicity**: Users always know which versions work together
2. **Reduced Cognitive Load**: No need to track multiple version numbers
3. **Consistent Release Process**: Same workflow for all packages
4. **Automated Testing**: Every alpha release is tested before publishing
5. **Clear History**: Conventional commits create readable git history
6. **Automated Changelogs**: Changelogs generated from commits
7. **Fast Iteration**: Alpha releases enable continuous deployment
8. **Controlled Stability**: Manual stable releases for production use
9. **Better Security**: Trusted publishing eliminates token management
10. **Developer Guardrails**: Git hooks catch issues before commit
11. **Simpler PyPI Configuration**: Only one trusted publisher per package (not two)
12. **Single Source of Truth**: One workflow to maintain and understand

### Negative

1. **Larger Releases**: Even small changes to one package require releasing all packages
2. **Version Number Inflation**: Version numbers increase faster than individual packages would
3. **Download Overhead**: Users downloading updates get all packages even if only one changed
4. **Commit Message Discipline**: Developers must follow conventional commit format
5. **Initial Setup Complexity**: PyPI trusted publishing requires one-time configuration per package

### Neutral

1. **Testing Burden**: All packages must be tested even if only one changed (but this is good practice)
2. **Git History**: Conventional commits are more verbose but more informative
3. **Two Release Tracks**: Developers must understand alpha vs. stable releases
4. **Monorepo Lock-in**: Moving packages out of monorepo would require significant rework

## Alternatives Considered

### Alternative 1: Independent Versioning

Each package maintains its own version number.

**Pros:**
- Smaller, more targeted releases
- Version numbers reflect actual changes per package
- More granular semantic versioning

**Cons:**
- Complex dependency matrix (which versions work together?)
- User confusion about compatibility
- Harder to document and communicate
- Requires careful dependency constraint management
- Testing matrix explosion

**Rejected because:** The packages are designed to work together as a cohesive framework, not as independent libraries.

### Alternative 2: Separate Workflows for Alpha and Stable

Use two distinct workflows: `publish.yml` for alpha, `release.yml` for stable.

**Pros:**
- Clear separation of concerns
- Each workflow optimized for its purpose
- Easier to understand each individual workflow

**Cons:**
- Requires two trusted publisher configurations per package (10 total)
- Duplicate code between workflows
- More maintenance burden
- More complex PyPI setup

**Initially implemented, then rejected in favor of:** Single unified workflow provides same functionality with less complexity and easier PyPI configuration.

### Alternative 3: Git Tags for Versioning

Use git tags as single source of truth, generate versions from tags.

**Pros:**
- Single source of truth
- Common practice in some ecosystems
- Automatic version from tag

**Cons:**
- Harder to automate in CI/CD
- Requires tag-based triggers
- More complex to implement with commitizen
- Version not visible in source code

**Rejected because:** Explicit version files are clearer and work better with our tooling.

### Alternative 4: API Tokens Instead of Trusted Publishing

Use PyPI API tokens stored in GitHub Secrets.

**Pros:**
- Simpler initial setup
- Works everywhere (not GitHub-specific)
- More familiar to developers

**Cons:**
- Security risk if tokens leak
- Token rotation required
- Need to manage 5 separate tokens (one per package)
- Less secure than OIDC

**Rejected because:** Trusted publishing is the modern, recommended approach by PyPI.

### Alternative 5: Minimum Version Dependencies (`>=`)

Keep using minimum version constraints for internal dependencies.

**Pros:**
- More flexible
- Allows any future version
- Standard in some ecosystems

**Cons:**
- Can install incompatible versions
- No protection against breaking changes
- Users could get broken combinations
- Less safe

**Rejected because:** Compatible release (`~=`) better balances flexibility and safety.

## References

- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Commitizen Documentation](https://commitizen-tools.github.io/commitizen/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- `PUBLISHING.md` - Detailed publishing guide
- `CONTRIBUTING.md` - Developer contribution guidelines
- `.cz.toml` - Commitizen configuration
- `.github/workflows/publish.yml` - Unified publishing workflow

## Implementation Notes

### Files Created/Modified

**Configuration:**
- `.cz.toml` - Commitizen config with monorepo support
- `pyproject.toml` - Added commitizen dev dependency

**Version Management:**
- `packages/*/version.py` - Version modules for each package (5 files)
- `packages/*/__init__.py` - Export `__version__` in each package (5 files)

**Changelogs:**
- `CHANGELOG.md` - Root changelog
- `packages/*/CHANGELOG.md` - Per-package changelogs (5 files)

**Workflows:**
- `.github/workflows/publish.yml` - Unified workflow for both alpha and stable releases

**Git Hooks:**
- `scripts/hooks/commit-msg` - Validates conventional commits
- `scripts/hooks/pre-commit` - Linting, formatting, type checking
- `scripts/install-hooks.sh` - Installs both hooks

**Documentation:**
- `PUBLISHING.md` - Complete publishing guide
- `CONTRIBUTING.md` - Developer guidelines with commit format
- `.github/PYPI_SETUP_SUMMARY.md` - Quick setup reference

### Dependency Constraint Updates

All internal dependencies updated from `>=` to `~=`:
- `myfy-web`: Depends on `myfy-core~=0.1.0`
- `myfy-cli`: Depends on `myfy-core~=0.1.0`
- `myfy-frontend`: Depends on `myfy-core~=0.1.0`, `myfy-web~=0.1.0`
- `myfy`: Depends on `myfy-core~=0.1.0`, `myfy-cli~=0.1.0`, optional `myfy-web~=0.1.0`

### Testing Requirements

Before any publish:
1. Linting with ruff across all packages
2. Type checking with ty across all packages
3. Test suite execution with pytest
4. Post-publish validation on Python 3.12 and 3.13

### Version Calculation

**Alpha versions:**
```bash
TOTAL_COMMITS=$(git rev-list --count HEAD)
BASE_VERSION="0.1.0"  # From pyproject.toml
VERSION="${BASE_VERSION}a${TOTAL_COMMITS}"
```

**Stable versions:**
- Commitizen analyzes conventional commits
- Determines bump type (MAJOR for breaking, MINOR for feat, PATCH for fix)
- Updates all version files simultaneously
- Creates git tag `v{version}`

## Future Considerations

1. **Test Publishing**: Consider adding TestPyPI workflow before production PyPI
2. **Release Notifications**: Automate release announcements (Discord, Slack, etc.)
3. **Version Badges**: Add version badges to README files
4. **Breaking Change Detection**: Automated API compatibility checking
5. **Performance Tracking**: Monitor package size and build time trends
6. **Multi-Platform Testing**: Expand test matrix to include macOS and Windows
7. **Documentation Versioning**: Version docs to match releases (e.g., with mike)
8. **Canary Releases**: Consider adding canary track between alpha and stable

## Decision Log

- **2025-10-29**: ADR created and accepted
- **2025-11-16**: Updated to consolidate dual workflows into single unified workflow
  - Changed from separate alpha and stable workflows to single `publish.yml`
  - Rationale: Simpler PyPI trusted publisher configuration (5 vs 10 configurations)
  - Maintains same functionality with conditional logic for alpha vs stable modes
- **Decision maker**: Project maintainers
- **Review date**: To be reviewed after 3 months of usage (2026-02-16)
