# Development Environment Setup

## Prerequisites

- Python 3.12+
- Node.js 22+
- pnpm
- Docker (for MySQL) OR local MySQL 8

## Quick Start (First Time)

### 1. Clone & Install

```bash
git clone <repo-url> stock_py
cd stock_py

# Backend dependencies
cd backend
pip install -r requirements.txt

# Frontend dependencies
cd frontend
pnpm install
```

### 2. Environment Config

```bash
cd backend
cp .env.example .env
# Edit .env if your MySQL credentials differ from defaults
```

Default credentials (matching docker-compose + init.sql):
```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=ZggDLAXkkHXFwQVM
MYSQL_DATABASE=stock_data
```

### 3. Start MySQL

**Option A — Docker (recommended):**
```bash
docker-compose up -d mysql
```

**Option B — Local MySQL 8:**
```sql
CREATE DATABASE stock_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'admin'@'localhost' IDENTIFIED BY 'ZggDLAXkkHXFwQVM';
GRANT ALL PRIVILEGES ON stock_data.* TO 'admin'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Run Migrations

```bash
cd backend
alembic upgrade head
```

### 5. Start Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs — Swagger UI with all endpoints.

### 6. Start Frontend (optional)

```bash
cd frontend
pnpm dev
```

Visit http://localhost:8001

## Verify

```bash
# Health check
curl http://localhost:8000/api/v1/health
# → {"code":200, "message":"ok", "data":null}
```

## Data Sync

### Initial Full Sync (one-time, ~46 minutes)

```bash
# Start the backend first, then trigger full sync:
python -c "
import asyncio
from app.core.database import async_session
from app.services.stock_sync_service import StockSyncService

async def main():
    async with async_session() as db:
        svc = StockSyncService(db)
        result = await svc.full_sync()
        print(result)

asyncio.run(main())
"
```

### Incremental Sync (automatic)

The scheduler runs automatically when the backend is running:
- **Daily 16:00**: K-line + fund flow incremental
- **Monday 16:30**: Weekly K-line
- **1st of month 16:30**: Monthly K-line
- **Saturday 09:00**: Stock list check
- **Daily 18:00**: Performance report check

### Manual Sync (API)

```
GET /api/v1/health → check scheduler status
```

Check `sync_status` table for sync progress:
```sql
SELECT * FROM sync_status;
```

## After Reboot

```bash
# 1. Start MySQL
docker-compose up -d mysql     # Docker
# or: net start MySQL80         # Windows service

# 2. Start backend
cd backend && uvicorn app.main:app --reload --port 8000

# 3. Data is persistent — no re-sync needed
# Scheduler resumes automatically with the app
```

## Moving Between Computers

The code is on Git (clone → install → migrate → done).  
The data (~6 GB after sync) has two approaches:

### Option A: Export/Import (Fastest — recommended)

**On old machine:**
```bash
# Export data only (no schema)
make db-export-data
# → creates stock_data_only.sql

# Or export everything (schema + data)
make db-export
# → creates stock_data_backup.sql
```
Copy the `.sql` file to the new machine.

**On new machine:**
```bash
# Schema is created by migration
make db-migrate

# Import the data
make db-import-data
```

### Option B: Re-sync from AKShare (Slower — zero setup)

No data to copy. Just run on the new machine:
```bash
make sync-full
# Takes ~46 minutes, downloads ~6 GB from AKShare
```

### Comparison

| | Export/Import | Re-sync |
|---|---|---|
| Data transfer | ~2 GB .sql file | None |
| Time | ~10 min (export) + ~20 min (import) | ~46 min |
| AKShare rate limits | None | May hit limits on full sync |
| Freshness | Snapshot at export time | Up-to-the-minute |
| Effort | Copy one file | One command |

### Note for Windows Users

The Makefile uses `python3`. On Windows, use:
```bash
make sync-full PYTHON=python
```

## Database Reset

```bash
cd backend
alembic downgrade base   # Drop all tables
alembic upgrade head     # Recreate all tables
# Then re-run full sync
```

## Project File Map

```
backend/app/
├── models/
│   ├── base.py              # Base, UUIDMixin, TimestampMixin
│   ├── stock_info.py        # StockInfo
│   ├── stock_quote.py       # StockDailyQuote, Weekly, Monthly
│   ├── stock_financial.py   # StockPerformanceReport, StockFinancialIndicator
│   ├── stock_forecast.py    # StockProfitForecast
│   ├── stock_fund_flow.py   # StockFundFlowDaily
│   ├── stock_board.py       # StockBoardInfo, StockBoardMember
│   └── sync_status.py       # SyncStatus
├── services/
│   ├── stock_sync_service.py   # AKShare → MySQL sync
│   ├── stock_query_service.py  # Read queries for API
│   └── rate_limiter.py         # TokenBucket + retry decorators
├── api/v1/
│   ├── health.py            # Health check endpoint
│   ├── stocks.py            # /stocks/* endpoints (12 routes)
│   └── boards.py            # /boards/* endpoints (2 routes)
├── tasks/
│   └── sync_tasks.py        # APScheduler job definitions
└── main.py                  # FastAPI app + scheduler setup
```
