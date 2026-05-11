# AGENTS.md - Backend Engineering Guide

This document defines how AI agents must work in this FastAPI backend. The goal
is not only to generate code, but to protect the architecture so the system can
grow without being rewritten.

## 1. Core Principle

Every change must preserve this flow:

```text
Route -> Service -> Repository -> Database
```

Each layer has exactly one responsibility:

- Route: HTTP handling.
- Service: business rules and workflows.
- Repository: database access.
- Schemas: request validation and response formatting.
- Models: database structure.
- Providers: dependency creation and injection.

Do not blur these boundaries.

## 2. Required Pre-Work Before Coding

Before generating or modifying code, agents must:

1. Read the project structure.
2. Identify the feature/app being changed.
3. Search for existing models, schemas, services, repositories, and routes.
4. Reuse existing logic where possible.
5. Extend an existing feature instead of creating a duplicate feature.
6. Confirm the change fits the established architecture.

Expected backend structure:

```text
app/
  main.py
  core/
  apps/
  shared/
```

If the structure does not exist yet, create it intentionally and consistently.

## 3. Layer Rules

### 3.1 Routes - `routes.py`

Routes may only:

- Receive requests.
- Validate request input through schemas or FastAPI dependencies.
- Call the service layer.
- Return responses.

Routes must not contain:

- Business logic.
- Database queries.
- Complex workflows.
- Direct model manipulation.

### 3.2 Services - `service.py`

Services must contain:

- Business rules.
- Workflows.
- Use-case orchestration.
- Validations that go beyond schema validation.
- Calls to repositories.

Services must not contain:

- Direct database queries.
- HTTP-specific logic.
- FastAPI response handling.

### 3.3 Repositories - `repository.py`

Repositories must contain:

- Database queries.
- Persistence operations.
- Query-specific helpers.

Repositories must not contain:

- Business rules.
- Request validation.
- HTTP behavior.
- Cross-feature workflows.

### 3.4 Schemas - `schemas.py`

Schemas are used for:

- Input validation.
- Response formatting.
- Typed API contracts.

Schemas must not contain business workflows or database access.

### 3.5 Models - `models.py`

Models define database structure only.

All SQLAlchemy ORM models must use the modern SQLAlchemy 2.0 typed declarative
style:

- Use `Mapped[...]` for every mapped attribute.
- Use `mapped_column(...)` for columns.
- Use typed `relationship(...)` declarations when relationships are needed.
- Do not use legacy `Column(...)` declarations in ORM models.

Models must not contain:

- Business logic.
- Request handling.
- Service workflows.

### 3.6 Providers - `providers.py`

Providers are used to:

- Create repositories.
- Create services.
- Wire dependencies for FastAPI.

Providers must keep dependency setup explicit and easy to trace.

## 4. Feature Structure

Each feature/app must follow this structure:

```text
feature_name/
  models.py
  schemas.py
  repository.py
  service.py
  routes.py
  providers.py
```

Do not put an entire feature in one file.

Feature code must stay isolated. For example, code inside `users/` must not
leak into `payments/`. Cross-feature interaction must be explicit, minimal, and
handled through the correct service boundaries.

## 5. Naming Rules

Use clear, predictable names:

- `UserService`
- `UserRepository`
- `UserCreateSchema`
- `UserReadSchema`
- `UserUpdateSchema`

Names should describe the feature and responsibility. Avoid vague names such as
`Manager`, `Handler`, `Helper`, or `Utils` unless the existing project pattern
already requires them.

## 6. Safety and Reliability

### 6.1 Race Conditions

When logic updates data or depends on existing state, assume concurrent
requests may happen.

Prefer:

- Database constraints.
- Unique indexes.
- Transactions.
- Atomic updates.

Avoid unsafe read-modify-write patterns unless protected by database-level
guarantees.

### 6.2 Error Handling

Failures must be explicit.

Agents must:

- Return meaningful errors.
- Avoid exposing raw internal exceptions.
- Avoid silent failures.
- Keep error handling consistent with existing project patterns.

### 6.3 Duplication

Before adding new logic, search the codebase.

Do not duplicate:

- Models.
- Schemas.
- Services.
- Repositories.
- Validation rules.
- Business workflows.

Reuse or extend existing code where it makes sense.

## 7. Database Rules

- Use Alembic migrations for schema changes.
- Do not rely on automatic table creation in production.
- Keep models simple and structural.
- Write ORM models with SQLAlchemy 2.0 `Mapped` and `mapped_column` syntax.
- Track every database schema change in a migration.

## 8. Function Design

Functions should be small and focused.

Each function should:

- Do one thing.
- Have a clear name.
- Be easy to test.
- Avoid hidden side effects.

Large workflows should be split into private service methods or repository
helpers when that improves readability.

## 9. Adding a Feature

Follow this order:

1. Check whether the feature already exists.
2. Identify the correct feature/app directory.
3. Create or update `models.py`.
4. Create or update `schemas.py`.
5. Create or update `repository.py`.
6. Create or update `service.py`.
7. Create or update `providers.py`.
8. Create or update `routes.py`.
9. Register the routes in `app/main.py`.
10. Add or update Alembic migrations when models change.
11. Verify there is no duplicated logic.
12. Verify the layer separation is correct.

## 10. Output Requirements for AI Agents

When generating code, agents must:

- Follow the project structure exactly.
- Keep code readable and minimal.
- Add comments only when they explain purpose or non-obvious behavior.
- Avoid overengineering.
- Respect existing patterns before introducing new ones.
- Include tests when the change has meaningful behavior or risk.

## 11. Red Flags

Do not do any of the following:

- Put business logic inside routes.
- Put database queries inside services.
- Put validation or workflows inside repositories.
- Duplicate models, schemas, services, or repositories.
- Create a new feature when an existing feature should be extended.
- Write large unstructured functions.
- Ignore existing project patterns.
- Hide failures or swallow exceptions silently.
- Add or keep legacy SQLAlchemy ORM `Column(...)` model declarations.
- Change database structure without a migration.

## 12. Final Standard

Code should be simple, layered, testable, and easy for the next engineer to
extend.

The responsibility of an agent is not to generate code quickly. The
responsibility is to generate code that can scale without being rewritten.
