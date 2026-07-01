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
- [x] P0: Project Skeleton
- [x] P1: Data Layer — 10 tables, 5,204/5,528 stocks synced (94.1%), 13 API endpoints
- [x] P2: Frontend — stock list, K-line charts (ECharts), financial dashboard, boards
- [x] P3: Quant Engine — 9 technical indicators, stock screener, backtest (3 strategies)

> Note: Original P2 (Scheduler) + P3 (API) merged into P1. Original P4 (Frontend) → P2, P5 (Quant) → P3.

## Project Summary (as of 2026-07-01)

### Backend — 25 Python files, 3,344 lines
- ORM: 10 data tables + sync_status
- API: 17 endpoints (health + stocks/13 + boards/2 + quant/4)
- Services: sync, query, indicators, screener, backtest, safe_syncer, rate_limiter
- Tasks: 6 APScheduler incremental sync jobs
- Scripts: sync_sina, sync_financials, sync_full, sync_stocks, sync_daily

### Frontend — 11 TS/TSX files
- Pages: Stocks (list + detail + KlineChart + FinancialsView), Boards, Screener, Backtest
- Services: stock.ts (all API wrappers), typings.d.ts

### Data — 1,636 万行日K线, 5,528 只股票, 99.3% 行业覆盖
- sync_sina.py: Sina source (stable, ~2.5h for full daily K-line)
- sync_financials.py: Sina source with SafeSyncer anti-blocking (~1.5h)
- 东方财富 source: intermittent IP blocks, use SafeSyncer when syncing

### API Docs
- Online: http://localhost:8000/docs (Swagger)
- Offline: docs/api/api-reference.md

### Remaining Data (not yet synced)
| Table | Notes |
|-------|-------|
| stock_daily_quote | ✅ 16.4M rows (missing 324 北交所) |
| stock_financial_indicator | 🔄 script ready: `python scripts/sync_financials.py` |
| stock_weekly_quote | ⏳ needs script |
| stock_monthly_quote | ⏳ needs script |
| stock_performance_report | ⏳ `stock_yjbb_em()` (东方财富) |
| stock_fund_flow_daily | ⏳ `stock_individual_fund_flow()` (东方财富, blocked) |
| stock_board_info/member | ⏳ 东方财富, blocked |
| stock_profit_forecast | ⏳ 东方财富, blocked |

### Optional Future
- User auth, Tushare data source migration, portfolio backtest, CI/CD, tests
| stock_profit_forecast | ❌ empty | Analyst estimates |

### Optional Enhancements
- Authentication / user accounts
- Multi-stock portfolio backtest
- Factor analysis / risk model
- Real-time push (WebSocket)
- Docker one-click deploy
- Unit / integration tests
- CI/CD pipeline

## Key Decisions
See `docs/decisions/` for Architecture Decision Records.
See `docs/database/p1-data-layer-design.md` for P1 detailed design.

## Environment Restoration
- **After reboot**: `docs/dev-guide/setup.md` → start MySQL, then `make dev-backend`
- **New machine**: `docs/dev-guide/new-machine-setup.md` → clone, install, migrate, `make sync-full` (~46 min)
- **Data portability**: `make db-export` on old machine → `make db-import` on new machine (fastest)
