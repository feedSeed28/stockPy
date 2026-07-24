# Stock Quant System — Makefile
#
# Usage:
#   Linux/Mac:   make dev-backend          (uses python3 by default)
#   Windows:     make dev-backend PYTHON=python
#
# PYTHON — override if your system uses "python" instead of "python3"
PYTHON := python3

.PHONY: install setup dev-backend dev-frontend \
        db-migrate db-revision db-downgrade db-reset \
        db-export db-import db-export-schema db-import-data \
        export-frontend-data \
        backfill-industry \
        sync-full sync-stocks sync-daily sync-financials sync-status \
        run-backtest \
        test lint help

# ═══════════════════════════════════════════════════════════════════════════
# Setup
# ═══════════════════════════════════════════════════════════════════════════

install:
	cd backend && pip install -r requirements.txt
	cd frontend && pnpm install

setup: install
	@echo "=== Step 1: Copy .env ==="
	@test -f backend/.env || cp backend/.env.example backend/.env
	@echo ".env ready (edit if needed)"
	@echo ""
	@echo "=== Step 2: Start MySQL ==="
	@echo "Option A (Docker): docker-compose up -d mysql"
	@echo "Option B (Native): ensure MySQL 8 is running on localhost:3306"
	@echo ""
	@echo "=== Step 3: Run migrations ==="
	cd backend && alembic upgrade head
	@echo ""
	@echo "=== Step 4: Start backend ==="
	@echo "make dev-backend"
	@echo ""
	@echo "=== Step 5 (optional): Sync data ==="
	@echo "make sync-full"

# ═══════════════════════════════════════════════════════════════════════════
# Development
# ═══════════════════════════════════════════════════════════════════════════

dev-backend:
	cd backend && PYTHONUTF8=1 uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && pnpm dev

# ═══════════════════════════════════════════════════════════════════════════
# Database
# ═══════════════════════════════════════════════════════════════════════════

db-migrate:
	cd backend && alembic upgrade head

db-revision:
	cd backend && alembic revision --autogenerate -m "$(msg)"

db-downgrade:
	cd backend && alembic downgrade -1

db-reset:
	cd backend && alembic downgrade base && alembic upgrade head

# ── Data Export / Import (for moving between machines) ──────────────

DB_USER ?= admin
DB_PASS ?= ZggDLAXkkHXFwQVM
DB_NAME ?= stock_data
DB_HOST ?= localhost
DB_PORT ?= 3306

MYSQL_CMD = mysql -h $(DB_HOST) -P $(DB_PORT) -u $(DB_USER) -p$(DB_PASS) $(DB_NAME)
MYSQLDUMP_CMD = mysqldump -h $(DB_HOST) -P $(DB_PORT) -u $(DB_USER) -p$(DB_PASS) $(DB_NAME)

db-export:
	@echo "Exporting full database to stock_data_backup.sql ..."
	$(MYSQLDUMP_CMD) --single-transaction --routines --triggers > stock_data_backup.sql
	@echo "Done: stock_data_backup.sql"

db-export-schema:
	@echo "Exporting schema only to stock_data_schema.sql ..."
	$(MYSQLDUMP_CMD) --no-data --single-transaction > stock_data_schema.sql
	@echo "Done: stock_data_schema.sql"

db-export-data:
	@echo "Exporting data only to stock_data_only.sql ..."
	$(MYSQLDUMP_CMD) --no-create-info --single-transaction > stock_data_only.sql
	@echo "Done: stock_data_only.sql"

db-import:
	@echo "Importing from stock_data_backup.sql ..."
	$(MYSQL_CMD) < stock_data_backup.sql
	@echo "Done."

db-import-data:
	@echo "Importing data only from stock_data_only.sql ..."
	$(MYSQL_CMD) < stock_data_only.sql
	@echo "Done."

# ── Frontend Static Data Export ───────────────────────────────────

export-frontend-data:
	cd backend && PYTHONUTF8=1 $(PYTHON) scripts/export_frontend_data.py

backfill-industry:
	cd backend && PYTHONUTF8=1 $(PYTHON) scripts/backfill_stock_industry.py

# ── Data Sync ──────────────────────────────────────────────────────

sync-full:
	cd backend && PYTHONUTF8=1 $(PYTHON) scripts/sync_full.py

sync-stocks:
	cd backend && PYTHONUTF8=1 $(PYTHON) scripts/sync_stocks.py

sync-daily:
	cd backend && PYTHONUTF8=1 $(PYTHON) scripts/sync_daily.py

sync-financials:
	cd backend && PYTHONUTF8=1 $(PYTHON) scripts/sync_financials.py

sync-status:
	cd backend && PYTHONUTF8=1 $(PYTHON) -c "\
from app.core.database import async_session; \
from sqlalchemy import select; \
from app.models.sync_status import SyncStatus; \
import asyncio; \
async def main(): \
    async with async_session() as db: \
        result = await db.execute(select(SyncStatus)); \
        for r in result.scalars().all(): \
            print(f'{r.table_name:30s} | {str(r.status):8s} | {str(r.last_data_date):12s} | {r.row_count:>10,} rows'); \
asyncio.run(main())"

# ── Quant Research ───────────────────────────────────────────────

run-backtest:
	cd backend && PYTHONUTF8=1 $(PYTHON) scripts/run_backtest.py $(ARGS)

# ═══════════════════════════════════════════════════════════════════════════
# Test & Lint
# ═══════════════════════════════════════════════════════════════════════════

test:
	cd backend && pytest -v

lint:
	cd backend && ruff check .
	cd frontend && pnpm lint

# ═══════════════════════════════════════════════════════════════════════════
# Help
# ═══════════════════════════════════════════════════════════════════════════

help:
	@echo "Stock Quant System — Makefile targets"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies"
	@echo "  make setup            First-time project setup"
	@echo ""
	@echo "Development:"
	@echo "  make dev-backend       Start FastAPI server (port 8000)"
	@echo "  make dev-frontend      Start React dev server (port 8001)"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate        Apply Alembic migrations"
	@echo "  make db-revision msg=X Create new migration"
	@echo "  make db-reset          Drop all tables and recreate"
	@echo ""
	@echo "Data Transfer (between machines):"
	@echo "  make db-export          Export full DB → stock_data_backup.sql"
	@echo "  make db-export-schema   Export schema only (no data)"
	@echo "  make db-export-data     Export data only (no CREATE TABLE)"
	@echo "  make db-import          Import full DB from stock_data_backup.sql"
	@echo "  make db-import-data     Import data only from stock_data_only.sql"
	@echo "  make export-frontend-data Export static JSON for standalone frontend"
	@echo "  make backfill-industry  Fill stock_info.industry from performance reports"
	@echo ""
	@echo "Data Sync:"
	@echo "  make sync-full          Full historical sync (~46 min)"
	@echo "  make sync-stocks        Stock list only"
	@echo "  make sync-daily         Daily incremental"
	@echo "  make sync-financials    Financial indicators with anti-blocking"
	@echo "  make sync-status        Show sync progress"
	@echo ""
	@echo "Quant Research:"
	@echo "  make run-backtest ARGS=\"--stock 000001 --strategy ma_cross\""
	@echo ""
	@echo "Windows users: add PYTHON=python"
	@echo "  e.g. make dev-backend PYTHON=python"
