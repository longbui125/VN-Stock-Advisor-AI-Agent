from __future__ import annotations

from datetime import date

import pandas as pd


def fetch_price_history(
    symbol: str,
    start: date | str,
    end: date | str,
    interval: str = "1D",
    source: str = "VCI",
) -> pd.DataFrame:
    """Fetch Vietnam stock price history through Vnstock."""

    symbol = symbol.upper()
    errors = []

    try:
        from vnstock import Quote

        quote = Quote(source=source.lower(), symbol=symbol)
        return quote.history(symbol=symbol, start=str(start), end=str(end), interval=interval)
    except Exception as exc:
        errors.append(f"Quote API error: {exc}")

    try:
        from vnstock import Vnstock

        stock = Vnstock().stock(symbol=symbol, source=source.upper())
        return stock.quote.history(start=str(start), end=str(end), interval=interval)
    except Exception as exc:
        errors.append(f"Unified API error: {exc}")

    raise RuntimeError("Could not fetch price history from Vnstock. " + "; ".join(errors))


def normalize_price_history(df: pd.DataFrame, symbol: str, source: str) -> list[dict]:
    if df is None or df.empty:
        return []

    normalized = df.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]

    aliases = {
        "trade_date": ["trade_date", "trading_date", "date", "time", "timestamp"],
        "open_price": ["open", "open_price", "openprice"],
        "high_price": ["high", "high_price", "highprice"],
        "low_price": ["low", "low_price", "lowprice"],
        "close_price": ["close", "close_price", "closeprice"],
        "adjusted_close_price": ["adjusted_close", "adjusted_close_price", "close_adj", "adj_close"],
        "volume": ["volume", "match_volume", "total_volume"],
        "value": ["value", "match_value", "total_value"],
    }

    selected: dict[str, str] = {}
    for canonical, candidates in aliases.items():
        for candidate in candidates:
            if candidate in normalized.columns:
                selected[canonical] = candidate
                break

    required = ["trade_date", "open_price", "high_price", "low_price", "close_price"]
    missing = [column for column in required if column not in selected]
    if missing:
        raise ValueError(
            f"Vnstock response is missing required columns {missing}. "
            f"Available columns: {list(normalized.columns)}"
        )

    trade_dates = pd.to_datetime(normalized[selected["trade_date"]], errors="coerce").dt.date
    rows: list[dict] = []

    for position, (_, row) in enumerate(normalized.iterrows()):
        trade_date = trade_dates.iloc[position]
        if pd.isna(trade_date):
            continue

        rows.append(
            {
                "symbol": symbol.upper(),
                "trade_date": trade_date,
                "open_price": _number_or_none(row.get(selected["open_price"])),
                "high_price": _number_or_none(row.get(selected["high_price"])),
                "low_price": _number_or_none(row.get(selected["low_price"])),
                "close_price": _number_or_none(row.get(selected["close_price"])),
                "adjusted_close_price": _number_or_none(
                    row.get(selected.get("adjusted_close_price"))
                    if selected.get("adjusted_close_price")
                    else None
                ),
                "volume": _int_or_none(row.get(selected.get("volume")) if selected.get("volume") else None),
                "value": _number_or_none(row.get(selected.get("value")) if selected.get("value") else None),
                "source": source.lower(),
            }
        )

    return rows


def _number_or_none(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    return float(value)


def _int_or_none(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    return int(float(value))
