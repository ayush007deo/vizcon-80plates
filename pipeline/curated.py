"""Readers for the hand-authored curated dataset (Req 16.5)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CURATED = Path(__file__).resolve().parent / "curated"


def _split(series: pd.Series) -> pd.Series:
    """Turn 'a|b|c' cells into lists; NaN/empty -> []."""
    return series.fillna("").apply(lambda s: [x for x in str(s).split("|") if x])


def famous_dishes() -> pd.DataFrame:
    df = pd.read_csv(CURATED / "famous_dishes.csv")
    df["taste_tags"] = _split(df["taste_tags"])
    return df


def festivals() -> pd.DataFrame:
    df = pd.read_csv(CURATED / "festivals.csv")
    df["foods"] = _split(df["foods"])
    return df


def migration() -> pd.DataFrame:
    return pd.read_csv(CURATED / "migration.csv")


def spice_routes() -> pd.DataFrame:
    return pd.read_csv(CURATED / "spice_routes.csv")


def dinner_symbolism() -> pd.DataFrame:
    df = pd.read_csv(CURATED / "dinner_symbolism.csv")
    for col in ("connecting_ingredients", "trade_routes", "cultural_values"):
        df[col] = _split(df[col])
    return df


def plate_composition() -> pd.DataFrame:
    """Curated food-group proportions (iso3, food_group, pct) — FAOSTAT fallback."""
    return pd.read_csv(CURATED / "plate_composition.csv")


def country_stats() -> pd.DataFrame:
    """Curated scalar fallbacks: life_expectancy, population, tourists, heritage."""
    return pd.read_csv(CURATED / "country_stats.csv")


def cuisine_country_map() -> dict[str, str]:
    df = pd.read_csv(CURATED / "cuisine_country_map.csv")
    return dict(zip(df["cuisine"].str.lower(), df["iso3"].str.upper()))
