"""Board API endpoints — /api/v1/boards/*."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.services import stock_query_service as qs

router = APIRouter(prefix="/boards", tags=["boards"])


@router.get("")
async def list_boards(
    board_type: str | None = Query(None, description="industry / concept"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """行业/概念板块列表."""
    items, total = await qs.list_boards(db, board_type=board_type, page=page, page_size=page_size)
    return ApiResponse(data={
        "items": [
            {"id": b.id, "board_code": b.board_code, "board_name": b.board_name,
             "board_type": b.board_type, "source": b.source}
            for b in items
        ],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/{board_id}/members")
async def get_board_members(
    board_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """板块成分股."""
    items, total = await qs.get_board_members(db, board_id, page=page, page_size=page_size)
    return ApiResponse(data={
        "items": items,
        "total": total, "page": page, "page_size": page_size,
    })
