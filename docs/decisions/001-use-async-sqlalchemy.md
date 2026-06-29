# ADR 001: Use SQLAlchemy Async Mode

## Status
Accepted

## Date
2026-06-26

## Context
The backend needs to handle concurrent data fetching from AKShare and serve API requests. Traditional synchronous ORM would block the event loop.

## Decision
Use SQLAlchemy 2.0 async with `asyncmy` driver for MySQL.

## Alternatives Considered

| Option | Rejected Because |
|--------|-----------------|
| Tortoise ORM | Less mature, smaller community |
| SQLAlchemy sync | Blocks FastAPI event loop |
| raw asyncmy (no ORM) | Loses migration and model safety |

## Consequences

### Positive
- Fully async, non-blocking database access
- Compatible with FastAPI's async paradigm
- Alembic migration support
- Large community and documentation

### Negative
- Some SQLAlchemy features require async syntax adaptation
- `asyncmy` has occasional version compatibility issues with MySQL 8.x updates
