"""A-stock board / sector models."""

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDMixin, TimestampMixin, Base


class StockBoardInfo(Base, UUIDMixin, TimestampMixin):
    """行业/概念板块信息."""

    __tablename__ = "stock_board_info"
    __table_args__ = (
        UniqueConstraint("board_name", "board_type", "source", name="uq_board"),
    )

    board_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="板块代码"
    )
    board_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="板块名称"
    )
    board_type: Mapped[str] = mapped_column(
        Enum("industry", "concept", name="board_type_enum"),
        nullable=False,
        comment="板块类型 industry=行业 concept=概念",
    )
    source: Mapped[str] = mapped_column(
        Enum("em", "ths", name="board_source_enum"),
        nullable=False,
        comment="数据源 em=东方财富 ths=同花顺",
    )


class StockBoardMember(Base, UUIDMixin, TimestampMixin):
    """板块成分股."""

    __tablename__ = "stock_board_member"
    __table_args__ = (
        UniqueConstraint("board_id", "stock_code", name="uq_board_stock"),
    )

    board_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="板块ID FK→stock_board_info.id"
    )
    stock_code: Mapped[str] = mapped_column(
        String(6), nullable=False, index=True, comment="股票代码"
    )
