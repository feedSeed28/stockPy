"""Health check endpoint."""

from fastapi import APIRouter

from app.schemas.common import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse)
async def health_check():
    """Application health check.

    Returns 200 when the service is running.
    Database connectivity check will be added in a later phase.
    """
    return ApiResponse(code=200, message="ok", data=None)
