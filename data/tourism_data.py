"""CSV-derived tourism analytics — no database, computed directly from the dataset.

Reads pipeline/raw/tourism_economy.csv once (cached) and derives every insight the
Travel & Tourism dashboard needs with pandas: global trend, the COVID collapse, top
destinations, spend per visitor, tourism dependence, and per-country series. Country
names/regions come from the bundled ISO 3166 reference (also a file), so this module
never touches PostgreSQL and loads instantly.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

from pipeline.ingest import iso_reference

_CSV = Path(__file__).resolve().parents[1] / "pipeline" / "raw" / "tourism_economy.csv"

_RENAME = {
    "country_code": "iso3",
    "tourism_arrivals": "arrivals",
    "tourism_receipts": "receipts",
    "tourism_exports": "exports_pct",
    "tourism_departures": "departures",
    "tourism_expenditures": "expenditures",
}
_METRICS = ["arrivals", "receipts", "exports_pct", "departures", "expenditures", "gdp"]

# Cache shim: st.cache_data when Streamlit runs, else a no-op (tests/pipeline).
try:  # pragma: no cover
    import streamlit as st

    _TESTING = os.environ.get("ATW_TESTING") == "1"

    def _cache(func):
        return func if _TESTING else st.cache_data(ttl=3600)(func)
except Exception:  # noqa: BLE001

    def _cache(func):
        return func


@lru_cache(maxsize=1)
def _frame() -> pd.DataFrame:
    """Load, clean, and enrich the tourism CSV once (real countries only)."""
    if not _CSV.exists():
        return pd.DataFrame(columns=["iso3", "name", "region", "year", *_METRICS])
    df = pd.read_csv(_CSV)
    df = df.dropna(subset=["country_code", "year"]).rename(columns=_RENAME)
    df["iso3"] = df["iso3"].astype(str).str.upper()
    df["year"] = df["year"].astype(int)
    # Real ISO countries only (drop World Bank aggregates like WLD, HIC, OED).
    df = df[df["iso3"].isin(iso_reference.valid_iso3())]
    df = df[df[_METRICS].notna().any(axis=1)]

    ref = iso_reference.ingest()[["iso3", "name", "region"]]
    df = df.merge(ref, on="iso3", how="left")
    df["name"] = df["name"].fillna(df["iso3"])
    return df[["iso3", "name", "region", "year", *_METRICS]]


# ---------------------------------------------------------------------------
# Derived views
# ---------------------------------------------------------------------------
@_cache
def years() -> list[int]:
    df = _frame()
    return sorted(int(y) for y in df["year"].unique())


@_cache
def countries() -> pd.DataFrame:
    """iso3, name, region for countries with any arrivals/receipts, sorted by name."""
    df = _frame()
    m = df[df["arrivals"].notna() | df["receipts"].notna()]
    out = m[["iso3", "name", "region"]].drop_duplicates().sort_values("name")
    return out.reset_index(drop=True)


@_cache
def global_trend() -> pd.DataFrame:
    df = _frame()
    g = df.groupby("year").agg(
        arrivals=("arrivals", "sum"), receipts=("receipts", "sum"),
        arrivals_n=("arrivals", "count"), receipts_n=("receipts", "count"),
    ).reset_index()
    return g.sort_values("year")


@_cache
def country_series(iso3s: tuple[str, ...]) -> pd.DataFrame:
    iso3s = tuple(i for i in iso3s if i)
    if not iso3s:
        return pd.DataFrame(columns=["iso3", "name", "year", "arrivals", "receipts", "exports_pct"])
    df = _frame()
    out = df[df["iso3"].isin(iso3s)][
        ["iso3", "name", "year", "arrivals", "receipts", "exports_pct"]
    ]
    return out.sort_values(["iso3", "year"])


@_cache
def top_destinations(year: int, metric: str = "arrivals", limit: int = 12) -> pd.DataFrame:
    col = "receipts" if metric == "receipts" else "arrivals"
    df = _frame()
    d = df[(df["year"] == year) & df[col].notna()].copy()
    d = d.rename(columns={col: "value"})
    return d[["iso3", "name", "region", "value"]].sort_values(
        "value", ascending=False).head(limit).reset_index(drop=True)


@_cache
def choropleth(year: int, metric: str = "arrivals") -> pd.DataFrame:
    col = "receipts" if metric == "receipts" else "arrivals"
    df = _frame()
    d = df[(df["year"] == year) & df[col].notna()].copy()
    d = d.rename(columns={col: "value"})
    return d[["iso3", "name", "region", "value"]].reset_index(drop=True)


@_cache
def choropleth_all_years(metric: str = "arrivals") -> pd.DataFrame:
    """Every country-year with a value, for an animated year-sweep map."""
    col = "receipts" if metric == "receipts" else "arrivals"
    df = _frame()
    d = df[df[col].notna()].copy().rename(columns={col: "value"})
    return d[["iso3", "name", "region", "year", "value"]].sort_values("year")


@_cache
def spend_per_visitor(year: int, min_arrivals: int = 1_000_000, limit: int = 12) -> pd.DataFrame:
    df = _frame()
    d = df[(df["year"] == year) & df["arrivals"].notna() & df["receipts"].notna()
           & (df["arrivals"] >= min_arrivals)].copy()
    d["spend_per_visitor"] = d["receipts"] / d["arrivals"].replace(0, pd.NA)
    d = d.dropna(subset=["spend_per_visitor"])
    return d[["iso3", "name", "region", "arrivals", "receipts", "spend_per_visitor"]] \
        .sort_values("spend_per_visitor", ascending=False).head(limit).reset_index(drop=True)


@_cache
def dependence(year: int, limit: int = 12) -> pd.DataFrame:
    df = _frame()
    d = df[(df["year"] == year) & df["exports_pct"].notna() & (df["exports_pct"] > 0)]
    return d[["iso3", "name", "region", "exports_pct"]].sort_values(
        "exports_pct", ascending=False).head(limit).reset_index(drop=True)


@_cache
def covid_impact() -> dict:
    """Global arrivals at the pre-pandemic peak vs the following trough (data-discovered)."""
    g = global_trend()
    g = g[g["arrivals_n"] > 0]
    if len(g) < 2:
        return {}
    peak_year = int(g.loc[g["arrivals"].idxmax(), "year"])
    after = g[g["year"] > peak_year]
    if after.empty:
        return {}
    trough_year = int(after.loc[after["arrivals"].idxmin(), "year"])

    df = _frame()
    panel = (set(df[(df["year"] == peak_year) & df["arrivals"].notna()]["iso3"])
             & set(df[(df["year"] == trough_year) & df["arrivals"].notna()]["iso3"]))
    if not panel:
        return {}
    sub = df[df["iso3"].isin(panel)]
    vals = {y: float(sub[sub["year"] == y]["arrivals"].sum()) for y in (peak_year, trough_year)}
    out = {"arrivals": vals, "peak_year": peak_year, "trough_year": trough_year,
           "panel_n": len(panel)}
    if vals[peak_year] > 0:
        out["crash_pct"] = (vals[trough_year] - vals[peak_year]) / vals[peak_year] * 100
    return out


@_cache
def country_facts(iso3: str) -> dict:
    """A compact set of click-to-reveal facts for one country's tourism story."""
    df = _frame()
    d = df[df["iso3"] == iso3].sort_values("year")
    d = d[d["arrivals"].notna() | d["receipts"].notna()]
    if d.empty:
        return {}
    name = d["name"].iloc[0]
    region = d["region"].iloc[0]
    facts: dict = {"iso3": iso3, "name": name, "region": region}

    arr = d[d["arrivals"].notna()]
    if not arr.empty:
        peak = arr.loc[arr["arrivals"].idxmax()]
        facts["peak_arrivals"] = float(peak["arrivals"])
        facts["peak_year"] = int(peak["year"])
        latest = arr.iloc[-1]
        facts["latest_year"] = int(latest["year"])
        facts["latest_arrivals"] = float(latest["arrivals"])

    rec = d[d["receipts"].notna()]
    if not rec.empty:
        facts["latest_receipts"] = float(rec.iloc[-1]["receipts"])
        facts["receipts_year"] = int(rec.iloc[-1]["year"])

    both = d[d["arrivals"].notna() & d["receipts"].notna() & (d["arrivals"] > 0)]
    if not both.empty:
        last = both.iloc[-1]
        facts["spend_per_visitor"] = float(last["receipts"] / last["arrivals"])

    dep = d[d["exports_pct"].notna()]
    if not dep.empty:
        facts["exports_pct"] = float(dep.iloc[-1]["exports_pct"])
    return facts
