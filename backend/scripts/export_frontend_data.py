"""Export frontend-readable static JSON data from MySQL.

Default export is intentionally small:
  - stocks.json
  - market.latest.json
  - boards.json
  - manifest.json

K-line export is opt-in because full-market JSON can be large:
  python scripts/export_frontend_data.py --symbols 000001,600000
  python scripts/export_frontend_data.py --all-kline --kline-limit 500
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "frontend" / "public" / "data"

KLINE_TABLES = {
    "daily": "stock_daily_quote",
    "weekly": "stock_weekly_quote",
    "monthly": "stock_monthly_quote",
}


def _json_default(value: Any):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _write_json(path: Path, payload: Any) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"), default=_json_default)
    return path.stat().st_size


def _db_config() -> dict[str, Any]:
    load_dotenv(BACKEND_DIR / ".env")
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "admin"),
        "password": os.getenv("MYSQL_PASSWORD", "ZggDLAXkkHXFwQVM"),
        "database": os.getenv("MYSQL_DATABASE", "stock_data"),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
    }


def _connect():
    return pymysql.connect(**_db_config())


def _fetch_all(conn, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def export_stocks(conn, output_dir: Path) -> dict[str, Any]:
    rows = _fetch_all(
        conn,
        """
        SELECT code, name, exchange, board_type, industry, is_active, listed_date
        FROM stock_info
        ORDER BY code
        """,
    )
    size = _write_json(output_dir / "stocks.json", {"items": rows, "total": len(rows)})
    return {"file": "stocks.json", "rows": len(rows), "bytes": size}


def export_market_latest(conn, output_dir: Path) -> dict[str, Any]:
    latest = _fetch_all(
        conn,
        """
        SELECT MAX(trade_date) AS trade_date
        FROM stock_daily_quote
        WHERE adjust_type = 'qfq'
        """,
    )[0]["trade_date"]
    if latest is None:
        size = _write_json(output_dir / "market.latest.json", {"date": None, "items": [], "total": 0})
        return {"file": "market.latest.json", "rows": 0, "bytes": size}

    rows = _fetch_all(
        conn,
        """
        SELECT q.stock_code AS code, i.name, i.industry,
               q.open, q.close, q.high, q.low, q.volume, q.amount,
               q.change_pct, q.change_amount, q.turnover_rate, q.amplitude
        FROM stock_daily_quote q
        LEFT JOIN stock_info i ON q.stock_code = i.code
        WHERE q.trade_date = %s AND q.adjust_type = 'qfq'
        ORDER BY q.change_pct DESC
        """,
        (latest,),
    )
    up = sum(1 for r in rows if (r.get("change_pct") or 0) > 0)
    down = sum(1 for r in rows if (r.get("change_pct") or 0) < 0)
    payload = {
        "date": latest,
        "items": rows,
        "total": len(rows),
        "stats": {"up": up, "down": down, "flat": len(rows) - up - down},
    }
    size = _write_json(output_dir / "market.latest.json", payload)
    return {"file": "market.latest.json", "rows": len(rows), "bytes": size}


def export_boards(conn, output_dir: Path, include_members: bool = True) -> dict[str, Any]:
    boards = _fetch_all(
        conn,
        """
        SELECT id, board_code, board_name, board_type, source
        FROM stock_board_info
        ORDER BY board_type, board_name
        """,
    )
    board_size = _write_json(output_dir / "boards.json", {"items": boards, "total": len(boards)})
    member_files = 0
    member_rows = 0

    if include_members:
        for board in boards:
            members = _fetch_all(
                conn,
                """
                SELECT m.stock_code, i.name AS stock_name
                FROM stock_board_member m
                LEFT JOIN stock_info i ON m.stock_code = i.code
                WHERE m.board_id = %s
                ORDER BY m.stock_code
                """,
                (board["id"],),
            )
            if not members:
                continue
            filename = f"{board['board_code']}.json"
            _write_json(
                output_dir / "board-members" / filename,
                {"board_code": board["board_code"], "items": members, "total": len(members)},
            )
            member_files += 1
            member_rows += len(members)

    return {
        "file": "boards.json",
        "rows": len(boards),
        "bytes": board_size,
        "member_files": member_files,
        "member_rows": member_rows,
    }


def resolve_symbols(conn, symbols: str | None, all_kline: bool) -> list[str]:
    if all_kline:
        rows = _fetch_all(
            conn,
            "SELECT code FROM stock_info WHERE is_active = 1 ORDER BY code",
        )
        return [r["code"] for r in rows]
    if not symbols:
        return []
    return [s.strip().zfill(6) for s in symbols.split(",") if s.strip()]


def export_kline(
    conn,
    output_dir: Path,
    symbols: list[str],
    periods: list[str],
    limit: int,
) -> dict[str, Any]:
    result = {"symbols": len(symbols), "files": 0, "rows": 0}
    if not symbols:
        return result

    for period in periods:
        table = KLINE_TABLES[period]
        for code in symbols:
            rows = _fetch_all(
                conn,
                f"""
                SELECT trade_date, open, close, high, low, volume, amount,
                       amplitude, change_pct, change_amount, turnover_rate
                FROM {table}
                WHERE stock_code = %s AND adjust_type = 'qfq'
                ORDER BY trade_date DESC
                LIMIT %s
                """,
                (code, limit),
            )
            rows = list(reversed(rows))
            if not rows:
                continue
            _write_json(
                output_dir / "kline" / period / f"{code}.json",
                {"code": code, "period": period, "items": rows, "total": len(rows)},
            )
            result["files"] += 1
            result["rows"] += len(rows)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export static JSON data for standalone frontend use.")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT_DIR), help="Output directory, default: frontend/public/data")
    parser.add_argument("--symbols", help="Comma-separated stock codes for K-line export, e.g. 000001,600000")
    parser.add_argument("--all-kline", action="store_true", help="Export K-line files for all active stocks")
    parser.add_argument("--kline-limit", type=int, default=500, help="Max bars per symbol/period")
    parser.add_argument("--periods", default="daily", help="Comma-separated periods: daily,weekly,monthly")
    parser.add_argument("--no-board-members", action="store_true", help="Skip board member JSON files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.out).resolve()
    periods = [p.strip() for p in args.periods.split(",") if p.strip()]
    unknown = [p for p in periods if p not in KLINE_TABLES]
    if unknown:
        raise SystemExit(f"Unsupported periods: {unknown}. Use daily, weekly, monthly.")

    started_at = datetime.now()
    manifest: dict[str, Any] = {
        "generated_at": started_at.isoformat(timespec="seconds"),
        "output_dir": str(output_dir),
        "exports": {},
    }

    with _connect() as conn:
        manifest["exports"]["stocks"] = export_stocks(conn, output_dir)
        manifest["exports"]["market"] = export_market_latest(conn, output_dir)
        manifest["exports"]["boards"] = export_boards(
            conn,
            output_dir,
            include_members=not args.no_board_members,
        )
        symbols = resolve_symbols(conn, args.symbols, args.all_kline)
        manifest["exports"]["kline"] = export_kline(
            conn,
            output_dir,
            symbols=symbols,
            periods=periods,
            limit=args.kline_limit,
        )

    manifest["duration_seconds"] = round((datetime.now() - started_at).total_seconds(), 2)
    _write_json(output_dir / "manifest.json", manifest)

    print(f"Export complete: {output_dir}")
    for name, info in manifest["exports"].items():
        print(f"  {name}: {info}")


if __name__ == "__main__":
    main()
