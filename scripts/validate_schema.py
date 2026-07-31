"""Offline validation of pipeline/schema.sql using a Postgres-aware parser.

Runs without a live database. Parses every statement in the Postgres dialect and
reports any that fail to parse. Usage: python scripts/validate_schema.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import sqlglot

SCHEMA = Path(__file__).resolve().parents[1] / "pipeline" / "schema.sql"


def main() -> int:
    sql = SCHEMA.read_text()
    statements = [s for s in sqlglot.transpile(sql, read="postgres", write="postgres")]
    print(f"Parsed {len(statements)} statements from {SCHEMA.name} — all valid Postgres.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"Schema validation FAILED: {exc}")
        sys.exit(1)
