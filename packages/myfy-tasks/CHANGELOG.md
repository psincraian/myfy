# Changelog

All notable changes to myfy-tasks will be documented in this file.

## [0.1.0] - Unreleased

### Added

- Initial release of myfy-tasks module
- `@task` decorator for defining async tasks
- SQL-based task queue (database-agnostic)
- `TasksModule` with full lifecycle support
- `TaskContext` for progress reporting
- `TaskResult[T]` for typed result retrieval
- `TaskWorker` for processing tasks
- CLI commands: `myfy tasks worker`, `myfy tasks list`, `myfy tasks stats`
- Dependency injection in tasks (same pattern as web handlers)
- Automatic retries with configurable delay
- Graceful shutdown handling
