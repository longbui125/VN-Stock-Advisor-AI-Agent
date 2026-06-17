from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from src.chunking.chunker import chunk_text
from src.utils.helpers import get_default_symbols, get_env, load_config
from src.utils.postgres import connect, init_schema, upsert_company, upsert_text_document
from src.vectordb.vector_store import delete_collection, upsert_text_chunks


TEXT_COLUMNS = [
    "business_model",
    "history",
    "company_type",
    "address",
    "branches",
    "website",
    "auditor",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Vietnam company text profiles into Qdrant.")
    parser.add_argument("--symbols", help="Comma-separated symbols, for example: VCB,FPT,HPG")
    parser.add_argument("--config", default="config.yaml", help="Data source config path")
    parser.add_argument("--source", default="KBS", help="Vnstock company source, default: KBS")
    parser.add_argument(
        "--collection",
        default=get_env("QDRANT_COLLECTION", "vn_stock_text_chunks"),
        help="Qdrant collection name",
    )
    parser.add_argument("--recreate-collection", action="store_true", help="Delete and recreate Qdrant collection first")
    parser.add_argument(
        "--include-related",
        action="store_true",
        help="Also ingest officers, shareholders, subsidiaries, affiliates, and recent news. This uses more API calls.",
    )
    parser.add_argument("--init-schema", action="store_true", help="Create Postgres schema before ingest")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and build documents without writing")
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
    docs_written = 0
    chunks_written = 0
    errors: dict[str, str] = {}

    conn = None
    try:
        if not args.dry_run:
            conn = connect()
            _start_run(conn, run_id, started_at, args, symbols)
            if args.recreate_collection:
                delete_collection(collection_name=args.collection)

        for symbol in symbols:
            try:
                docs, company = fetch_company_documents(
                    symbol=symbol,
                    source=args.source,
                    include_related=args.include_related,
                )
                chunks = []
                for doc in docs:
                    chunks.extend(chunk_text(doc["text"], _chunk_metadata(doc)))

                if args.dry_run:
                    print(f"{symbol}: documents={len(docs)} chunks={len(chunks)}")
                    continue

                if company:
                    upsert_company(conn, company)

                for doc in docs:
                    upsert_text_document(conn, doc)

                docs_written += len(docs)
                chunks_written += upsert_text_chunks(chunks, collection_name=args.collection)
                print(f"{symbol}: documents={len(docs)} chunks={len(chunks)}")
            except Exception as exc:
                errors[symbol] = str(exc)
                print(f"{symbol}: error={exc}", file=sys.stderr)

        if conn:
            status = "success" if not errors else "partial_success"
            _finish_run(conn, run_id, status, docs_written, chunks_written, errors)
            conn.commit()

        print(
            json.dumps(
                {
                    "run_id": str(run_id),
                    "symbols": symbols,
                    "documents_written": docs_written,
                    "chunks_written": chunks_written,
                    "errors": errors,
                    "dry_run": args.dry_run,
                },
                ensure_ascii=False,
            )
        )
        return 0 if not errors else 2
    except Exception as exc:
        if conn:
            _finish_run(conn, run_id, "failed", docs_written, chunks_written, {"fatal": str(exc)})
            conn.commit()
        raise
    finally:
        if conn:
            conn.close()


def fetch_company_documents(
    symbol: str,
    source: str = "KBS",
    include_related: bool = False,
) -> tuple[list[dict], dict | None]:
    from vnstock import Company

    symbol = symbol.upper()
    company_api = Company(symbol=symbol, source=source.upper())
    overview = company_api.overview()
    overview_row = _first_row(overview)

    if not overview_row:
        return [], None

    company = _company_from_overview(overview_row, symbol=symbol, source=f"vnstock_{source.lower()}")
    docs: list[dict] = []

    profile_text = _overview_to_text(overview_row, symbol)
    if profile_text.strip():
        docs.append(
            _document(
                symbol=symbol,
                source=f"vnstock_{source.lower()}",
                document_type="company_profile",
                title=f"{symbol} company profile",
                text=profile_text,
                url=str(overview_row.get("website") or ""),
                published_at=str(overview_row.get("as_of_date") or ""),
            )
        )

    if not include_related:
        return docs, company

    for method_name, document_type, title_suffix in [
        ("officers", "company_officers", "officers"),
        ("shareholders", "shareholders", "major shareholders"),
        ("subsidiaries", "subsidiaries", "subsidiaries"),
        ("affiliate", "affiliates", "affiliates"),
        ("news", "company_news", "recent company news"),
    ]:
        if not hasattr(company_api, method_name):
            continue
        try:
            df = getattr(company_api, method_name)()
            text = _dataframe_to_text(df)
            if text.strip():
                docs.append(
                    _document(
                        symbol=symbol,
                        source=f"vnstock_{source.lower()}",
                        document_type=document_type,
                        title=f"{symbol} {title_suffix}",
                        text=text,
                        url=str(overview_row.get("website") or ""),
                        published_at=str(overview_row.get("as_of_date") or ""),
                    )
                )
        except Exception:
            continue

    return docs, company


def _resolve_symbols(symbols_arg: str | None, config: dict) -> list[str]:
    if symbols_arg:
        return [symbol.strip().upper() for symbol in symbols_arg.split(",") if symbol.strip()]
    return get_default_symbols(config, "vnstock_company_text")


def _first_row(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {}
    return df.iloc[0].to_dict()


def _company_from_overview(row: dict[str, Any], symbol: str, source: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "company_name": _clean(row.get("company_name") or row.get("short_name") or symbol),
        "exchange": _clean(row.get("exchange")),
        "industry": _clean(row.get("industry") or row.get("industry_name")),
        "icb_code": _clean(row.get("icb_code")),
        "source": source,
    }


def _overview_to_text(row: dict[str, Any], symbol: str) -> str:
    lines = [f"Ma co phieu: {symbol}"]
    for column in TEXT_COLUMNS:
        value = _clean(row.get(column))
        if value:
            lines.append(f"{column}: {value}")

    for column in [
        "exchange",
        "founded_date",
        "listing_date",
        "ceo_name",
        "ceo_position",
        "number_of_employees",
        "charter_capital",
        "outstanding_shares",
        "as_of_date",
    ]:
        value = _clean(row.get(column))
        if value:
            lines.append(f"{column}: {value}")
    return "\n".join(lines)


def _dataframe_to_text(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return ""

    rows = []
    for record in df.fillna("").to_dict("records"):
        parts = []
        for key, value in record.items():
            clean_value = _clean(value)
            if clean_value:
                parts.append(f"{key}: {clean_value}")
        if parts:
            rows.append("; ".join(parts))
    return "\n".join(rows)


def _document(
    symbol: str,
    source: str,
    document_type: str,
    title: str,
    text: str,
    url: str = "",
    published_at: str = "",
) -> dict[str, Any]:
    content_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()
    document_id = f"{source}:{symbol}:{document_type}:{content_hash[:12]}"
    return {
        "document_id": document_id,
        "symbol": symbol,
        "source": source,
        "document_type": document_type,
        "title": title,
        "published_at": _published_at_or_none(published_at),
        "url": url,
        "storage_path": "",
        "content_hash": content_hash,
        "text": text,
    }


def _chunk_metadata(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": doc["document_id"],
        "symbol": doc["symbol"],
        "source": doc["source"],
        "document_type": doc["document_type"],
        "title": doc["title"],
        "published_at": doc["published_at"] or "",
        "url": doc["url"] or "",
        "content_hash": doc["content_hash"],
    }


def _published_at_or_none(value: str) -> str | None:
    value = _clean(value)
    if not value:
        return None
    return value


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return " ".join(str(value).split())


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
                "vnstock_text",
                "ingest_vn_texts",
                "running",
                started_at,
                json.dumps(
                    {
                        "symbols": symbols,
                        "source": args.source,
                        "collection": args.collection,
                        "include_related": args.include_related,
                        "recreate_collection": args.recreate_collection,
                    }
                ),
            ),
        )


def _finish_run(
    conn,
    run_id: uuid.UUID,
    status: str,
    docs_written: int,
    chunks_written: int,
    errors: dict[str, str],
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE market_data.ingestion_runs
            SET status = %s,
                finished_at = NOW(),
                rows_inserted = %s,
                error_message = %s,
                metadata = metadata || %s::jsonb
            WHERE run_id = %s
            """,
            (
                status,
                docs_written,
                json.dumps(errors, ensure_ascii=False) if errors else None,
                json.dumps({"chunks_written": chunks_written}),
                run_id,
            ),
        )


if __name__ == "__main__":
    raise SystemExit(main())
