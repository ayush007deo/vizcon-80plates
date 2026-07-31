"""Land-border adjacency (Req 3.4). Reads the GeoDataSource country-borders CSV.

The file uses ISO 3166-1 alpha-2 codes; build_neighbors maps them to alpha-3 using
the ISO reference so neighbors can be stored on country_profile.neighbors (iso3[]).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "raw" / "country_borders.csv"


def ingest() -> pd.DataFrame:
    if not RAW.exists():
        raise FileNotFoundError(f"Missing borders file: {RAW}")
    df = pd.read_csv(RAW)
    return df[["country_code", "country_border_code"]].dropna(subset=["country_code"])


def build_neighbors(borders: pd.DataFrame, alpha2_to_iso3: dict[str, str]) -> dict[str, list[str]]:
    """Return iso3 -> sorted list of neighbor iso3 codes."""
    neighbors: dict[str, set[str]] = {}
    for _, r in borders.iterrows():
        a = alpha2_to_iso3.get(str(r["country_code"]).upper())
        b = alpha2_to_iso3.get(str(r["country_border_code"]).upper()) \
            if pd.notna(r["country_border_code"]) else None
        if not a:
            continue
        neighbors.setdefault(a, set())
        if b:
            neighbors[a].add(b)
    return {k: sorted(v) for k, v in neighbors.items()}
