from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

from src.ingestion.vnstock_client import fetch_price_history, normalize_price_history
from src.utils.helpers import get_default_symbols, load_config
from src.utils.postgres import connect, init_schema, upsert_price_daily


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Vietnam stock daily prices into Postgres.")
    parser.add_argument("--symbols", help="Comma-separated symbols, for example: VCB,FPT,HPG")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD")
    parser.add_argument("--interval", default="1D", help="Vnstock interval, default: 1D")
    parser.add_argument("--source", default="VCI", help="Vnstock upstream source, default: VCI")
    parser.add_argument("--config", default="config.yaml", help="Data source config path")
    parser.add_argument("--init-schema", action="store_true", help="Create Postgres schema before ingest")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and normalize data without inserting")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    symbols = _resolve_symbols(args.symbols, config)

    if not symbols:
        raise RuntimeError("No symbols provided. Use --symbols or set default_symbols in config.yaml.")

    if args.init_schema and not args.dry_run:
        init_schema()

    run_id = uuid.uuid4()
    started_at = datetime.now(timezone.utc)
    rows_inserted = 0
    errors: dict[str, str] = {}

    conn = None
    try:
        if not args.dry_run:
            conn = connect()
            _start_run(conn, run_id, started_at, args, symbols)

        for symbol in symbols:
            try:
                raw = fetch_price_history(
                    symbol=symbol,
                    start=args.start,
                    end=args.end,
                    interval=args.interval,
                    source=args.source,
                )
                rows = normalize_price_history(raw, symbol=symbol, source=args.source)
                rows = _filter_date_range(rows, args.start, args.end)
                if args.dry_run:
                    print(f"{symbol}: fetched={len(raw)} normalized={len(rows)}")
                else:
                    rows_inserted += upsert_price_daily(conn, rows)
                    print(f"{symbol}: upserted={len(rows)}")
            except Exception as exc:
                errors[symbol] = str(exc)
                print(f"{symbol}: error={exc}", file=sys.stderr)

        if conn:
            status = "success" if not errors else "partial_success"
            _finish_run(conn, run_id, status, rows_inserted, errors)
            conn.commit()

        print(
            json.dumps(
                {
                    "run_id": str(run_id),
                    "symbols": symbols,
                    "rows_inserted": rows_inserted,
                    "errors": errors,
                    "dry_run": args.dry_run,
                },
                ensure_ascii=False,
            )
        )
        return 0 if not errors else 2
    except Exception as exc:
        if conn:
            _finish_run(conn, run_id, "failed", rows_inserted, {"fatal": str(exc)})
            conn.commit()
        raise
    finally:
        if conn:
            conn.close()


def _resolve_symbols(symbols_arg: str | None, config: dict) -> list[str]:
    if symbols_arg:
        return [symbol.strip().upper() for symbol in symbols_arg.split(",") if symbol.strip()]
    return get_default_symbols(config, "vnstock_market")


def _default_start() -> str:
    return (date.today() - timedelta(days=365 * 3)).isoformat()


def _filter_date_range(rows: list[dict], start: str, end: str) -> list[dict]:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    return [row for row in rows if start_date <= row["trade_date"] <= end_date]


def _start_run(conn, run_id: uuid.UUID, started_at: datetime, args: argparse.Namespace, symbols: list[str]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO market_data.ingestion_runs (
                run_id, source, job_name, status, started_at, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                run_id,
                "vnstock",
                "ingest_vn_prices",
                "running",
                started_at,
                json.dumps(
                    {
                        "symbols": symbols,
                        "start": args.start,
                        "end": args.end,
                        "interval": args.interval,
                        "source": args.source,
                    }
                ),
            ),
        )


def _finish_run(conn, run_id: uuid.UUID, status: str, rows_inserted: int, errors: dict[str, str]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE market_data.ingestion_runs
            SET status = %s,
                finished_at = NOW(),
                rows_inserted = %s,
                error_message = %s
            WHERE run_id = %s
            """,
            (
                status,
                rows_inserted,
                json.dumps(errors, ensure_ascii=False) if errors else None,
                run_id,
            ),
        )


if __name__ == "__main__":
    raise SystemExit(main())
