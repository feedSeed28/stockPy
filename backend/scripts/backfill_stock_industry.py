"""Backfill stock_info.industry from local performance report data.

Usage (from backend/):
    PYTHONUTF8=1 python scripts/backfill_stock_industry.py
    PYTHONUTF8=1 python scripts/backfill_stock_industry.py --overwrite

The default mode only fills empty stock_info.industry values. It does not call
external data sources.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill stock_info.industry from latest stock_performance_report rows."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing stock_info.industry values instead of filling blanks only.",
    )
    return parser.parse_args()


async def count_industry(conn) -> dict[str, int]:
    result = await conn.execute(text("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN industry IS NOT NULL AND industry <> '' THEN 1 ELSE 0 END) AS with_industry,
            SUM(CASE WHEN industry IS NULL OR industry = '' THEN 1 ELSE 0 END) AS without_industry
        FROM stock_info
    """))
    row = result.mappings().one()
    return {
        "total": int(row["total"] or 0),
        "with_industry": int(row["with_industry"] or 0),
        "without_industry": int(row["without_industry"] or 0),
    }


async def count_source(conn) -> int:
    result = await conn.execute(text("""
        SELECT COUNT(DISTINCT p.stock_code)
        FROM stock_performance_report p
        JOIN stock_info s ON s.code = p.stock_code
        WHERE p.industry IS NOT NULL AND p.industry <> ''
    """))
    return int(result.scalar() or 0)


async def backfill(overwrite: bool) -> None:
    where_clause = "" if overwrite else "WHERE s.industry IS NULL OR s.industry = ''"
    update_sql = f"""
        UPDATE stock_info s
        JOIN (
            SELECT stock_code, industry
            FROM (
                SELECT
                    p.stock_code,
                    p.industry,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.stock_code
                        ORDER BY p.report_date DESC, p.id DESC
                    ) AS rn
                FROM stock_performance_report p
                WHERE p.industry IS NOT NULL AND p.industry <> ''
            ) ranked
            WHERE rn = 1
        ) latest ON latest.stock_code = s.code
        SET s.industry = latest.industry
        {where_clause}
    """

    async with engine.begin() as conn:
        before = await count_industry(conn)
        source_count = await count_source(conn)
        result = await conn.execute(text(update_sql))
        after = await count_industry(conn)

    print("Industry backfill complete")
    print(f"Source stocks with industry: {source_count}")
    print(f"Rows changed: {result.rowcount}")
    print(f"Before: {before}")
    print(f"After:  {after}")


async def main() -> None:
    args = parse_args()
    await backfill(overwrite=args.overwrite)


if __name__ == "__main__":
    asyncio.run(main())
