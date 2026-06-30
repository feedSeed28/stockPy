"""Data sync status tracking model."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SyncStatus(Base):
    """数据同步状态追踪."""

    __tablename__ = "sync_status"

    table_name: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="表名",
    )
    last_sync_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最近同步完成时间"
    )
    last_data_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="最新数据日期"
    )
    row_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="当前同步行数"
    )
    status: Mapped[str] = mapped_column(
        Enum("idle", "syncing", "error", name="sync_status_enum"),
        default="idle",
        comment="同步状态",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="状态更新时间",
    )
