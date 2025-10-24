# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the myfy framework.

## What are ADRs?

Architecture Decision Records document important architectural decisions made in the project, including:
- The context and problem being addressed
- The decision made and why
- Consequences of the decision
- Alternatives that were considered

## Index

- [ADR-0001: Record Architecture Decisions](0001-record-architecture-decisions.md) - Establishes the practice of using ADRs
- [ADR-0002: Modular Configuration Design](0002-modular-configuration-design.md) - Module-owned configuration pattern
- [ADR-0003: Dependency Injection with Scopes](0003-dependency-injection-with-scopes.md) - Scoped DI container design

## Creating New ADRs

1. Copy `template.md` to a new file with format `XXXX-title-with-dashes.md`
2. Use the next sequential number (check existing ADRs)
3. Fill in all sections of the template
4. Submit as part of a pull request
5. Once merged, the ADR is considered accepted and immutable

## ADR Lifecycle

- **Proposed** - Initial draft under discussion
- **Accepted** - Decision has been made and is active
- **Deprecated** - Decision is no longer recommended but still documented
- **Superseded** - Replaced by a newer ADR (reference the new one)

ADRs should not be edited once accepted. If a decision changes, create a new ADR that supersedes the old one.
