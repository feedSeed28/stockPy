# CLAUDE.md

## Project Overview
Stock Quant System (stock_py) — A-stock quantitative analysis platform.
**Scope**: A股沪深两市 only（排除北交所、B股、港股、基金、期货）.

## ⚠️ Critical: IP Blocking Warning
**Server IP has been blocked by Sina and 东方财富 due to batch sync.**
- ❌ Batch sync from server (8 concurrent × 5,530 stocks) → IP blocked immediately
- ✅ Frontend direct calls from browser (user IP) → safe
- ✅ Single-stock queries via LiveFetcher → safe (1 request per user view)
- If re-syncing on new machine: use 1 concurrent + 5s delay + run 2-6am
- See `memory/ip-blocking-lessons.md` for details

## Quick Start (New Machine)
```bash
git clone <repo> stock_py && cd stock_py
cd backend && pip install -r requirements.txt && cp .env.example .env
# Start MySQL, then:
alembic upgrade head
# ⚠️ IMPORTANT: Run sync with LOW concurrency to avoid IP block:
python scripts/sync_sina.py        # K-line full sync (~2.5h, set SYNC_CONCURRENCY=1)
python scripts/sync_financials.py  # Financial indicators (~1.5h, EM source, SafeSyncer)
python -m uvicorn app.main:app --reload --port 8000
# Frontend (another terminal):
cd frontend && pnpm install && pnpm dev
# Open http://localhost:8001
```

## Tech Stack
- **Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.0 async + asyncmy (MySQL 8) — 38 py files, 27 API endpoints
- **Frontend**: React 18 + Ant Design Pro v6 + Umi Max + ECharts — 10 pages
- **Data**: AKShare (东方财富 EM APIs for browser-direct, Sina for server K-line)
- **Scheduler**: APScheduler (daily 16:00 incremental)
- **DB**: MySQL 8, database=stock_data, user=admin

## Architecture: Dual-Mode Data Sources

| Mode | Data Path | Default | Toggle Location |
|------|-----------|---------|-----------------|
| 💾 后端接口 | Browser → FastAPI → MySQL | ✅ Default | Data Management page |
| 🔥 前端直连 | Browser → 东方财富 API (user IP) | Manual | Data Management page |

## Product Direction
- Frontend should remain useful when the backend is not running.
  - Direct mode uses browser-side 东方财富 APIs for market, K-line, quotes, boards, and limit-up views where CORS allows it.
  - Backend mode uses FastAPI + MySQL for cached historical data, strategy research, and endpoints that cannot be called from browser.
- Backend is primarily a data sync/cache service plus quant research engine.
  - Keep sync scripts conservative to avoid IP blocks.
  - Keep indicators, screeners, and backtests usable from API and CLI scripts.
  - Quant implementation lives under `backend/app/quant/`; API routers call quant modules directly.
- Backend responsibilities are separated by entry point:
  - `backend/scripts/sync_stocks.py`: synchronize the stock master list only.
  - `backend/scripts/sync_daily.py`: incrementally synchronize daily qfq K-line data.
  - `backend/scripts/sync_financials.py`: slowly synchronize financial indicators with resume and anti-blocking controls.
  - `backend/scripts/sync_full.py`: orchestrate the full historical database sync; use only during controlled maintenance windows.
  - `backend/scripts/backfill_stock_industry.py`: local DB backfill from latest `stock_performance_report.industry` to `stock_info.industry`.
  - `backend/scripts/export_frontend_data.py`: read MySQL and generate static JSON for the standalone frontend. It does not synchronize upstream data.
  - `backend/scripts/run_backtest.py`: run a local CLI strategy research job from MySQL data. It does not belong to the API request path.
  - FastAPI: provide queries, status, and explicit task-triggering endpoints; it should not contain bulk-sync or backtest orchestration.
- Static export lets the frontend read generated JSON without a running backend.
- Backend static export is available via `backend/scripts/export_frontend_data.py`.
  - UI entry: Data Management page → 前端静态数据导出.
  - API entry: `POST /api/v1/data/export-static`, `GET /api/v1/data/export-static/status`.
  - Default export writes `stocks.json`, `market.latest.json`, `boards.json`, and `manifest.json`.
  - K-line export is opt-in: use `--symbols 000001,600000` or `--all-kline --kline-limit 500`.
  - Default output is `frontend/public/data/`, which is ignored by git.

## Correctness Rules
- Recent K-line windows must query latest rows first (`ORDER BY trade_date DESC LIMIT N`) and then reverse to chronological order before indicator/slope calculations.
- Backtests must not execute a signal on the same bar that generated it. Current rule: signal is generated on close and executed at the next bar open with slippage/commission.
- Backtests use A-share daily trading rules by default: 100-share lots, configurable commission/min commission, sell-side stamp tax, slippage, T+1, suspension/no-volume skip, and price-limit execution blocks.
- Price-limit defaults: ST 5%, ChiNext/STAR 20%, Beijing-style prefixes 30%, otherwise 10%. ST stocks are rejected by API unless `exclude_st=false`.
- Board member APIs should accept internal board UUIDs; backend query service also tolerates external `board_code` for compatibility.
- Screener `between` conditions require both `value` and `value2`; normalize reversed bounds before comparison.

**Key files:**
- `frontend/src/services/dataProvider.ts` — unified frontend data provider (`backendProvider` / `directProvider`)
- `frontend/src/utils/dataSource.ts` — mode state (localStorage)
- `frontend/src/services/eastmoney.ts` — 东方财富 browser API wrapper (14 functions, all CORS ✅)
- `frontend/src/pages/DataManagement/index.tsx` — toggle UI
- `backend/app/services/live_fetcher.py` — DB-first with AKShare fallback
- `backend/scripts/export_frontend_data.py` — MySQL → frontend static JSON export
- `backend/scripts/backfill_stock_industry.py` — local industry backfill for stock list display
- `backend/scripts/run_backtest.py` — CLI backtest entry point backed by local MySQL data
- `backend/app/quant/indicators.py` — technical indicators and signal helpers
- `backend/app/quant/screener.py` — multi-condition stock screener
- `backend/app/quant/backtest.py` — strategies and backtest runner

**Backend quant package boundary:**
- `app.quant` owns indicators, strategy definitions, screeners, and backtest execution.
- `app.api.v1.quant` and `app.api.v1.slope` call `app.quant` directly.
- `app.services.indicator_service`, `app.services.screener_service`, and `app.services.backtest_service` are compatibility wrappers only; new code should not import them.
- Backtest rule tests live in `backend/tests/test_backtest_a_share_rules.py`.

**Provider migration status:**
- Migrated: stock detail summary, K-line chart, market overview, boards, limit-up.
- Backend-only by design for now: screener, backtest, slope, LHB, data management.
- New frontend data calls should go through `getStockDataProvider()` unless the feature is explicitly backend-only.

## API (27 endpoints)
| Group | Endpoints |
|-------|-----------|
| stocks | list, detail, daily/weekly/monthly K-line, performance, financials, forecast, fund-flow, kline-range, today |
| boards | list, members |
| quant | indicators (9 types), screener, backtest (3 strategies), strategies list |
| market | today (sortable OHLCV overview) |
| slope | scan (trend screening: strong_up/mild_up/sideways/mild_down/strong_down) |
| limit-up | period (local DB, period-based, with historical stats) |
| lhb | daily detail, institution, stock-stats (Sina source ✅) |
| data | sync-status, trigger-sync, export-static, export-static/status |
| health | health check |

## Database (12 tables)
| Table | Status | Rows |
|-------|--------|------|
| stock_info | ✅ Complete | 5,530 |
| stock_daily_quote | ⚠️ Stops at 2026-07-03 | 16.4M |
| stock_weekly_quote | ✅ | 6,036 |
| stock_monthly_quote | ⚠️ Partial | 813 |
| stock_financial_indicator | ✅ Complete (EM source) | 314K (5,206 stocks) |
| stock_performance_report | ✅ Complete (EM source) | 208K |
| stock_profit_forecast | ✅ Complete (EM source) | 2,355 |
| stock_fund_flow_daily | ❌ EM blocked | 1,440 |
| stock_board_info | ✅ | 464 |
| stock_board_member | ❌ EM blocked | 0 |
| sync_status | ✅ | 8 |

## Frontend (10 pages)
| Page | Route | Direct Mode | Backend Mode |
|------|-------|-------------|--------------|
| 股票列表 | /stocks | — | ProTable DB query |
| 股票详情 | /stocks/:code | EM real-time + K-line + financials | Backend DB + LiveFetcher |
| 板块 | /boards | EM industry/concept + members | Backend DB |
| 选股 | /screener | — (backend-only) | Multi-condition scan |
| 回测 | /backtest | — (backend-only) | Strategy + equity curve |
| 趋势 | /slope | — (backend-only) | MA slope scan |
| 行情 | /market | EM market list (all stocks) | Backend DB |
| 涨停板 | /limit-up | EM limit-up pool (today) | DB period query |
| 龙虎榜 | /lhb | — (Sina no CORS) | Backend Sina proxy |
| 数据管理 | /data-management | Toggle + sync status | Trigger sync |

## Data Sources Status (2026-07-10)
| Source | Server Access | Browser Access | Used For |
|--------|--------------|----------------|----------|
| Sina (新浪) | ⚠️ IP blocked for batch, OK singles | ❌ No CORS | Server K-line, 龙虎榜 |
| 东方财富 push2 | ⚠️ Partial | ✅ CORS | Real-time quotes, K-line, boards |
| 东方财富 push2his | ❌ Blocked (TLS) | ✅ CORS | Historical K-line, fund flow |
| 东方财富 datacenter | ✅ | ✅ CORS * | Financial indicators |
| 东方财富 datacenter-web | ✅ | ✅ CORS * | Performance, forecasts |
| 同花顺 | ✅ | — | Boards (backend) |

## Key Commands (Windows)
```bash
# Backend
cd backend && set PYTHONUTF8=1 && python -m uvicorn app.main:app --reload --port 8000
# Frontend
cd frontend && pnpm dev
# Sync data (⚠️ use LOW concurrency: SYNC_CONCURRENCY=1 in stock_sync_service.py)
cd backend && set PYTHONUTF8=1 && python scripts/sync_sina.py
cd backend && set PYTHONUTF8=1 && python scripts/sync_financials.py
# Recommended Make targets (run from the repository root)
make sync-stocks
make sync-daily
make sync-financials
make sync-full
# Backfill local stock industry names from performance report data
make backfill-industry
# Export data for a standalone frontend
make export-frontend-data
# Run a CLI backtest without putting research orchestration in FastAPI
make run-backtest ARGS="--stock 000001 --strategy ma_cross"
# Export static JSON for standalone frontend
cd backend && set PYTHONUTF8=1 && python scripts/export_frontend_data.py
cd backend && set PYTHONUTF8=1 && python scripts/export_frontend_data.py --symbols 000001,600000 --periods daily,weekly
# Export DB for transfer
mysqldump -h localhost -u admin -pZggDLAXkkHXFwQVM --no-create-info --single-transaction stock_data > stock_data_dump.sql
```

## Important Notes
- `python` not `python3` on Windows
- `PYTHONUTF8=1` needed for Chinese comments in source
- 北交所 (8xxxxx/4xxxxx/92xxxx) excluded
- **Batch sync concurrency**: NEVER use >2 concurrent workers for Sina/EM APIs
- **Frontend direct mode** avoids server IP blocking entirely (browser IP per user)
- **LiveFetcher** auto-fetches single stocks from AKShare when DB is empty
- `stock_financial_indicator` now uses EM source (`_em` function), Sina version is broken
- `tsc --noEmit` should pass before frontend changes are considered complete.

## Docs
- API reference: docs/api/api-reference.md
- Setup guide: docs/dev-guide/setup.md
- Architecture: docs/architecture.md
- Memory: `memory/MEMORY.md` — full knowledge base index
- Plan: `plans/warm-beaming-wind.md` — architecture design doc
