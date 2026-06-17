from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.utils.helpers import SCHEMA_PATH, get_env


def get_postgres_uri(env_name: str = "POSTGRES_URI") -> str:
    uri = get_env(env_name)
    if not uri:
        raise RuntimeError(
            f"Missing {env_name}. Example: postgresql://stocks:stocks@localhost:5432/stocks"
        )
    return uri


def connect(postgres_uri: str | None = None):
    import psycopg

    return psycopg.connect(postgres_uri or get_postgres_uri())


def init_schema(postgres_uri: str | None = None, schema_path: str | Path = SCHEMA_PATH) -> None:
    sql = Path(schema_path).read_text(encoding="utf-8")
    with connect(postgres_uri) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def upsert_price_daily(conn, rows: Iterable[dict]) -> int:
    records = list(rows)
    if not records:
        return 0

    sql = """
        INSERT INTO market_data.price_daily (
            symbol,
            trade_date,
            open_price,
            high_price,
            low_price,
            close_price,
            adjusted_close_price,
            volume,
            value,
            source
        )
        VALUES (
            %(symbol)s,
            %(trade_date)s,
            %(open_price)s,
            %(high_price)s,
            %(low_price)s,
            %(close_price)s,
            %(adjusted_close_price)s,
            %(volume)s,
            %(value)s,
            %(source)s
        )
        ON CONFLICT (symbol, trade_date, source) DO UPDATE SET
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            adjusted_close_price = EXCLUDED.adjusted_close_price,
            volume = EXCLUDED.volume,
            value = EXCLUDED.value,
            ingested_at = NOW()
    """

    with conn.cursor() as cur:
        cur.executemany(sql, records)
    return len(records)


def upsert_company(conn, company: dict) -> None:
    sql = """
        INSERT INTO market_data.companies (
            symbol,
            company_name,
            exchange,
            industry,
            icb_code,
            source
        )
        VALUES (
            %(symbol)s,
            %(company_name)s,
            %(exchange)s,
            %(industry)s,
            %(icb_code)s,
            %(source)s
        )
        ON CONFLICT (symbol) DO UPDATE SET
            company_name = EXCLUDED.company_name,
            exchange = EXCLUDED.exchange,
            industry = EXCLUDED.industry,
            icb_code = EXCLUDED.icb_code,
            source = EXCLUDED.source,
            updated_at = NOW()
    """

    with conn.cursor() as cur:
        cur.execute(sql, company)


def upsert_text_document(conn, document: dict) -> None:
    sql = """
        INSERT INTO market_data.text_documents (
            document_id,
            symbol,
            source,
            document_type,
            title,
            published_at,
            url,
            storage_path,
            content_hash
        )
        VALUES (
            %(document_id)s,
            %(symbol)s,
            %(source)s,
            %(document_type)s,
            %(title)s,
            %(published_at)s,
            %(url)s,
            %(storage_path)s,
            %(content_hash)s
        )
        ON CONFLICT (document_id) DO UPDATE SET
            symbol = EXCLUDED.symbol,
            source = EXCLUDED.source,
            document_type = EXCLUDED.document_type,
            title = EXCLUDED.title,
            published_at = EXCLUDED.published_at,
            url = EXCLUDED.url,
            storage_path = EXCLUDED.storage_path,
            content_hash = EXCLUDED.content_hash,
            ingested_at = NOW()
    """

    payload = {
        key: value
        for key, value in document.items()
        if key
        in {
            "document_id",
            "symbol",
            "source",
            "document_type",
            "title",
            "published_at",
            "url",
            "storage_path",
            "content_hash",
        }
    }

    with conn.cursor() as cur:
        cur.execute(sql, payload)
