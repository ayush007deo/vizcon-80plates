"""ISO 3166 country/region reference (Req 16.1, 20.3).

Reads pipeline/raw/iso_3166.csv (lukes/ISO-3166-Countries-with-Regional-Codes).
Returns iso3, name, region — the backbone for the consistent identifier and Region.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "raw" / "iso_3166.csv"

# Friendly common names for the verbose official ISO 3166 labels.
_NAME_OVERRIDES = {
    "Iran, Islamic Republic of": "Iran",
    "Korea, Republic of": "South Korea",
    "Korea, Democratic People's Republic of": "North Korea",
    "Russian Federation": "Russia",
    "Bolivia, Plurinational State of": "Bolivia",
    "Venezuela, Bolivarian Republic of": "Venezuela",
    "Tanzania, United Republic of": "Tanzania",
    "Moldova, Republic of": "Moldova",
    "Syrian Arab Republic": "Syria",
    "Viet Nam": "Vietnam",
    "Lao People's Democratic Republic": "Laos",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "United States of America": "United States",
    "Taiwan, Province of China": "Taiwan",
    "Congo, Democratic Republic of the": "DR Congo",
    "Micronesia, Federated States of": "Micronesia",
    "Palestine, State of": "Palestine",
    "Netherlands, Kingdom of the": "Netherlands",
    "Türkiye": "Turkey",
    "Czechia": "Czechia",
    "Brunei Darussalam": "Brunei",
    "Bolivia (Plurinational State of)": "Bolivia",
    "Iran (Islamic Republic of)": "Iran",
    "Venezuela (Bolivarian Republic of)": "Venezuela",
}


def display_name(official: str) -> str:
    """Return a short, friendly country name from an official ISO 3166 label."""
    if official in _NAME_OVERRIDES:
        return _NAME_OVERRIDES[official]
    s = re.sub(r"\s*\(.*?\)", "", official)   # drop parentheticals
    s = s.split(",")[0].strip()                 # cut at the first comma
    return s or official


def ingest() -> pd.DataFrame:
    if not RAW.exists():
        raise FileNotFoundError(f"Missing ISO reference: {RAW}")
    df = pd.read_csv(RAW, dtype=str)
    out = df.rename(columns={"alpha-3": "iso3"})[["iso3", "name", "region"]].copy()
    out["iso3"] = out["iso3"].str.upper()
    out["name"] = out["name"].map(display_name)
    # Drop rows without a usable region label (e.g., Antarctica).
    out["region"] = out["region"].replace("", pd.NA)
    return out.dropna(subset=["iso3", "name"]).reset_index(drop=True)


def alpha2_to_iso3() -> dict[str, str]:
    """Map ISO 3166-1 alpha-2 -> alpha-3 for reconciling code-based sources."""
    df = pd.read_csv(RAW, dtype=str)
    return {
        str(a2).upper(): str(a3).upper()
        for a2, a3 in zip(df["alpha-2"], df["alpha-3"])
        if isinstance(a2, str) and isinstance(a3, str)
    }


def valid_iso3() -> set[str]:
    """Set of real ISO 3166-1 alpha-3 codes (excludes World Bank aggregates like WLD)."""
    df = pd.read_csv(RAW, dtype=str)
    return {str(a3).upper() for a3 in df["alpha-3"] if isinstance(a3, str)}


# Common alternate country names used by non-ISO datasets (e.g. World Happiness Report).
_NAME_ALIASES = {
    "united states": "USA", "united states of america": "USA",
    "united kingdom": "GBR", "great britain": "GBR",
    "south korea": "KOR", "republic of korea": "KOR",
    "north korea": "PRK", "russia": "RUS", "czech republic": "CZE", "czechia": "CZE",
    "slovakia": "SVK", "ivory coast": "CIV", "cote divoire": "CIV",
    "trinidad tobago": "TTO", "swaziland": "SWZ", "eswatini": "SWZ",
    "palestinian territories": "PSE", "palestine": "PSE", "state of palestine": "PSE",
    "congo brazzaville": "COG", "congo kinshasa": "COD", "dr congo": "COD",
    "democratic republic of the congo": "COD", "republic of the congo": "COG",
    "laos": "LAO", "vietnam": "VNM", "syria": "SYR", "iran": "IRN",
    "bolivia": "BOL", "venezuela": "VEN", "tanzania": "TZA", "moldova": "MDA",
    "taiwan": "TWN", "taiwan province of china": "TWN", "hong kong": "HKG",
    "hong kong s a r of china": "HKG", "macedonia": "MKD", "north macedonia": "MKD",
    "turkey": "TUR", "turkiye": "TUR", "gambia": "GMB", "the gambia": "GMB",
    "brunei": "BRN", "cape verde": "CPV", "myanmar": "MMR", "burma": "MMR",
}


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z]", "", str(name).lower())


def name_to_iso3() -> dict[str, str]:
    """Map a normalized country name -> ISO3 (canonical ISO names + common aliases).

    Lets file-based datasets that key on country *name* (World Happiness Report, etc.)
    resolve to our iso3 identifier without a database.
    """
    df = pd.read_csv(RAW, dtype=str)
    out: dict[str, str] = {}
    for name, iso3, official in zip(df["name"], df["alpha-3"], df["name"]):
        if isinstance(iso3, str):
            out[_norm_name(name)] = iso3.upper()
    out.update({_norm_name(k): v for k, v in _NAME_ALIASES.items()})
    return out


def m49_to_iso3() -> dict[int, str]:
    """Map UN M49 numeric country code -> ISO3 (for FAOSTAT area codes)."""
    df = pd.read_csv(RAW, dtype=str)
    out: dict[int, str] = {}
    for code, iso3 in zip(df["country-code"], df["alpha-3"]):
        try:
            out[int(code)] = str(iso3).upper()
        except (TypeError, ValueError):
            continue
    return out
