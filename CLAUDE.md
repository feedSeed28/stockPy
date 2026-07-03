# CLAUDE.md

## Project Overview
Stock Quant System (stock_py) — A-stock quantitative analysis platform.
**Scope**: A股沪深两市 only（排除北交所、B股、港股、基金、期货）.

## Quick Start (New Machine)
```bash
git clone <repo> stock_py && cd stock_py
cd backend && pip install -r requirements.txt && cp .env.example .env
# Start MySQL, then:
alembic upgrade head
python scripts/sync_sina.py        # ~2.5h, Sina source, safe
python scripts/sync_financials.py  # ~1.5h, SafeSyncer anti-blocking
python -m uvicorn app.main:app --reload --port 8000
# Frontend (another terminal):
cd frontend && pnpm install && pnpm dev
# Open http://localhost:8001
```

## Tech Stack
- **Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.0 async + asyncmy (MySQL 8)
- **Frontend**: React 18 + Ant Design Pro v6 + Umi Max + ECharts
- **Data**: AKShare (Sina primary, 同花顺 secondary, 东方财富 blocked)
- **Scheduler**: APScheduler (daily 16:00 incremental)
- **DB**: MySQL 8, database=stock_data, user=admin

## API (21 endpoints)
| Group | Endpoints |
|-------|-----------|
| stocks | list, detail, daily/weekly/monthly K-line, performance, financials, forecast, fund-flow, kline-range, today |
| boards | list, members |
| quant | indicators (9 types), screener, backtest (3 strategies), strategies list |
| market | today (sortable OHLCV overview) |
| slope | scan (trend screening: strong_up/mild_up/sideways/mild_down/strong_down) |
| limit-up | period (local DB, period-based, with historical stats) |
| lhb | daily detail, institution, stock-stats (Sina source ✅) |
| health | health check |

## Database (12 tables)
- stock_info: 5,205 stocks, 99.3% industry coverage
- stock_daily_quote: 16.4M rows (Sina source, 前复权)
- stock_board_info: 464 boards (同花顺)
- stock_financial_indicator, stock_weekly_quote, stock_monthly_quote, stock_performance_report, stock_fund_flow_daily, stock_board_member, stock_profit_forecast: empty (scripts ready)

## Frontend (9 pages)
| Page | Route | Features |
|------|-------|----------|
| 股票列表 | /stocks | ProTable, exchange/board/status filters |
| 股票详情 | /stocks/:code | Today stats, limit-up counts, K-line ECharts, financials |
| 板块 | /boards | Industry/concept list, member drawer |
| 选股 | /screener | Multi-condition builder (ROE, margins, MA/MACD/RSI cross) |
| 回测 | /backtest | Strategy config, equity curve, metrics, trades |
| 趋势 | /slope | MA slope scan, 5 trend types, ST filter, period selector |
| 行情 | /market | Daily OHLCV, sortable, up/down/flat stats |
| 涨停板 | /limit-up | Card layout, 今日/5/10/20日 + custom, historical stats |
| 龙虎榜 | /lhb | Daily detail, institution buy/sell, stock stats (Sina ✅) |

## Data Sources Status
| Source | Status | Used For |
|--------|--------|----------|
| Sina (新浪) | ✅ Primary | K-line, financials, 龙虎榜 |
| 同花顺 | ✅ | Boards |
| 东方财富 | ❌ Blocked | Limit-up实时 (fallback to local DB period endpoint) |

## Key Commands (Windows)
```bash
# Backend
cd backend && set PYTHONUTF8=1 && python -m uvicorn app.main:app --reload --port 8000
# Frontend
cd frontend && pnpm dev
# Sync data
cd backend && set PYTHONUTF8=1 && python scripts/sync_sina.py
cd backend && set PYTHONUTF8=1 && python scripts/sync_financials.py
# Export DB for transfer
mysqldump -h localhost -u admin -pZggDLAXkkHXFwQVM --no-create-info --single-transaction stock_data > stock_data_dump.sql
```

## Important Notes
- `python` not `python3` on Windows
- `PYTHONUTF8=1` needed for Chinese comments in source
- 北交所 (8xxxxx/4xxxxx/92xxxx) excluded, 323 stocks removed from DB
- Negative close prices from 前复权 handled correctly (slope uses abs avg price normalization)
- ST stocks filterable in trend/slope page
- `scripts/sync_sina.py` uses Sina, safe from IP blocks, supports resume
- `scripts/sync_financials.py` uses SafeSyncer (2s±0.5s delay, 30/batch, 25s pause)

## Docs
- API reference: docs/api/api-reference.md
- Setup guide: docs/dev-guide/setup.md
- New machine: docs/dev-guide/new-machine-setup.md
- P1 design: docs/database/p1-data-layer-design.md
- Architecture: docs/architecture.md
