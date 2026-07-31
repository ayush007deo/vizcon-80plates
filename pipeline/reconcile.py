"""Reconcile country labels from any source to a single ISO3 identifier (Req 16.7).

Given a reference table (iso3, name, region) and a set of alias overrides, map any
incoming country name to its iso3. Differing names for the same country collapse to
one profile. A fuzzy fallback resolves near-misses and flags low-confidence matches.
"""
from __future__ import annotations

import difflib
import re

# Common source-specific names that don't match the ISO reference exactly.
ALIASES: dict[str, str] = {
    "united states of america": "USA",
    "united states": "USA",
    "usa": "USA",
    "us": "USA",
    "u.s.": "USA",
    "russia": "RUS",
    "russian federation": "RUS",
    "south korea": "KOR",
    "korea, rep.": "KOR",
    "republic of korea": "KOR",
    "north korea": "PRK",
    "iran": "IRN",
    "iran, islamic rep.": "IRN",
    "vietnam": "VNM",
    "viet nam": "VNM",
    "bolivia": "BOL",
    "venezuela": "VEN",
    "tanzania": "TZA",
    "syria": "SYR",
    "laos": "LAO",
    "czech republic": "CZE",
    "czechia": "CZE",
    "uk": "GBR",
    "united kingdom": "GBR",
    "great britain": "GBR",
    "turkey": "TUR",
    "turkiye": "TUR",
    "egypt": "EGY",
    "egypt, arab rep.": "EGY",
    "ivory coast": "CIV",
    "cote d'ivoire": "CIV",
}


def _norm(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


class Reconciler:
    """Resolves country names to ISO3 using a reference table + aliases + fuzzy match."""

    def __init__(self, reference: list[dict], fuzzy_cutoff: float = 0.86):
        # reference rows: {"iso3":..., "name":..., "region":...}
        self.by_name: dict[str, str] = {}
        self.iso3_set: set[str] = set()
        self.region: dict[str, str] = {}
        for row in reference:
            iso3 = (row["iso3"] or "").upper()
            self.iso3_set.add(iso3)
            self.by_name[_norm(row["name"])] = iso3
            if row.get("region"):
                self.region[iso3] = row["region"]
        self._names = list(self.by_name.keys())
        self.fuzzy_cutoff = fuzzy_cutoff
        self.unresolved: list[str] = []
        self.low_confidence: list[tuple[str, str]] = []

    def resolve(self, name: str) -> str | None:
        """Return iso3 for a country name, or None if it cannot be resolved."""
        if not name:
            return None
        n = _norm(name)
        # Direct iso3 passthrough.
        if name.upper() in self.iso3_set:
            return name.upper()
        if n in ALIASES:
            return ALIASES[n]
        if n in self.by_name:
            return self.by_name[n]
        match = difflib.get_close_matches(n, self._names, n=1, cutoff=self.fuzzy_cutoff)
        if match:
            iso3 = self.by_name[match[0]]
            self.low_confidence.append((name, iso3))
            return iso3
        self.unresolved.append(name)
        return None
