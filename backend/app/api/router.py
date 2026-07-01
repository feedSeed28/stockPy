"""API router aggregation."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.stocks import router as stocks_router
from app.api.v1.boards import router as boards_router
from app.api.v1.quant import router as quant_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(stocks_router, tags=["stocks"])
api_router.include_router(boards_router, tags=["boards"])
api_router.include_router(quant_router, tags=["quant"])
