from __future__ import annotations

from src.utils.postgres import init_schema


def main() -> int:
    init_schema()
    print("Postgres schema initialized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
