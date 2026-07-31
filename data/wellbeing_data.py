"""CSV-derived World Happiness Report data — no database.

Reads the World Happiness Report yearly CSVs directly (cached), normalizing the
schema differences across years, and resolves country names to iso3 via the ISO
reference. Powers the "happiest tables" story: where the world feels best, and the
factors behind it (social support, healthy life expectancy, freedom, generosity).
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from pipeline.ingest import iso_reference

_DIR = Path(__file__).resolve().parents[1] / "data" / "World Happiness Report up to 2022"

try:  # pragma: no cover
    import streamlit as st

    _TESTING = os.environ.get("ATW_TESTING") == "1"

    def _cache(func):
        return func if _TESTING else st.cache_data(ttl=3600)(func)
except Exception:  # noqa: BLE001

    def _cache(func):
        return func


# Per-schema column resolution. Values are lists of candidate column names.
_COUNTRY = ["Country or region", "Country name", "Country"]
_SCORE = ["Score", "Ladder score", "Happiness score"]
_FACTORS = {
    "gdp": ["GDP per capita", "Explained by: Log GDP per capita", "Explained by: GDP per capita"],
    "social": ["Social support", "Explained by: Social support"],
    "life_exp": ["Healthy life expectancy", "Explained by: Healthy life expectancy"],
    "freedom": ["Freedom to make life choices", "Explained by: Freedom to make life choices"],
    "generosity": ["Generosity", "Explained by: Generosity"],
    "corruption": ["Perceptions of corruption", "Explained by: Perceptions of corruption"],
}


def _num(series: pd.Series) -> pd.Series:
    """Coerce to float, handling European decimals ('7,821') and thousands."""
    s = series.astype(str).str.strip().str.replace('"', "", regex=False)
    # If commas are decimal separators (no dot present), swap them.
    if s.str.contains(",").any() and not s.str.contains(r"\.").any():
        s = s.str.replace(",", ".", regex=False)
    else:
        s = s.str.replace(",", "", regex=False)
    return pd.to_numeric(s, errors="coerce")


def _pick(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


@lru_cache(maxsize=1)
def _latest_frame() -> pd.DataFrame:
    """Most recent year's happiness table, normalized to iso3 + score + factors."""
    if not _DIR.exists():
        return pd.DataFrame()
    files = sorted(_DIR.glob("*.csv"))
    if not files:
        return pd.DataFrame()
    path = files[-1]  # latest year available
    year = int(re.search(r"(\d{4})", path.name).group(1))
    df = pd.read_csv(path)

    ccol, scol = _pick(df, _COUNTRY), _pick(df, _SCORE)
    if not ccol or not scol:
        return pd.DataFrame()

    n2i = iso_reference.name_to_iso3()
    out = pd.DataFrame({"country": df[ccol].astype(str)})
    out["iso3"] = out["country"].map(lambda c: n2i.get(re.sub(r"[^a-z]", "", c.lower())))
    out["score"] = _num(df[scol])
    for key, cands in _FACTORS.items():
        col = _pick(df, cands)
        out[key] = _num(df[col]) if col else pd.NA
    out["year"] = year

    regions = dict(zip(iso_reference.ingest()["iso3"], iso_reference.ingest()["region"]))
    out["region"] = out["iso3"].map(regions)
    return out.dropna(subset=["iso3", "score"]).reset_index(drop=True)


@_cache
def latest_year() -> int | None:
    df = _latest_frame()
    return int(df["year"].iloc[0]) if not df.empty else None


@_cache
def happiness() -> pd.DataFrame:
    """iso3, country, region, score (0-10 ladder) + factor columns, latest year."""
    return _latest_frame().copy()


@_cache
def happiest(limit: int = 10) -> pd.DataFrame:
    df = _latest_frame()
    return df.sort_values("score", ascending=False).head(limit).reset_index(drop=True)


@_cache
def factors(iso3: str) -> dict:
    """Factor contributions for one country (what makes it happy)."""
    df = _latest_frame()
    row = df[df["iso3"] == iso3]
    if row.empty:
        return {}
    r = row.iloc[0]
    keys = {"gdp": "Economy", "social": "Social support",
            "life_exp": "Healthy life expectancy", "freedom": "Freedom",
            "generosity": "Generosity", "corruption": "Trust / low corruption"}
    out = {"country": r["country"], "score": float(r["score"]), "factors": {}}
    for k, label in keys.items():
        v = r.get(k)
        if pd.notna(v):
            out["factors"][label] = float(v)
    return out
