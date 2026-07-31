"""Ingestion runner with per-source failure isolation (Req 16.4).

Each source ingest is a callable returning a normalized DataFrame. safe_ingest runs
it, records success/failure in load_log, and never raises — so one failing source
does not abort the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass
class IngestResult:
    name: str
    ok: bool
    rows: int
    message: str
    data: pd.DataFrame | None


def _log(engine: Engine, source_id: int | None, status: str, message: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO load_log (source_id, status, message) "
                "VALUES (:sid, :st, :msg)"
            ),
            {"sid": source_id, "st": status, "msg": message[:1000]},
        )


def safe_ingest(
    engine: Engine,
    name: str,
    fn: Callable[[], pd.DataFrame],
    source_id: int | None = None,
) -> IngestResult:
    """Run one source ingest, logging outcome; failures are caught and recorded."""
    try:
        df = fn()
        rows = 0 if df is None else len(df)
        _log(engine, source_id, "success", f"{name}: {rows} rows")
        return IngestResult(name, True, rows, "ok", df)
    except Exception as exc:  # noqa: BLE001 - isolation is the whole point
        _log(engine, source_id, "failure", f"{name}: {type(exc).__name__}: {exc}")
        return IngestResult(name, False, 0, str(exc), None)
