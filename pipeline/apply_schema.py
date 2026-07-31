"""Apply the PostgreSQL schema (task 2.2).

Idempotent: schema.sql uses IF NOT EXISTS throughout, so running this repeatedly
is safe. Usage:

    python -m pipeline.apply_schema
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from data.db import get_engine

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def apply_schema() -> None:
    """Execute schema.sql against the configured database."""
    ddl = SCHEMA_PATH.read_text()
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(ddl))
    print(f"Applied schema from {SCHEMA_PATH.name}")


if __name__ == "__main__":
    apply_schema()
