"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.tasks import sync_tasks

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup: register scheduled jobs
    _setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started with jobs: %s", [j.id for j in scheduler.get_jobs()])
    yield
    # Shutdown: dispose engine pool and stop scheduler
    scheduler.shutdown(wait=False)
    await engine.dispose()


def _setup_scheduler():
    """Register APScheduler jobs.

    All times in Asia/Shanghai (Beijing time).
    - 16:00: daily K-line + fund flow incremental (market close)
    - 18:00: stock list + performance report check
    - Monday 16:30: weekly K-line
    - 1st of month 16:30: monthly K-line
    """
    # Daily: after market close
    scheduler.add_job(
        sync_tasks.sync_daily_kline_incremental,
        "cron",
        hour=16,
        minute=0,
        id="daily_kline",
    )
    scheduler.add_job(
        sync_tasks.sync_fund_flow_daily,
        "cron",
        hour=16,
        minute=5,
        id="fund_flow_daily",
    )

    # Weekly: Monday after close
    scheduler.add_job(
        sync_tasks.sync_weekly_kline,
        "cron",
        day_of_week="mon",
        hour=16,
        minute=30,
        id="weekly_kline",
    )

    # Monthly: 1st of month
    scheduler.add_job(
        sync_tasks.sync_monthly_kline,
        "cron",
        day="1",
        hour=16,
        minute=30,
        id="monthly_kline",
    )

    # Stock list + performance check (less frequent)
    scheduler.add_job(
        sync_tasks.sync_stock_list_weekly,
        "cron",
        day_of_week="sat",
        hour=9,
        minute=0,
        id="stock_list_weekly",
    )
    scheduler.add_job(
        sync_tasks.sync_performance_reports,
        "cron",
        hour=18,
        minute=0,
        id="performance_reports",
    )


app = FastAPI(
    title="Stock Quant System",
    description="股票量化系统 API -- A股数据",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(api_router, prefix=settings.api_v1_prefix)
