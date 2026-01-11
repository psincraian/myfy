---
description: Interactive scaffolding wizard for myfy components
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# myfy Scaffolding Wizard

Help the user create myfy components interactively.

## Process

1. **Ask what to scaffold**

Present these options to the user:
- **Module** - Create a new myfy module with settings and service
- **Route** - Create a new route handler with DI
- **Provider** - Create a DI provider with correct scope
- **Task** - Create a background task
- **Settings** - Create a settings class
- **Full Feature** - Create module + routes + providers + tasks for a complete feature

2. **For each choice, gather requirements**

### Module
- Module name (e.g., "notifications", "payments")
- Dependencies (WebModule, DataModule, etc.)
- What services it provides
- Description

### Route
- HTTP method (GET, POST, PUT, DELETE, PATCH)
- Path (e.g., "/users/{user_id}")
- Request body model (for POST/PUT/PATCH)
- Required DI dependencies
- Authentication required?

### Provider
- Service type being provided
- Scope (SINGLETON, REQUEST, TASK)
- Dependencies it needs
- Purpose

### Task
- Task name and purpose
- Parameters
- Progress reporting needed?
- Retry behavior

### Settings
- Setting fields and types
- Default values
- Environment prefix
- Validation rules

### Full Feature
- Feature name (e.g., "notifications")
- Then gather requirements for all components

3. **Generate the code**

Use the appropriate scaffolding patterns from the myfy plugin agents.

4. **Show the user what was created**

List all created files and provide usage examples.

## Example Interaction

User: /myfy:scaffold