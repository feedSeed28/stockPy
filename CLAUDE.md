# CLAUDE.md

## Project Overview
Stock Quant System (stock_py) — a full-stack quantitative stock analysis platform.
**Scope**: A-stock (A股) market only.

## Tech Stack
- **Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.0 async + asyncmy (MySQL 8)
- **Frontend**: React 18 + Ant Design Pro v6 + Umi Max + ECharts
- **Data Source**: AKShare (no API key needed, free & open source)
- **Task Scheduler**: APScheduler (AsyncIOScheduler)
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
- Connection driver: asyncmy (async), pymysql (sync for Alembic)
- Naming: snake_case table/column names
- Base model includes: id (UUID), created_at, updated_at
- Batch upsert: INSERT ON DUPLICATE KEY UPDATE (MySQL-native, via dialect)

### Code Architecture
- **Backend**: API → Service → Model (strict 3-layer)
- **Frontend**: Pages → Components → Services (strict 3-layer)
- No business logic in routes/API layer
- No raw SQL in routes

### Project Structure
```
stock_py/
├── backend/              # Python FastAPI
│   ├── app/
│   │   ├── api/v1/       # Route handlers
│   │   ├── services/     # Business logic + sync
│   │   ├── models/       # SQLAlchemy ORM
│   │   ├── schemas/      # Pydantic models
│   │   ├── core/         # Config, database
│   │   └── tasks/        # APScheduler jobs
│   ├── alembic/          # DB migrations
│   └── tests/
├── frontend/             # React Ant Design Pro
├── docs/                 # Documentation & ADRs
├── docker/               # Docker configs
├── CLAUDE.md             # This file
└── Makefile              # Common commands
```

## Database Tables (P1 — 10 tables)

| Table | Rows est. | Purpose |
|-------|-----------|---------|
| `stock_info` | 5,500 | A股基本信息 |
| `stock_daily_quote` | ~40M | 日K线 (by year partition) |
| `stock_weekly_quote` | ~8M | 周K线 |
| `stock_monthly_quote` | ~2M | 月K线 |
| `stock_performance_report` | 500K | 季度业绩报表 |
| `stock_financial_indicator` | 600K | 财务指标 (25 columns) |
| `stock_profit_forecast` | 100K | 分析师盈利预测 |
| `stock_fund_flow_daily` | ~5M | 每日资金流向 |
| `stock_board_info` | 500 | 行业/概念板块 |
| `stock_board_member` | 100K | 板块成分股 |
| `sync_status` | 10 | 同步状态追踪 |

## Sync Strategy

- **Initial**: One-time full load via `make sync-full` (takes ~46 min)
- **Incremental**: APScheduler daily at 16:00 Beijing time
  - Daily K-line: last 5 days per stock
  - Fund flow: last 5 days
  - Stock list: weekly check for new listings
  - Performance reports: daily check for new quarters
  - Weekly K-line: Mondays 16:30
  - Monthly K-line: 1st of month 16:30
- **Rate limit**: 3 calls/sec (TokenBucket), 5 concurrent tasks
- **Retry**: 3 attempts with exponential backoff (1s → 4s → 16s)
- **Resume**: `sync_status` table tracks progress, restart skips already-synced data

## Current Phase
- [x] P0: Project Skeleton (completed)
- [x] P1: Data Layer (models, AKShare sync service, API endpoints)
- [ ] P2: Scheduler (APScheduler tasks — integrated in P1)
- [ ] P3: API Layer (CRUD endpoints — integrated in P1)
- [ ] P4: Frontend (pages, charts)
- [ ] P5: Quant Engine (indicators, backtesting)

## Key Decisions
See `docs/decisions/` for Architecture Decision Records.
See `docs/database/p1-data-layer-design.md` for P1 detailed design.

## Environment Restoration
- **After reboot**: `docs/dev-guide/setup.md` → start MySQL, then `make dev-backend`
- **New machine**: `docs/dev-guide/new-machine-setup.md` → clone, install, migrate, `make sync-full` (~46 min)
- **Data portability**: `make db-export` on old machine → `make db-import` on new machine (fastest)
