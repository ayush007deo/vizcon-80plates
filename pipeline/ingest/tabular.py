"""Local-file ingest for the downloaded public datasets, parsed to their real formats.

Files live under pipeline/raw/. Each ingest returns a normalized frame; loaders that
can resolve a country identifier return an `iso3` column, otherwise a `country` name
column to be reconciled downstream. Missing files raise FileNotFoundError so
safe_ingest logs a failure and the pipeline continues (Req 16.4).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipeline.ingest import iso_reference

RAW = Path(__file__).resolve().parents[1] / "raw"


def _require(filename: str) -> Path:
    path = RAW / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Expected dataset not found: {path} (download it — see data.txt)"
        )
    return path


# --- FAOSTAT Food Balance Sheets (wide) -----------------------------------
# Map FAOSTAT FBS item names to friendly plate food groups.
_FAO_ITEM_TO_GROUP = {
    "Cereals - Excluding Beer": "Cereals",
    "Starchy Roots": "Roots",
    "Sugar & Sweeteners": "Sugar",
    "Sugar Crops": "Sugar",
    "Pulses": "Pulses",
    "Treenuts": "Nuts",
    "Nuts and products": "Nuts",
    "Oilcrops": "Oils",
    "Vegetable Oils": "Oils",
    "Vegetables": "Vegetables",
    "Fruits - Excluding Wine": "Fruits",
    "Meat": "Meat",
    "Offals": "Meat",
    "Fish, Seafood": "Seafood",
    "Milk - Excluding Butter": "Dairy",
    "Eggs": "Eggs",
    "Animal fats": "Oils",
}
_FAO_KCAL_ELEMENT = 664  # "Food supply (kcal/capita/day)"


def faostat_food_groups() -> pd.DataFrame:
    """FAOSTAT food balance -> iso3, food_group, quantity (kcal/capita/day, latest year).

    Aggregates FBS item-level calorie supply into plate food groups for the most
    recent year available, keyed to iso3 via the UN M49 area code.
    """
    path = _require("faostat_food_balance.csv")
    m49 = iso_reference.m49_to_iso3()

    usecols = ["Area Code (M49)", "Item", "Element Code"]
    year_cols = [f"Y{y}" for y in range(2010, 2023)]
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)

    # Keep only calorie-supply rows for items we map to a plate group.
    df = df[df["Element Code"] == _FAO_KCAL_ELEMENT]
    df = df[df["Item"].isin(_FAO_ITEM_TO_GROUP)]

    present_years = [c for c in year_cols if c in df.columns]
    if not present_years:
        raise ValueError("FAOSTAT: no expected year columns found")

    def _latest(row):
        for c in reversed(present_years):
            v = row.get(c)
            if pd.notna(v):
                return v
        return None

    df = df.copy()
    df["quantity"] = df.apply(_latest, axis=1)
    df = df.dropna(subset=["quantity"])

    # M49 code arrives like "'004"; strip non-digits.
    def _iso3(code) -> str | None:
        s = "".join(ch for ch in str(code) if ch.isdigit())
        return m49.get(int(s)) if s else None

    df["iso3"] = df["Area Code (M49)"].map(_iso3)
    df["food_group"] = df["Item"].map(_FAO_ITEM_TO_GROUP)
    df = df.dropna(subset=["iso3"])

    # Sum items that map to the same group (e.g., Meat + Offals).
    out = (
        df.groupby(["iso3", "food_group"], as_index=False)["quantity"].sum()
    )
    return out


# --- Life expectancy (long time series) -----------------------------------
def life_expectancy() -> pd.DataFrame:
    """Our World in Data life expectancy -> iso3, life_expectancy (latest year).

    The OWID export carries an ISO3 `Code`; aggregate rows (World, regions) have an
    empty Code and are dropped. Falls back to country names if Code is absent.
    """
    df = pd.read_csv(_require("life_expectancy.csv"))
    df = df.rename(columns={"Entity": "country", "Life expectancy": "life_expectancy",
                            "Life Expectancy": "life_expectancy", "Code": "iso3"})
    if "iso3" in df.columns:
        df = df.dropna(subset=["iso3"])
        df["iso3"] = df["iso3"].astype(str).str.upper()
        if "Year" in df.columns:
            df = df.sort_values("Year").groupby("iso3", as_index=False).last()
        return df[["iso3", "life_expectancy"]].dropna()
    if "Year" in df.columns:
        df = df.sort_values("Year").groupby("country", as_index=False).last()
    return df[["country", "life_expectancy"]].dropna()


# --- Population (has ISO3 as CCA3) -----------------------------------------
def population() -> pd.DataFrame:
    """World population dataset -> iso3, population (2022)."""
    df = pd.read_csv(_require("world_population.csv"))
    df = df.rename(columns={"CCA3": "iso3", "2022 Population": "population"})
    df["iso3"] = df["iso3"].astype(str).str.upper()
    return df[["iso3", "population"]].dropna()


# --- Tourism (World Bank WDI, year columns, 4 header rows) -----------------
def tourism() -> pd.DataFrame:
    """World Bank international arrivals -> iso3, annual_tourists (latest year)."""
    path = _require("tourism_arrivals.csv")
    df = pd.read_csv(path, skiprows=4)
    year_cols = [c for c in df.columns if c.strip().isdigit()]

    def _latest(row):
        for c in reversed(year_cols):
            v = row.get(c)
            if pd.notna(v):
                return v
        return None

    df["annual_tourists"] = df.apply(_latest, axis=1)
    df = df.rename(columns={"Country Code": "iso3"})
    df["iso3"] = df["iso3"].astype(str).str.upper()
    out = df[["iso3", "annual_tourists"]].dropna()
    return out


# --- World tourism & economy (arrivals + receipts, by ISO3) ----------------
def tourism_economy() -> pd.DataFrame:
    """World tourism-economy dataset -> iso3, annual_tourists, tourism_receipts (latest year)."""
    df = pd.read_csv(_require("tourism_economy.csv"))
    df = df.dropna(subset=["country_code"])
    df = df.rename(columns={"country_code": "iso3", "tourism_arrivals": "annual_tourists"})
    # Latest year per country that has at least arrivals or receipts.
    df = df[df["annual_tourists"].notna() | df["tourism_receipts"].notna()]
    df = df.sort_values("year").groupby("iso3", as_index=False).last()
    df["iso3"] = df["iso3"].astype(str).str.upper()
    return df[["iso3", "annual_tourists", "tourism_receipts"]]


# --- UNESCO World Heritage (WHC 2019 structured dataset, CC0) --------------
_WHC = "unesco_2019/whc-sites-2019.csv"


def _read_whc() -> pd.DataFrame:
    return pd.read_csv(_require(_WHC), encoding="latin-1", low_memory=False)


def unesco() -> pd.DataFrame:
    """Per-country UNESCO site counts -> country, unesco_heritage_count."""
    df = _read_whc()
    counts = (
        df.groupby("states_name_en").size()
        .reset_index(name="unesco_heritage_count")
        .rename(columns={"states_name_en": "country"})
    )
    return counts


_CULINARY_RE = (
    r"cuisine|culinary|gastronom|\bfood\b|\bdish|bread|coffee|\btea\b|\bwine\b|\bbeer\b|"
    r"\bdiet\b|cooking|\bmeal|beverage|ferment|noodle|couscous|kimchi|pizza|\bsoup|pilaf|"
    r"palov|dolma|lavash|flatbread|baking|brew"
)


def culinary_heritage() -> pd.DataFrame:
    """UNESCO Intangible Cultural Heritage, filtered to culinary/food traditions.

    Returns one row per (element, country): element, year, link, country.
    """
    path = _require("ich/elements.csv")
    df = pd.read_csv(path, engine="python", on_bad_lines="skip").fillna("")
    mask = (
        df["label"].str.contains(_CULINARY_RE, case=False, regex=True)
        | df["primary_concepts"].str.contains(_CULINARY_RE, case=False, regex=True)
    )
    food = df[mask]
    rows = []
    for _, r in food.iterrows():
        year = int(r["year"]) if str(r["year"]).strip().isdigit() else None
        for country in str(r["countries"]).split(","):
            country = country.strip()
            if country:
                rows.append({"element": r["label"], "year": year,
                             "link": r["link"], "country": country})
    return pd.DataFrame(rows)


def heritage_sites() -> pd.DataFrame:
    """Individual heritage sites -> name, country, category, region, lat, lon, year, danger."""
    df = _read_whc()
    out = df.rename(columns={
        "name_en": "name", "states_name_en": "country", "region_en": "region",
        "latitude": "latitude", "longitude": "longitude",
        "date_inscribed": "year_inscribed",
    })[["name", "country", "category", "region", "latitude", "longitude",
        "year_inscribed", "danger"]].copy()
    out["in_danger"] = out["danger"].fillna(0).astype(int) == 1
    out = out.drop(columns=["danger"])
    out = out.dropna(subset=["latitude", "longitude"])
    return out
