# CLAUDE.md

## Project Overview
Stock Quant System (stock_py) — a full-stack quantitative stock analysis platform.

## Tech Stack
- **Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.0 async + asyncmy (MySQL 8)
- **Frontend**: React 18 + Ant Design Pro v6 + Umi Max + ECharts
- **Data Source**: AKShare
- **Task Scheduler**: APScheduler
- **Database**: MySQL 8 (database: stock_data)
- **Package Manager**: pip (backend) / pnpm (frontend)

## Core Conventions

### API
- All responses use unified format: `{ code: int, message: str, data: T | null }`
- API prefix: `/api/v1/`
- Swagger docs at: `/docs`
- CORS allowed: `localhost:8001`
- Health check: `GET /api/v1/health`

### Database
- ORM: SQLAlchemy 2.0 async with DeclarativeBase
- Migration: Alembic (configured in `backend/alembic/`)
- Connection driver: asyncmy (async), mysqldb (sync for Alembic)
- Naming: snake_case table/column names
- Base model includes: id (UUID), created_at, updated_at

### Code Architecture
- **Backend**: API → Service → Model (strict 3-layer)
- **Frontend**: Pages → Components → Services (strict 3-layer)
- No business logic in routes/API layer
- No raw SQL in routes

### Project Structure
```
stock_py/
├── backend/           # Python FastAPI
├── frontend/          # React Ant Design Pro
├── docs/              # Documentation & ADRs
├── scripts/           # DevOps scripts
├── CLAUDE.md          # This file
└── Makefile           # Common commands
```

## Current Phase
- [x] P0: Project Skeleton (completed)
- [ ] P1: Data Layer (database models, AKShare integration)
- [ ] P2: Scheduler (APScheduler tasks)
- [ ] P3: API Layer (CRUD endpoints)
- [ ] P4: Frontend (pages, charts)
- [ ] P5: Quant Engine (indicators, backtesting)

## Key Decisions
See `docs/decisions/` for Architecture Decision Records.
