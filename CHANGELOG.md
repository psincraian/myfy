# Changelog

All notable changes to the myfy monorepo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


### Added
- Initial release of myfy framework
- Core dependency injection system
- Web/ASGI module with routing
- CLI tools
- Frontend module with Tailwind 4 and DaisyUI 5
- Comprehensive documentation

## v0.1.2 (2025-11-16)

### Refactor

- **ci**: use only one file for publishing to pypi

## v0.1.1 (2025-11-16)

### Feat

- **newsletter**: add offline captcha for newsletter subscription (#18)
- **frontend**: implement cache headers for static assets (#19)
- add favicons
- **website**: add docker image
- **website**: add myfy website (#12)
- **cli**: add Klyne tracking to all CLI commands (#10)
- **cli**: add myfy start (#7)
- **chore**: allow to override params using classes
- add doc image
- add klyne
- **frontend**: improve the example website
- **cli**: have a fully functional app on init
- **cli**: add frontend init
- **workspace**: add code quality agent
- **workspace**: add package version and publishig
- first version of frontend module
- add hooks
- add ruff and ty
- first commit

### Fix

- **ci**: release to PyPI
- **ci**: release
- **docker**: copy images directory to dist for static serving (#17)
- **website**: add favicon configuration to base template (#15)
- **web**: change default host to 0.0.0.0 for Docker compatibility (#14)
- **website**: use database env var
- **website**: deploy
- **frontend**: static assets (#8)
- config override
- **cli**: load config from settings
- **docs**: update repo url
- **frontend**: vite health check timeout error (#2)
- **ci**: exclude stubs
- **frontend**: scaffold dir
- **ci**: make sure that alphaa depends on alpha
- **ci**: version
- **ci**: versioning
- **ci**: building
- **ci**: added __init__.py files to namespace directories for proper editable installs
- format

### Refactor

- **website**: remove leaf effects and background from website (#16)
- **ci**: reuse workflows
