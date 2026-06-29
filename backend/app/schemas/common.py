"""Unified API response schema."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper.

    All endpoints return this shape:
        { "code": 200, "message": "ok", "data": ... }
    """

    code: int = 200
    message: str = "ok"
    data: T | None = None
