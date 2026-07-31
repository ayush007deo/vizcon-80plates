"""Derived data: plate proportions, cuisine similarity, clusters, nutrition, tags.

Pure functions over pandas/dicts so they are unit-testable without a database.
- normalize_food_groups: proportions per country sum to 100 (Req 5.3)
- compute_similarity: Jaccard over food sets, 0..100, symmetric, self=100 (Req 6)
- cluster_countries: one cluster per country (Req 11.3)
- nutrition_score / resolve_conflicts helpers
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd


# ---------------------------------------------------------------------------
# Plate proportions (Req 5.2, 5.3)
# ---------------------------------------------------------------------------
def normalize_food_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Scale each country's food-group quantities to percentages summing to 100.

    Input columns: iso3, food_group, quantity (any positive unit).
    Output columns: iso3, food_group, pct  (rounded to whole percents, sum == 100).
    """
    out = []
    for iso3, grp in df.groupby("iso3"):
        total = grp["quantity"].sum()
        if total <= 0:
            continue
        pct = (grp["quantity"] / total * 100).round()
        # Fix rounding drift so the integer percents sum to exactly 100.
        diff = int(100 - pct.sum())
        if diff != 0 and len(pct) > 0:
            idx = pct.idxmax()
            pct.loc[idx] += diff
        for fg, p in zip(grp["food_group"], pct):
            out.append({"iso3": iso3, "food_group": fg, "pct": float(p)})
    return pd.DataFrame(out, columns=["iso3", "food_group", "pct"])


# ---------------------------------------------------------------------------
# Similarity (Req 6.3, 6.4, 6.5, 6.7)
# ---------------------------------------------------------------------------
def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def compute_similarity(food_sets: dict[str, Iterable[str]]) -> list[dict]:
    """Pairwise similarity from each country's set of foods/ingredients.

    Returns rows {iso3_a, iso3_b, score, common_foods, unique_a, unique_b} for each
    unordered pair (a < b). score is 0..100. Self-pairs are handled by the accessor.
    """
    codes = sorted(food_sets)
    norm = {c: {str(x).strip().lower() for x in (food_sets[c] or [])} for c in codes}
    rows: list[dict] = []
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            sa, sb = norm[a], norm[b]
            score = round(_jaccard(sa, sb) * 100, 1)
            rows.append({
                "iso3_a": a,
                "iso3_b": b,
                "score": score,
                "common_foods": sorted(sa & sb),
                "unique_a": sorted(sa - sb),
                "unique_b": sorted(sb - sa),
            })
    return rows


# ---------------------------------------------------------------------------
# Clustering (Req 11.1, 11.3)
# ---------------------------------------------------------------------------
def cluster_countries(proportions: pd.DataFrame, k: int = 4, seed: int = 42) -> pd.DataFrame:
    """Cluster countries on their food-group proportion vectors.

    Input: iso3, food_group, pct. Output: iso3, cluster_id (exactly one per country).
    Falls back gracefully when scikit-learn is unavailable or samples < k.
    """
    wide = proportions.pivot_table(
        index="iso3", columns="food_group", values="pct", fill_value=0.0
    )
    if wide.empty:
        return pd.DataFrame(columns=["iso3", "cluster_id"])

    n = len(wide)
    k_eff = max(1, min(k, n))
    try:
        from sklearn.cluster import KMeans

        labels = KMeans(n_clusters=k_eff, random_state=seed, n_init=10).fit_predict(wide.values)
    except Exception:  # noqa: BLE001 - fallback without sklearn
        # Deterministic fallback: bucket by dominant food group.
        dominant = wide.idxmax(axis=1)
        codes = {name: i for i, name in enumerate(sorted(dominant.unique()))}
        labels = [codes[dominant.loc[iso3]] for iso3 in wide.index]

    return pd.DataFrame({"iso3": list(wide.index), "cluster_id": list(labels)})


def name_clusters(proportions: pd.DataFrame, assignments: pd.DataFrame) -> dict[int, str]:
    """Name each cluster from its most prominent food group."""
    merged = assignments.merge(proportions, on="iso3")
    names: dict[int, str] = {}
    for cid, grp in merged.groupby("cluster_id"):
        top = grp.groupby("food_group")["pct"].mean().idxmax()
        names[int(cid)] = f"{top}-forward"
    return names


# ---------------------------------------------------------------------------
# Nutrition score (Req 4.2) — computed, not sourced
# ---------------------------------------------------------------------------
def nutrition_score(food_pcts: dict[str, float]) -> float:
    """Simple 0..100 score: reward vegetables/fruit/pulses, penalize sugar/processed."""
    good = sum(food_pcts.get(g, 0.0) for g in ("Vegetables", "Fruits", "Pulses"))
    bad = sum(food_pcts.get(g, 0.0) for g in ("Sugar", "Processed", "Oils"))
    raw = 50 + good - bad
    return float(max(0.0, min(100.0, raw)))


# ---------------------------------------------------------------------------
# Conflict resolution (Req 16.8)
# ---------------------------------------------------------------------------
def resolve_conflicts(values: list[tuple[str, object, int]]):
    """Given (source_name, value, precedence) tuples for one field, pick the winner.

    Lower precedence number wins. None values are ignored. Returns the winning value
    (or None if all are None).
    """
    candidates = [(prec, val) for _, val, prec in values if val is not None]
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    return candidates[0][1]
