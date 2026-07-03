"""API router aggregation."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.stocks import router as stocks_router
from app.api.v1.boards import router as boards_router
from app.api.v1.quant import router as quant_router
from app.api.v1.limit_up import router as limit_up_router
from app.api.v1.lhb import router as lhb_router
from app.api.v1.market import router as market_router
from app.api.v1.slope import router as slope_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(stocks_router, tags=["stocks"])
api_router.include_router(boards_router, tags=["boards"])
api_router.include_router(quant_router, tags=["quant"])
api_router.include_router(limit_up_router, tags=["limit-up"])
api_router.include_router(lhb_router, tags=["lhb"])
api_router.include_router(market_router, tags=["market"])
api_router.include_router(slope_router, tags=["slope"])
