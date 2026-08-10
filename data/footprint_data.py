"""Environmental footprint of the plate — derived, no new database tables.

The story: what does a nation's everyday plate cost the planet, and can a country
eat *well* (long, healthy lives) without eating *heavy* (a high-carbon diet)?

We reuse the food-group composition already loaded per country (`country_food_group`)
and weight it by a small lookup of the environmental cost of each food group. The
lookup values are representative per-group averages drawn from Our World in Data's
"Environmental Impacts of Food" (Poore & Nemecek, 2018, *Science*), which reports the
greenhouse-gas emissions, land use, and freshwater withdrawals per kilogram of food
across the global supply chain.

Because plate composition is a share of the plate (percentages that sum to ~100), the
country metric is an *intensity*: the average kilograms of CO2-equivalent (or m2 land,
or litres of water) embodied in one kilogram of the typical plate. It is comparable
across countries and needs no per-country emissions dataset — an elegant reuse of data
we already trust.

Source: Our World in Data — Environmental impacts of food production
        https://ourworldindata.org/environmental-impacts-of-food
        (Poore, J. & Nemecek, T. (2018). Science, 360(6392), 987-992.)
"""
from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd

from data.db import run_query

SOURCE_NAME = "Our World in Data — Environmental Impacts of Food"
SOURCE_URL = "https://ourworldindata.org/environmental-impacts-of-food"

# ---------------------------------------------------------------------------
# Cache shim: use st.cache_data when Streamlit is running, else a no-op (tests).
# ---------------------------------------------------------------------------
try:  # pragma: no cover
    import streamlit as st

    _TESTING = os.environ.get("ATW_TESTING") == "1"

    def _cache(func):
        return func if _TESTING else st.cache_data(ttl=3600)(func)
except Exception:  # noqa: BLE001

    def _cache(func):
        return func


# ---------------------------------------------------------------------------
# Environmental cost per food group.
# Representative per-group averages from OWID / Poore & Nemecek (2018):
#   co2   = kg CO2-equivalent per kg of food (full supply chain)
#   land  = m2 of land used per kg of food (per year)
#   water = litres of freshwater withdrawn per kg of food
# The "Meat", "Dairy", "Seafood", "Oils" and "Cereals" groups are aggregates, so their
# values are supply-weighted blends of their members (e.g. Meat blends poultry, pork,
# beef and lamb). These are group-level approximations, not exact national figures.
# ---------------------------------------------------------------------------
FOOTPRINT: dict[str, dict[str, float]] = {
    "Cereals":    {"co2": 2.7,  "land": 3.2,  "water": 900},
    "Vegetables": {"co2": 0.5,  "land": 0.4,  "water": 240},
    "Fruits":     {"co2": 1.1,  "land": 1.0,  "water": 420},
    "Pulses":     {"co2": 0.9,  "land": 3.4,  "water": 1250},
    "Roots":      {"co2": 0.6,  "land": 0.9,  "water": 90},
    "Nuts":       {"co2": 0.4,  "land": 13.0, "water": 4100},
    "Oils":       {"co2": 6.3,  "land": 8.0,  "water": 2000},
    "Sugar":      {"co2": 2.5,  "land": 2.0,  "water": 210},
    "Dairy":      {"co2": 3.2,  "land": 9.0,  "water": 630},
    "Eggs":       {"co2": 4.5,  "land": 6.3,  "water": 580},
    "Seafood":    {"co2": 5.1,  "land": 2.9,  "water": 1500},
    "Meat":       {"co2": 22.0, "land": 45.0, "water": 1200},
}

# Food groups that come from animals — used to explain *why* a diet is heavy.
ANIMAL_GROUPS = {"Meat", "Dairy", "Eggs", "Seafood"}

GROUP_EMOJI = {
    "Cereals": "🌾", "Vegetables": "🥬", "Fruits": "🍓", "Pulses": "🫘",
    "Roots": "🥔", "Nuts": "🥜", "Oils": "🫒", "Sugar": "🍬",
    "Dairy": "🧀", "Eggs": "🥚", "Seafood": "🐟", "Meat": "🥩",
}


def footprint_table() -> pd.DataFrame:
    """The lookup as a tidy frame: food_group, co2, land, water."""
    rows = [{"food_group": g, **v} for g, v in FOOTPRINT.items()]
    return pd.DataFrame(rows, columns=["food_group", "co2", "land", "water"])


# ---------------------------------------------------------------------------
# Per-country diet footprint (weighted by plate composition).
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _plate_frame() -> pd.DataFrame:
    """Country plate composition joined to profile scalars (region, life exp, pop)."""
    return run_query(
        """
        SELECT fg.iso3, fg.food_group, fg.pct,
               c.name, c.region, c.life_expectancy, c.population
        FROM country_food_group fg
        JOIN country_profile c ON c.iso3 = fg.iso3
        """
    )


def _weighted(group: pd.DataFrame, metric: str) -> float:
    """Plate-share-weighted average of a footprint metric for one country."""
    total_pct = 0.0
    total_val = 0.0
    for _, r in group.iterrows():
        fp = FOOTPRINT.get(r["food_group"])
        if fp is None:
            continue
        total_pct += float(r["pct"])
        total_val += float(r["pct"]) * fp[metric]
    return total_val / total_pct if total_pct > 0 else float("nan")


@_cache
def country_footprints() -> pd.DataFrame:
    """One row per country with the intensity of its plate.

    Columns: iso3, name, region, life_expectancy, population,
             co2, land, water, animal_share (%), planet_score (0-100, higher = greener).
    """
    plate = _plate_frame()
    if plate.empty:
        return pd.DataFrame()

    rows = []
    for iso3, grp in plate.groupby("iso3"):
        first = grp.iloc[0]
        animal_pct = grp[grp["food_group"].isin(ANIMAL_GROUPS)]["pct"].sum()
        total_pct = grp["pct"].sum()
        rows.append({
            "iso3": iso3,
            "name": first["name"],
            "region": first["region"],
            "life_expectancy": first["life_expectancy"],
            "population": first["population"],
            "co2": _weighted(grp, "co2"),
            "land": _weighted(grp, "land"),
            "water": _weighted(grp, "water"),
            "animal_share": (animal_pct / total_pct * 100) if total_pct else float("nan"),
        })
    df = pd.DataFrame(rows).dropna(subset=["co2"])

    # Planet score: min-max invert of CO2 intensity so greener plates score higher.
    lo, hi = df["co2"].min(), df["co2"].max()
    if hi > lo:
        df["planet_score"] = ((hi - df["co2"]) / (hi - lo) * 100).round(1)
    else:
        df["planet_score"] = 100.0
    return df.sort_values("co2").reset_index(drop=True)


@_cache
def country_breakdown(iso3: str) -> pd.DataFrame:
    """Per-food-group CO2 contribution for one country's plate (largest first).

    Columns: food_group, pct, co2_per_kg, co2_contribution (share-weighted).
    """
    plate = _plate_frame()
    grp = plate[plate["iso3"] == iso3]
    if grp.empty:
        return pd.DataFrame(columns=["food_group", "pct", "co2_per_kg", "co2_contribution"])
    total_pct = grp["pct"].sum() or 1.0
    rows = []
    for _, r in grp.iterrows():
        fp = FOOTPRINT.get(r["food_group"])
        if fp is None:
            continue
        rows.append({
            "food_group": r["food_group"],
            "pct": float(r["pct"]),
            "co2_per_kg": fp["co2"],
            "co2_contribution": float(r["pct"]) / total_pct * fp["co2"],
        })
    out = pd.DataFrame(rows)
    return out.sort_values("co2_contribution", ascending=False).reset_index(drop=True)


@_cache
def footprint_story() -> dict:
    """Headline numbers for the sustainability hero, or {} if data is thin."""
    df = country_footprints()
    if len(df) < 6:
        return {}

    greenest = df.nsmallest(5, "co2")[["iso3", "name", "co2", "animal_share",
                                       "life_expectancy"]].to_dict("records")
    heaviest = df.nlargest(5, "co2")[["iso3", "name", "co2", "animal_share",
                                      "life_expectancy"]].to_dict("records")

    # Do low-footprint diets pay for it in shorter lives? (The surprise: not really.)
    d = df.dropna(subset=["life_expectancy"])
    corr = (float(d["co2"].corr(d["life_expectancy"]))
            if len(d) >= 6 and d["co2"].nunique() > 1 else None)

    # The "healthy AND sustainable" quadrant: below-median footprint, above-median life.
    med_co2 = df["co2"].median()
    med_life = d["life_expectancy"].median() if not d.empty else None
    sweet_spot = 0
    if med_life is not None:
        sweet_spot = int(len(d[(d["co2"] <= med_co2) & (d["life_expectancy"] >= med_life)]))

    return {
        "n": int(len(df)),
        "min_co2": float(df["co2"].min()),
        "max_co2": float(df["co2"].max()),
        "mean_co2": float(df["co2"].mean()),
        "ratio": float(df["co2"].max() / df["co2"].min()) if df["co2"].min() > 0 else None,
        "greenest": greenest,
        "heaviest": heaviest,
        "corr_life": corr,
        "median_co2": float(med_co2),
        "median_life": float(med_life) if med_life is not None else None,
        "sweet_spot_count": sweet_spot,
    }
