# Changelog - myfy-data

All notable changes to myfy-data will be documented in this file.

## [Unreleased]

## [0.1.2] - 2025-12-13

### Added
- Async SQLAlchemy integration with REQUEST-scoped sessions
- DatabaseSettings with Pydantic configuration
- SessionFactory for managing async database sessions
- Connection pooling with configurable parameters
- Alembic migrations support via MigrationManager
- IDataProvider protocol for module extension
- Testing utilities (test_database, TestDatabaseFixture)
- Support for SQLite, PostgreSQL, and MySQL async drivers
