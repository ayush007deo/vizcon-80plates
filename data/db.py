"""Database engine and low-level query helpers.

Supports both PostgreSQL (for pipeline/local dev) and SQLite (for Streamlit Cloud).
Uses SQLite bundled database at data/plates.db when DATABASE_URL points to sqlite.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

import config

_SQLITE_PATH = Path(__file__).resolve().parent / "plates.db"


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return a process-wide SQLAlchemy engine.
    
    Uses SQLite if DATABASE_URL contains 'sqlite' or if plates.db exists
    and DATABASE_URL is not explicitly set to postgres.
    """
    url = config.DATABASE_URL
    if "sqlite" in url:
        return create_engine(url, future=True)
    if _SQLITE_PATH.exists() and "postgresql" not in url:
        return create_engine(f"sqlite:///{_SQLITE_PATH}", future=True)
    # If postgres is configured but unreachable, fall back to SQLite
    try:
        engine = create_engine(url, pool_pre_ping=True, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception:  # noqa: BLE001
        if _SQLITE_PATH.exists():
            return create_engine(f"sqlite:///{_SQLITE_PATH}", future=True)
        raise


def run_query(sql: str, params: Mapping[str, Any] | None = None) -> pd.DataFrame:
    """Run a parameterized SELECT and return the result as a DataFrame."""
    engine = get_engine()
    # SQLite doesn't support all PostgreSQL syntax, handle common differences
    adjusted_sql = sql
    is_sqlite = "sqlite" in str(engine.url)
    if is_sqlite:
        adjusted_sql = adjusted_sql.replace("::text", "")
        adjusted_sql = adjusted_sql.replace("ILIKE", "LIKE")
        # string_agg(DISTINCT col, sep ORDER BY col) -> group_concat(col, sep)
        import re
        adjusted_sql = re.sub(
            r"string_agg\(DISTINCT\s+(\w+),\s*'([^']*)'\s*ORDER BY \w+\)",
            r"group_concat(\1, '\2')",
            adjusted_sql
        )
        # string_agg(col, sep) -> group_concat(col, sep)
        adjusted_sql = re.sub(
            r"string_agg\((\w+),\s*'([^']*)'\)",
            r"group_concat(\1, '\2')",
            adjusted_sql
        )
        # Remove unnest/LATERAL (PostgreSQL-specific)
        if "unnest" in adjusted_sql.lower():
            return pd.DataFrame()
    with engine.connect() as conn:
        df = pd.read_sql(text(adjusted_sql), conn, params=dict(params or {}))
    # Parse JSON string columns back to Python lists (SQLite stores arrays as JSON)
    if is_sqlite and not df.empty:
        _parse_json_columns(df)
    return df


def _parse_json_columns(df: pd.DataFrame) -> None:
    """In-place: convert JSON-encoded list strings to actual Python lists."""
    import json
    for col in df.columns:
        # Pandas 3.0+ uses StringDtype; older uses object
        if df[col].dtype == object or df[col].dtype.name in ("str", "string", "object"):
            sample = df[col].dropna().head(3)
            if sample.empty:
                continue
            # Check if any value looks like a JSON array
            if any(isinstance(v, str) and v.startswith("[") for v in sample):
                df[col] = df[col].apply(
                    lambda x: json.loads(x) if isinstance(x, str) and x.startswith("[") else x
                )


def ensure_list(val) -> list:
    """Convert a value to a list — handles JSON strings, actual lists, and None."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        if val.startswith("["):
            import json
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return []
        return [val] if val else []
    return list(val)


def execute(sql: str, params: Mapping[str, Any] | None = None) -> None:
    """Run a parameterized statement inside a transaction (pipeline writes)."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(sql), dict(params or {}))
