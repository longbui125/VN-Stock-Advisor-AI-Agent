from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "postgres_schema.sql"


def get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config_path = resolve_project_path(path)
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def get_default_symbols(config: dict[str, Any], source_name: str = "vnstock_market") -> list[str]:
    source = config.get("sources", {}).get(source_name, {})
    return [str(symbol).upper() for symbol in source.get("default_symbols", [])]
