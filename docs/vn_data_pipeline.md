# Vietnam Stock Data Pipeline

This repo is moving away from news data. Structured market and financial data goes
to Postgres. Company text profiles are chunked and embedded into Qdrant for RAG.

## Initial Sources

- Vnstock: prototype connector for OHLCV and company profile text.
- FiinGroup API Datafeed: production connector placeholder for paid exchange data.
- Vietstock DataFeed: production connector placeholder for financial statements,
  ratios, corporate data, and macro data.

## Environment

```powershell
$env:POSTGRES_URI="postgresql://stocks:stocks@localhost:5432/stocks"
$env:QDRANT_URL="http://localhost:6333"
```

## Start Local Services

```powershell
docker compose up -d
```

This starts Postgres, Qdrant, the schema init job, the price ingest job, the text
ingest job, Adminer, and the Streamlit app.

## Initialize Warehouse

```powershell
docker compose run --rm init-postgres
```

## Dry Run

```powershell
python -m src.ingestion.price_loader --symbols VCB,FPT,HPG --start 2023-01-01 --end 2026-06-09 --dry-run
```

## Real Insert

```powershell
docker compose run --rm ingest-prices
```

## RAG Text Ingest

```powershell
docker compose run --rm ingest-texts
```

This runs:

```text
src/ingestion/text_loader.py
```

The script fetches company profiles from Vnstock, stores document metadata in
Postgres, chunks text, embeds chunks with local hashing embeddings, and upserts
them into Qdrant collection `vn_stock_text_chunks`.

## Suggested Schedule

- Daily price data: once per trading day after market close.
- Financial statements and ratios: once or twice per day during reporting season.
- Exchange disclosures and company reports: every 4-8 hours; embed only newly
  detected text documents.

## Run App

```powershell
docker compose up -d app
```

Open:

```text
http://localhost:8501
```

## Monitor Data

Open Adminer:

```text
http://localhost:8080
```

Login:

```text
System: PostgreSQL
Server: postgres
Username: stocks
Password: stocks
Database: stocks
```

Useful tables:

- `market_data.price_daily`: daily OHLCV stock prices.
- `market_data.ingestion_runs`: status and row counts for each ingest run.
- `market_data.text_documents`: metadata for text documents embedded in Qdrant.

Adminer opens the `public` schema by default. The schema also contains shortcut
views such as `public.price_daily` and `public.ingestion_runs`, so you can inspect
data without switching schemas.

Qdrant collection:

```text
vn_stock_text_chunks
```

Useful checks:

```powershell
docker compose logs ingest-texts
docker compose logs ingest-prices
```
