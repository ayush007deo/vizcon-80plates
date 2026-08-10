"""CSV-derived spice-consumption analytics — no database.

Reads the FAOSTAT-style 'Global spice consumption.csv' directly (cached) and derives
the world's spice-consumption picture: who consumes the most, the map, and which
spices dominate. Keyed to iso3 via the UN M49 area code; country names from the
bundled ISO reference. Absolute consumption (tonnes) is used — per-capita from this
trade-balance figure is unreliable (small re-exporting nations distort it).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

from pipeline.ingest import iso_reference

_CSV = Path(__file__).resolve().parent / "Global spice consumption.csv"
if not _CSV.exists():
    _CSV = Path(__file__).resolve().parents[1] / "data" / "Global spice consumption.csv"

try:  # pragma: no cover
    import streamlit as st

    _TESTING = os.environ.get("ATW_TESTING") == "1"

    def _cache(func):
        return func if _TESTING else st.cache_data(ttl=3600)(func)
except Exception:  # noqa: BLE001

    def _cache(func):
        return func


# Friendly short names for the FAOSTAT spice items.
_ITEM_SHORT = {
    "Anise, badian, coriander, cumin, caraway, fennel and juniper berries, raw": "Anise & cumin seeds",
    "Chillies and peppers, dry (Capsicum spp., Pimenta spp.), raw": "Chillies & peppers",
    "Cinnamon and cinnamon-tree flowers, raw": "Cinnamon",
    "Cloves (whole stems), raw": "Cloves",
    "Ginger, raw": "Ginger",
    "Nutmeg, mace, cardamoms, raw": "Nutmeg & cardamom",
    "Pepper (Piper spp.), raw": "Pepper",
    "Vanilla, raw": "Vanilla",
    "Spices n.e.c.": "Other spices",
}


@lru_cache(maxsize=1)
def _frame() -> pd.DataFrame:
    import os
    if not _CSV.exists():
        # Try alternate paths
        alt = Path(os.getcwd()) / "data" / "Global spice consumption.csv"
        if alt.exists():
            globals()["_CSV"] = alt
        else:
            return pd.DataFrame(columns=["iso3", "name", "year", "item", "consumption", "production"])
    df = pd.read_csv(_CSV, encoding="latin-1", low_memory=False)
    df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]
    m49 = iso_reference.m49_to_iso3()

    def _iso3(code):
        digits = "".join(ch for ch in str(code) if ch.isdigit())
        return m49.get(int(digits)) if digits else None

    df["iso3"] = df["Area Code (M49)"].map(_iso3)
    df = df.dropna(subset=["iso3"])
    df["item"] = df["Item"].map(lambda x: _ITEM_SHORT.get(str(x).strip(), "Other spices"))
    df = df.rename(columns={"Year": "year", "Consumption": "consumption",
                            "Production": "production"})
    df["year"] = df["year"].astype(int)
    names = dict(zip(iso_reference.ingest()["iso3"], iso_reference.ingest()["name"]))
    df["name"] = df["iso3"].map(names).fillna(df["iso3"])
    df["region"] = df["iso3"].map(
        dict(zip(iso_reference.ingest()["iso3"], iso_reference.ingest()["region"])))
    return df[["iso3", "name", "region", "year", "item", "consumption", "production"]]


@_cache
def latest_year() -> int | None:
    df = _frame()
    return int(df["year"].max()) if not df.empty else None


@_cache
def top_consumers(year: int | None = None, limit: int = 12) -> pd.DataFrame:
    """Countries by total spice consumption (tonnes) for a year."""
    df = _frame()
    if df.empty:
        return df
    year = year or int(df["year"].max())
    cur = df[(df["year"] == year) & df["consumption"].notna()]
    agg = (cur.groupby(["iso3", "name", "region"], as_index=False)["consumption"].sum()
           .sort_values("consumption", ascending=False).head(limit))
    return agg.reset_index(drop=True)


@_cache
def consumption_map(year: int | None = None) -> pd.DataFrame:
    """All countries' total spice consumption for a year (for the choropleth)."""
    df = _frame()
    if df.empty:
        return df
    year = year or int(df["year"].max())
    cur = df[(df["year"] == year) & df["consumption"].notna()]
    return (cur.groupby(["iso3", "name", "region"], as_index=False)["consumption"].sum()
            .reset_index(drop=True))


@_cache
def spice_breakdown(year: int | None = None) -> pd.DataFrame:
    """Global consumption by spice type for a year (which spices the world eats most)."""
    df = _frame()
    if df.empty:
        return df
    year = year or int(df["year"].max())
    cur = df[(df["year"] == year) & df["consumption"].notna()]
    return (cur.groupby("item", as_index=False)["consumption"].sum()
            .sort_values("consumption", ascending=False).reset_index(drop=True))


@_cache
def global_trend() -> pd.DataFrame:
    """Worldwide total spice consumption per year (the growing appetite story)."""
    df = _frame()
    if df.empty:
        return df
    g = (df[df["consumption"].notna()].groupby("year", as_index=False)["consumption"].sum()
         .sort_values("year"))
    return g


@_cache
def regional_intensity(year: int | None = None) -> pd.DataFrame:
    """Average spice consumption per country, by world region (who seasons boldest)."""
    df = _frame()
    if df.empty:
        return df
    year = year or int(df["year"].max())
    cur = df[(df["year"] == year) & df["consumption"].notna() & df["region"].notna()]
    per_country = cur.groupby(["iso3", "region"], as_index=False)["consumption"].sum()
    out = (per_country.groupby("region", as_index=False)["consumption"].mean()
           .rename(columns={"consumption": "avg_consumption"})
           .sort_values("avg_consumption", ascending=False))
    return out.reset_index(drop=True)


_POP = Path(__file__).resolve().parents[1] / "pipeline" / "raw" / "world_population.csv"
_LE = Path(__file__).resolve().parents[1] / "pipeline" / "raw" / "life_expectancy.csv"


@_cache
def spice_vs_longevity(year: int | None = None, min_pop: int = 5_000_000) -> dict:
    """Cross-dataset: do higher-spice cultures live longer?

    Joins per-capita spice consumption (spice CSV ÷ population CSV) with life
    expectancy (OWID CSV), restricted to countries above a population floor to drop
    tiny re-export trade hubs. Buckets countries into Low/Medium/High spice terciles
    and reports average life expectancy per tier + the correlation. Returns {} if the
    inputs are unavailable. Correlation is not causation — framed as a pattern.
    """
    import numpy as np

    df = _frame()
    if df.empty or not _POP.exists() or not _LE.exists():
        return {}
    year = year or int(df["year"].max())
    cons = (df[(df["year"] == year) & df["consumption"].notna()]
            .groupby("iso3")["consumption"].sum())

    pop = pd.read_csv(_POP).rename(columns={"CCA3": "iso3", "2022 Population": "pop"})
    pop["iso3"] = pop["iso3"].astype(str).str.upper()
    le = pd.read_csv(_LE).rename(columns={"Code": "iso3", "Life expectancy": "le",
                                          "Life Expectancy": "le"})
    if "Year" in le.columns:
        le = le.sort_values("Year").groupby("iso3", as_index=False).last()
    le = le[["iso3", "le"]]

    d = (pd.DataFrame({"cons": cons})
         .join(pop.set_index("iso3")["pop"]).join(le.set_index("iso3")["le"]).dropna())
    d = d[d["pop"] > min_pop]
    if len(d) < 12:
        return {}
    d["per_capita_g"] = d["cons"] / d["pop"] * 1_000_000  # grams/person/year
    d["tier"] = pd.qcut(d["per_capita_g"], 3, labels=["Low", "Medium", "High"])
    tiers = d.groupby("tier", observed=True)["le"].mean().round(1).to_dict()
    corr = float(np.log(d["per_capita_g"].clip(lower=0.1)).corr(d["le"]))
    return {"year": year, "n": int(len(d)), "tiers": tiers, "corr": round(corr, 2)}


@_cache
def country_top_spices(iso3: str, year: int | None = None, limit: int = 5) -> pd.DataFrame:
    """A single country's leading spices by consumption (for click/context)."""
    df = _frame()
    if df.empty:
        return df
    year = year or int(df["year"].max())
    cur = df[(df["iso3"] == iso3) & (df["year"] == year) & df["consumption"].notna()]
    return (cur.groupby("item", as_index=False)["consumption"].sum()
            .sort_values("consumption", ascending=False).head(limit).reset_index(drop=True))
