CREATE SCHEMA IF NOT EXISTS market_data;

CREATE TABLE IF NOT EXISTS market_data.ingestion_runs (
    run_id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    job_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    rows_inserted INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE TABLE IF NOT EXISTS market_data.companies (
    symbol TEXT PRIMARY KEY,
    company_name TEXT,
    exchange TEXT,
    industry TEXT,
    icb_code TEXT,
    source TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_data.securities (
    symbol TEXT PRIMARY KEY,
    company_symbol TEXT REFERENCES market_data.companies(symbol),
    exchange TEXT,
    asset_type TEXT NOT NULL DEFAULT 'stock',
    status TEXT,
    listed_date DATE,
    source TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_data.price_daily (
    symbol TEXT NOT NULL,
    trade_date DATE NOT NULL,
    open_price NUMERIC(20, 4),
    high_price NUMERIC(20, 4),
    low_price NUMERIC(20, 4),
    close_price NUMERIC(20, 4),
    adjusted_close_price NUMERIC(20, 4),
    volume BIGINT,
    value NUMERIC(24, 4),
    source TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, trade_date, source)
);

CREATE INDEX IF NOT EXISTS idx_price_daily_symbol_date
    ON market_data.price_daily(symbol, trade_date DESC);

CREATE TABLE IF NOT EXISTS market_data.financial_statements (
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    quarter INTEGER,
    statement_type TEXT NOT NULL,
    metric_code TEXT NOT NULL,
    metric_name TEXT,
    value NUMERIC(28, 4),
    unit TEXT,
    source TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, period, statement_type, metric_code, source)
);

CREATE TABLE IF NOT EXISTS market_data.financial_ratios (
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    quarter INTEGER,
    ratio_code TEXT NOT NULL,
    ratio_name TEXT,
    value NUMERIC(28, 8),
    source TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, period, ratio_code, source)
);

CREATE TABLE IF NOT EXISTS market_data.corporate_actions (
    action_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    action_type TEXT NOT NULL,
    announcement_date DATE,
    record_date DATE,
    execution_date DATE,
    value TEXT,
    source TEXT NOT NULL,
    url TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_data.text_documents (
    document_id TEXT PRIMARY KEY,
    symbol TEXT,
    source TEXT NOT NULL,
    document_type TEXT NOT NULL,
    title TEXT,
    published_at TIMESTAMPTZ,
    url TEXT,
    storage_path TEXT,
    content_hash TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE VIEW public.price_daily AS
SELECT * FROM market_data.price_daily;

CREATE OR REPLACE VIEW public.ingestion_runs AS
SELECT * FROM market_data.ingestion_runs;

CREATE OR REPLACE VIEW public.companies AS
SELECT * FROM market_data.companies;

CREATE OR REPLACE VIEW public.securities AS
SELECT * FROM market_data.securities;

CREATE OR REPLACE VIEW public.financial_statements AS
SELECT * FROM market_data.financial_statements;

CREATE OR REPLACE VIEW public.financial_ratios AS
SELECT * FROM market_data.financial_ratios;

CREATE OR REPLACE VIEW public.corporate_actions AS
SELECT * FROM market_data.corporate_actions;

CREATE OR REPLACE VIEW public.text_documents AS
SELECT * FROM market_data.text_documents;
