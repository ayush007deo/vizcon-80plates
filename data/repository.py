"""Typed, read-only accessors over the Data_Store (task 3.2).

Every function reads from PostgreSQL and returns plain pandas/dict structures.
When running inside Streamlit, results are memoized with st.cache_data; outside
Streamlit (tests, pipeline) the cache decorator degrades to a no-op wrapper so the
same functions are directly callable and testable.

Design notes:
- similarity is stored one direction; get_similarity handles either order and the
  self-pair (score 100) without requiring a row (Req 6.7).
- get_health_points returns only rows complete in vegetable supply, life expectancy,
  population, and region (Req 10.5).
- search_dishes uses a parameterized, case-insensitive substring match (Req 13.1-13.2).
"""
from __future__ import annotations

from typing import Any

import pandas as pd

import config
from data.db import run_query, ensure_list

# ---------------------------------------------------------------------------
# Cache shim: use st.cache_data when Streamlit is running, else a no-op.
# ---------------------------------------------------------------------------
import os

_TESTING = os.environ.get("ATW_TESTING") == "1"

try:  # pragma: no cover - exercised implicitly
    import streamlit as st

    def _cache(func):
        # Disable memoization under tests so results never leak across databases
        # (st.cache_data keys only on arguments, not on the active DB).
        return func if _TESTING else st.cache_data(ttl=config.CACHE_TTL)(func)
except Exception:  # noqa: BLE001 - Streamlit not present (pipeline scripts)

    def _cache(func):
        return func


# ---------------------------------------------------------------------------
# Countries
# ---------------------------------------------------------------------------
@_cache
def list_countries() -> pd.DataFrame:
    """All countries with a profile: iso3, name, region, has_profile flag."""
    return run_query(
        """
        SELECT iso3, name, region, TRUE AS has_profile
        FROM country_profile
        ORDER BY name
        """
    )


@_cache
def countries_for_map() -> pd.DataFrame:
    """All countries with region, neighbors, and a has_story flag.

    has_story is TRUE when the country has at least one dish or food-group row, i.e.
    there is a story to enter (drives selectable vs non-selectable on the map).
    """
    return run_query(
        """
        SELECT c.iso3, c.name, c.region, c.neighbors,
               EXISTS (SELECT 1 FROM dish d WHERE d.iso3 = c.iso3) AS has_story
        FROM country_profile c
        ORDER BY c.name
        """
    )


@_cache
def map_hover_stats() -> pd.DataFrame:
    """Per-country dish & festival counts for rich map hover previews."""
    return run_query(
        """
        SELECT c.iso3,
               (SELECT COUNT(*) FROM dish d WHERE d.iso3 = c.iso3)     AS dishes,
               (SELECT COUNT(*) FROM festival f WHERE f.iso3 = c.iso3) AS festivals
        FROM country_profile c
        """
    )


@_cache
def get_country_profile(iso3: str) -> dict[str, Any] | None:
    """Full profile for one country, or None if absent (Req 1.6, 4)."""
    df = run_query(
        """
        SELECT iso3, name, region, unesco_heritage_count, life_expectancy,
               nutrition_score, annual_tourists, population, staple_foods, neighbors
        FROM country_profile
        WHERE iso3 = :iso3
        """,
        {"iso3": iso3},
    )
    if df.empty:
        return None
    row = df.iloc[0].to_dict()
    row["staple_foods"] = ensure_list(row.get("staple_foods"))
    row["neighbors"] = ensure_list(row.get("neighbors"))
    row["dishes"] = get_dishes(iso3)["name"].tolist()
    row["festivals"] = _festival_names(iso3)
    return row


def _festival_names(iso3: str) -> list[str]:
    df = run_query(
        "SELECT name FROM festival WHERE iso3 = :iso3 ORDER BY month, name",
        {"iso3": iso3},
    )
    return df["name"].tolist()


@_cache
def get_dishes(iso3: str) -> pd.DataFrame:
    """Dishes for a country (Req 4.2)."""
    return run_query(
        """
        SELECT dish_id, name, course, taste_tags, ai_derived, ai_technique
        FROM dish
        WHERE iso3 = :iso3
        ORDER BY name
        """,
        {"iso3": iso3},
    )


# ---------------------------------------------------------------------------
# Plate composition (Req 5)
# ---------------------------------------------------------------------------
@_cache
def get_food_groups(iso3: str) -> pd.DataFrame:
    """Food-group supply proportions for a country, ordered largest first."""
    return run_query(
        """
        SELECT food_group, pct
        FROM country_food_group
        WHERE iso3 = :iso3
        ORDER BY pct DESC
        """,
        {"iso3": iso3},
    )


# ---------------------------------------------------------------------------
# Similarity (Req 6)
# ---------------------------------------------------------------------------
@_cache
def get_similarity(iso3_a: str, iso3_b: str) -> dict[str, Any]:
    """Similarity between two countries; handles either order and self-pairs."""
    if iso3_a == iso3_b:
        foods = get_food_groups(iso3_a)["food_group"].tolist()
        return {
            "score": 100.0,
            "common_foods": foods,
            "unique_a": [],
            "unique_b": [],
        }
    df = run_query(
        """
        SELECT iso3_a, iso3_b, score, common_foods, unique_a, unique_b
        FROM similarity
        WHERE (iso3_a = :a AND iso3_b = :b) OR (iso3_a = :b AND iso3_b = :a)
        LIMIT 1
        """,
        {"a": iso3_a, "b": iso3_b},
    )
    if df.empty:
        # No precomputed row: fall back to a food-group Jaccard so the score is
        # always defined in [0, 100] (Req 6.3) with meaningful common/unique lists.
        fa = set(get_food_groups(iso3_a)["food_group"])
        fb = set(get_food_groups(iso3_b)["food_group"])
        union = fa | fb
        score = round(len(fa & fb) / len(union) * 100, 1) if union else 0.0
        return {
            "score": score,
            "common_foods": sorted(fa & fb),
            "unique_a": sorted(fa - fb),
            "unique_b": sorted(fb - fa),
        }
    row = df.iloc[0]
    # Normalize orientation so unique_a always corresponds to the caller's iso3_a.
    if row["iso3_a"] == iso3_a:
        ua, ub = row["unique_a"], row["unique_b"]
    else:
        ua, ub = row["unique_b"], row["unique_a"]
    return {
        "score": float(row["score"]),
        "common_foods": ensure_list(row["common_foods"]),
        "unique_a": ensure_list(ua),
        "unique_b": ensure_list(ub),
    }


# ---------------------------------------------------------------------------
# Dish search (Req 13)
# ---------------------------------------------------------------------------
@_cache
def most_similar(iso3: str, n: int = 4) -> pd.DataFrame:
    """Countries with the most similar plate (the 'Who shares my plate?' feature)."""
    return run_query(
        """
        WITH pairs AS (
            SELECT CASE WHEN iso3_a = :i THEN iso3_b ELSE iso3_a END AS other,
                   score, common_foods
            FROM similarity
            WHERE iso3_a = :i OR iso3_b = :i
        )
        SELECT p.other AS iso3, c.name, c.region, p.score, p.common_foods
        FROM pairs p JOIN country_profile c ON c.iso3 = p.other
        ORDER BY p.score DESC, c.name
        LIMIT :n
        """,
        {"i": iso3, "n": n},
    )


@_cache
def taste_profile(iso3: str) -> pd.DataFrame:
    """A country's flavor fingerprint from its dishes' taste tags (tag, count)."""
    return run_query(
        """
        SELECT tag, COUNT(*) AS n
        FROM dish d, unnest(d.taste_tags) AS tag
        WHERE d.iso3 = :i
        GROUP BY tag
        ORDER BY n DESC, tag
        """,
        {"i": iso3},
    )


@_cache
def heritage_rank(iso3: str) -> dict[str, Any]:
    """World & regional rank for a country's UNESCO heritage count (story context)."""
    df = run_query(
        """
        SELECT iso3, region, unesco_heritage_count AS h,
               RANK() OVER (ORDER BY unesco_heritage_count DESC) AS world_rank,
               RANK() OVER (PARTITION BY region ORDER BY unesco_heritage_count DESC)
                   AS region_rank
        FROM country_profile
        WHERE unesco_heritage_count IS NOT NULL
        """
    )
    row = df[df["iso3"] == iso3]
    if row.empty:
        return {}
    r = row.iloc[0]
    return {"world_rank": int(r["world_rank"]), "region_rank": int(r["region_rank"]),
            "region": r["region"]}


@_cache
def search_dishes(text_query: str) -> pd.DataFrame:
    """Case-insensitive substring search on dish names with their countries."""
    q = (text_query or "").strip()
    if not q:
        return pd.DataFrame(columns=["dish", "iso3", "country"])
    return run_query(
        """
        SELECT d.name AS dish, c.iso3, c.name AS country
        FROM dish d
        JOIN country_profile c ON c.iso3 = d.iso3
        WHERE d.name ILIKE '%' || :q || '%'
        ORDER BY d.name, c.name
        """,
        {"q": q},
    )


# ---------------------------------------------------------------------------
# Health bubble chart (Req 10)
# ---------------------------------------------------------------------------
@_cache
def get_health_points(food_group: str = "Vegetables") -> pd.DataFrame:
    """Countries complete in a chosen food group's supply, life expectancy, pop, region."""
    return run_query(
        """
        SELECT c.iso3, c.name, c.region, c.life_expectancy, c.population,
               fg.pct AS supply
        FROM country_profile c
        JOIN country_food_group fg
          ON fg.iso3 = c.iso3 AND fg.food_group = :g
        WHERE c.life_expectancy IS NOT NULL
          AND c.population IS NOT NULL
          AND c.region IS NOT NULL
        ORDER BY c.name
        """,
        {"g": food_group},
    )


@_cache
def health_food_groups() -> list[str]:
    """Food groups with enough coverage to explore against life expectancy."""
    df = run_query(
        """
        SELECT fg.food_group, COUNT(*) AS n
        FROM country_food_group fg
        JOIN country_profile c ON c.iso3 = fg.iso3
        WHERE c.life_expectancy IS NOT NULL
        GROUP BY fg.food_group
        HAVING COUNT(*) >= 5
        """
    )
    avail = set(df["food_group"])
    # A focused, meaningful set for the explorer (skip oils/eggs/nuts clutter).
    preferred = ["Vegetables", "Fruits", "Meat", "Seafood", "Sugar", "Cereals", "Dairy"]
    return [g for g in preferred if g in avail]


@_cache
def diet_health_story(food_group: str = "Vegetables", n: int = 5) -> dict[str, Any]:
    """The culture-eats-longer story for one food group, ready for hero cards.

    Splits countries into the third that eat the MOST of this food vs the third that
    eat the LEAST, and returns their average life expectancy, the gap, the correlation,
    and the top/bottom country lists. Empty dict if there isn't enough data.
    """
    df = get_health_points(food_group).dropna(subset=["supply", "life_expectancy"])
    if len(df) < 6:
        return {}
    df = df.sort_values("supply")
    third = max(1, len(df) // 3)
    low, high = df.head(third), df.tail(third)
    cols = ["iso3", "name", "supply", "life_expectancy"]
    return {
        "food_group": food_group,
        "n": int(len(df)),
        "avg_share": float(df["supply"].mean()),
        "high_life": float(high["life_expectancy"].mean()),
        "low_life": float(low["life_expectancy"].mean()),
        "diff": float(high["life_expectancy"].mean() - low["life_expectancy"].mean()),
        "corr": float(df["supply"].corr(df["life_expectancy"]))
        if df["supply"].nunique() > 1 else None,
        "top": df.sort_values("supply", ascending=False).head(n)[cols].to_dict("records"),
        "bottom": df.sort_values("supply").head(n)[cols].to_dict("records"),
    }


@_cache
def healthiest_countries(n: int = 5) -> pd.DataFrame:
    """Countries with the most balanced plates (highest nutrition score)."""
    return run_query(
        """
        SELECT iso3, name, nutrition_score, life_expectancy
        FROM country_profile
        WHERE nutrition_score IS NOT NULL
        ORDER BY nutrition_score DESC, name
        LIMIT :n
        """,
        {"n": n},
    )


# ---------------------------------------------------------------------------
# Flavor wheel clusters (Req 11)
# ---------------------------------------------------------------------------
@_cache
def get_clusters() -> pd.DataFrame:
    """Each included country with its single cuisine cluster."""
    return run_query(
        """
        SELECT cc.iso3, c.name AS country, cl.cluster_name
        FROM country_cluster cc
        JOIN cuisine_cluster cl ON cl.cluster_id = cc.cluster_id
        JOIN country_profile c ON c.iso3 = cc.iso3
        ORDER BY cl.cluster_name, c.name
        """
    )


# ---------------------------------------------------------------------------
# Migration & spice routes (Req 7, 8)
# ---------------------------------------------------------------------------
@_cache
def list_migration_ingredients() -> list[str]:
    df = run_query("SELECT ingredient FROM migration_story ORDER BY ingredient")
    return df["ingredient"].tolist()


@_cache
def get_migration_story(ingredient: str) -> pd.DataFrame:
    """Ordered steps of an ingredient's journey (chronological)."""
    return run_query(
        """
        SELECT s.seq, s.location_name, s.lat, s.lon, s.time_period
        FROM migration_step s
        JOIN migration_story m ON m.story_id = s.story_id
        WHERE m.ingredient = :ingredient
        ORDER BY s.seq
        """,
        {"ingredient": ingredient},
    )


@_cache
def list_spices() -> list[str]:
    df = run_query("SELECT spice FROM spice_route ORDER BY spice")
    return df["spice"].tolist()


@_cache
def get_spice_route(spice: str) -> pd.DataFrame:
    """Ordered steps of a spice's route (earliest to latest)."""
    return run_query(
        """
        SELECT s.seq, s.location_name, s.lat, s.lon, s.time_period
        FROM spice_step s
        JOIN spice_route r ON r.route_id = s.route_id
        WHERE r.spice = :spice
        ORDER BY s.seq
        """,
        {"spice": spice},
    )


# ---------------------------------------------------------------------------
# Festivals (Req 9)
# ---------------------------------------------------------------------------
@_cache
def festival_counts_by_month() -> dict[int, int]:
    """Number of recorded festivals per month (1-12)."""
    df = run_query(
        "SELECT month, COUNT(*) AS n FROM festival GROUP BY month ORDER BY month"
    )
    return {int(r["month"]): int(r["n"]) for _, r in df.iterrows()}


@_cache
def get_festivals_by_month(month: int) -> pd.DataFrame:
    """Countries celebrating in a month, with foods and annual tourists."""
    return run_query(
        """
        SELECT f.name AS festival, c.iso3, c.name AS country,
               f.traditional_foods, c.annual_tourists
        FROM festival f
        JOIN country_profile c ON c.iso3 = f.iso3
        WHERE f.month = :month
        ORDER BY c.name
        """,
        {"month": month},
    )


# ---------------------------------------------------------------------------
# Taste passport recommendations (Req 12)
# ---------------------------------------------------------------------------
@_cache
def recommend_countries(prefs: tuple[str, ...]) -> pd.DataFrame:
    """Up to 10 countries ranked by number of selected preferences matched.

    A country matches a preference if any of its dishes carries that taste tag.
    """
    prefs = tuple(p for p in prefs if p)
    if not prefs:
        return pd.DataFrame(columns=["iso3", "country", "region", "match_count", "matched_tags"])
    return run_query(
        """
        SELECT c.iso3, c.name AS country, c.region,
               COUNT(DISTINCT tag) AS match_count,
               array_agg(DISTINCT tag ORDER BY tag) AS matched_tags
        FROM country_profile c
        JOIN dish d ON d.iso3 = c.iso3
        JOIN LATERAL unnest(d.taste_tags) AS tag ON TRUE
        WHERE tag = ANY(:prefs)
        GROUP BY c.iso3, c.name, c.region
        ORDER BY match_count DESC, c.name
        LIMIT 10
        """,
        {"prefs": list(prefs)},
    )


@_cache
def signature_dish_for(iso3: str, prefs: tuple[str, ...]) -> dict[str, Any] | None:
    """A representative dish for a country given the user's tastes.

    Prefers a main course whose taste tags overlap the preferences (the most
    'on-point' dish to show as the poster); falls back to any dish for the country.
    """
    prefs = tuple(p for p in prefs if p)
    df = run_query(
        """
        SELECT name, course, taste_tags,
               (SELECT COUNT(*) FROM unnest(taste_tags) AS t WHERE t = ANY(:prefs)) AS overlap
        FROM dish
        WHERE iso3 = :iso3
        ORDER BY overlap DESC, (course = 'main') DESC, name
        LIMIT 1
        """,
        {"iso3": iso3, "prefs": list(prefs)},
    )
    if df.empty:
        return None
    r = df.iloc[0]
    return {"dish": r["name"], "course": r["course"],
            "taste_tags": ensure_list(r["taste_tags"])}


# ---------------------------------------------------------------------------
# Global insights (Req 14)
# ---------------------------------------------------------------------------
@_cache
def heritage_points() -> pd.DataFrame:
    """Countries with a UNESCO heritage count (for the heritage map/ranking)."""
    return run_query(
        """
        SELECT iso3, name, region, unesco_heritage_count AS heritage,
               annual_tourists
        FROM country_profile
        WHERE unesco_heritage_count IS NOT NULL
        ORDER BY unesco_heritage_count DESC
        """
    )


@_cache
def heritage_site_points() -> pd.DataFrame:
    """Individual UNESCO sites with coordinates and category (for the sites map)."""
    return run_query(
        """
        SELECT name, iso3, country, category, region, latitude, longitude,
               year_inscribed, in_danger
        FROM heritage_site
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """
    )


@_cache
def heritage_category_counts() -> dict[str, int]:
    """Count of sites by category (Cultural / Natural / Mixed)."""
    df = run_query(
        "SELECT category, COUNT(*) AS n FROM heritage_site "
        "WHERE category IS NOT NULL GROUP BY category ORDER BY n DESC"
    )
    return {r["category"]: int(r["n"]) for _, r in df.iterrows()}


@_cache
def culinary_heritage() -> pd.DataFrame:
    """UNESCO culinary intangible-heritage traditions (element, year, link, countries)."""
    return run_query(
        """
        SELECT element, MIN(year) AS year, MIN(link) AS link,
               string_agg(DISTINCT country, ', ' ORDER BY country) AS countries
        FROM culinary_heritage
        GROUP BY element
        ORDER BY year, element
        """
    )


@_cache
def get_country_culinary(iso3: str) -> pd.DataFrame:
    """Culinary intangible-heritage traditions inscribed for a country."""
    return run_query(
        """
        SELECT element, year, link FROM culinary_heritage
        WHERE iso3 = :iso3 ORDER BY year, element
        """,
        {"iso3": iso3},
    )


# ---------------------------------------------------------------------------
# Food <-> travel connection (uses already-loaded scalar columns; the interactive
# Travel dashboard itself reads the tourism CSV directly via data.tourism_data)
# ---------------------------------------------------------------------------
@_cache
def food_travel_comparison() -> dict[str, Any]:
    """Compare tourism for countries WITH vs WITHOUT UNESCO culinary heritage.

    Culinary heritage = a country appears in the culinary_heritage table (its food
    traditions are UNESCO-inscribed). Returns average annual tourists and tourism
    receipts for each group, plus group sizes, so we can show that a living food
    culture goes hand in hand with drawing travelers. Metrics are averaged only over
    countries where the value exists.
    """
    df = run_query(
        """
        WITH tagged AS (
            SELECT c.iso3, c.annual_tourists, c.tourism_receipts,
                   EXISTS (SELECT 1 FROM culinary_heritage h WHERE h.iso3 = c.iso3)
                       AS has_food_heritage
            FROM country_profile c
        )
        SELECT has_food_heritage,
               COUNT(*)                                        AS n,
               AVG(annual_tourists)                            AS avg_tourists,
               COUNT(annual_tourists)                          AS tourists_n,
               AVG(tourism_receipts)                           AS avg_receipts,
               COUNT(tourism_receipts)                         AS receipts_n
        FROM tagged
        GROUP BY has_food_heritage
        """
    )
    out: dict[str, Any] = {"with": None, "without": None}
    for _, r in df.iterrows():
        key = "with" if r["has_food_heritage"] else "without"
        out[key] = {
            "n": int(r["n"]),
            "avg_tourists": float(r["avg_tourists"]) if pd.notna(r["avg_tourists"]) else None,
            "tourists_n": int(r["tourists_n"]),
            "avg_receipts": float(r["avg_receipts"]) if pd.notna(r["avg_receipts"]) else None,
            "receipts_n": int(r["receipts_n"]),
        }
    return out


@_cache
def top_food_destinations(limit: int = 8) -> pd.DataFrame:
    """Countries whose food traditions are UNESCO-inscribed, ranked by tourism receipts.

    Joins the culinary-heritage countries to their tourism economy so we can show the
    top food-and-travel destinations — where a celebrated cuisine meets real visitor
    spending. Includes how many culinary traditions each country carries.
    """
    return run_query(
        """
        SELECT c.iso3, c.name, c.region, c.annual_tourists, c.tourism_receipts,
               COUNT(DISTINCT h.element) AS culinary_traditions
        FROM country_profile c
        JOIN culinary_heritage h ON h.iso3 = c.iso3
        WHERE c.tourism_receipts IS NOT NULL
        GROUP BY c.iso3, c.name, c.region, c.annual_tourists, c.tourism_receipts
        ORDER BY c.tourism_receipts DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )


@_cache
def heritage_tourism_points() -> pd.DataFrame:
    """Countries complete in heritage, tourism, and region (culture-vs-tourism scatter)."""
    return run_query(
        """
        SELECT iso3, name, region, unesco_heritage_count AS heritage, annual_tourists
        FROM country_profile
        WHERE unesco_heritage_count IS NOT NULL
          AND annual_tourists IS NOT NULL
          AND region IS NOT NULL
        """
    )


@_cache
def landing_kpis() -> dict[str, int]:
    """Headline counts for the landing-page animated counters (all real, from the DB)."""
    df = run_query(
        """
        SELECT
            (SELECT COUNT(*) FROM country_profile)                       AS countries,
            (SELECT COUNT(*) FROM dish)                                  AS dishes,
            (SELECT COUNT(*) FROM heritage_site)                         AS heritage_sites,
            (SELECT COUNT(*) FROM festival)                              AS festivals,
            (SELECT COUNT(DISTINCT element) FROM culinary_heritage)      AS culinary,
            (SELECT COALESCE(SUM(annual_tourists),0) FROM country_profile) AS tourists
        """
    )
    r = df.iloc[0]
    return {k: int(r[k]) for k in
            ["countries", "dishes", "heritage_sites", "festivals", "culinary", "tourists"]}


@_cache
def get_insights() -> dict[str, Any]:
    """Aggregate findings, each computed only over countries where the metric exists."""
    df = run_query(
        """
        SELECT
            COUNT(*)                                          AS country_count,
            AVG(life_expectancy)                              AS avg_life_expectancy,
            COUNT(life_expectancy)                            AS life_n,
            SUM(annual_tourists)                              AS total_tourists,
            COUNT(annual_tourists)                            AS tourists_n
        FROM country_profile
        """
    )
    if df.empty or int(df.iloc[0]["country_count"]) == 0:
        return {"country_count": 0}
    row = df.iloc[0].to_dict()
    row["staple_foods"] = ensure_list(row.get("staple_foods"))
    row["neighbors"] = ensure_list(row.get("neighbors"))
    row["country_count"] = int(row["country_count"])

    # Country with the most UNESCO heritage sites (metric computed where available).
    heritage = run_query(
        """
        SELECT name, unesco_heritage_count AS v FROM country_profile
        WHERE unesco_heritage_count IS NOT NULL
        ORDER BY unesco_heritage_count DESC, name LIMIT 1
        """
    )
    if not heritage.empty:
        row["top_heritage_country"] = heritage.iloc[0]["name"]
        row["top_heritage_count"] = int(heritage.iloc[0]["v"])

    # Highest nutrition score.
    nutri = run_query(
        """
        SELECT name, nutrition_score AS v FROM country_profile
        WHERE nutrition_score IS NOT NULL
        ORDER BY nutrition_score DESC, name LIMIT 1
        """
    )
    if not nutri.empty:
        row["top_nutrition_country"] = nutri.iloc[0]["name"]
        row["top_nutrition_score"] = float(nutri.iloc[0]["v"])

    # Largest cuisine cluster.
    cluster = run_query(
        """
        SELECT cl.cluster_name AS name, COUNT(*) AS v
        FROM country_cluster cc JOIN cuisine_cluster cl ON cl.cluster_id = cc.cluster_id
        GROUP BY cl.cluster_name ORDER BY v DESC, cl.cluster_name LIMIT 1
        """
    )
    if not cluster.empty:
        row["biggest_cluster"] = cluster.iloc[0]["name"]
        row["biggest_cluster_size"] = int(cluster.iloc[0]["v"])

    return row


# ---------------------------------------------------------------------------
# Global Dinner Party (Req 15)
# ---------------------------------------------------------------------------
@_cache
def country_count() -> int:
    df = run_query("SELECT COUNT(*) AS n FROM country_profile")
    return int(df.iloc[0]["n"])


@_cache
def dish_countries() -> list[str]:
    """Countries that have at least one dish (the pool for the dinner party)."""
    return run_query("SELECT DISTINCT iso3 FROM dish ORDER BY iso3")["iso3"].tolist()


def get_dinner_symbolism(dish_id: int) -> dict[str, Any]:
    df = run_query(
        """
        SELECT symbolism, connecting_ingredients, trade_routes, cultural_values
        FROM dinner_symbolism WHERE dish_id = :d
        """,
        {"d": dish_id},
    )
    if df.empty:
        return {"symbolism": None, "connecting_ingredients": [],
                "trade_routes": [], "cultural_values": []}
    r = df.iloc[0]
    return {
        "symbolism": r["symbolism"],
        "connecting_ingredients": ensure_list(r["connecting_ingredients"]),
        "trade_routes": ensure_list(r["trade_routes"]),
        "cultural_values": ensure_list(r["cultural_values"]),
    }


def assemble_dinner(exclude: list[str] | None = None, seed: int | None = None) -> dict[str, Any]:
    """Assemble a 5-country dinner: a dish per course + a festival (Req 15).

    Picks five distinct dish-having countries (each with non-zero chance), assigns a
    starter/main/dessert/drink each from a distinct country, and a festival from the
    fifth. Retries so a new dinner differs from the previous set (Req 15.5).
    """
    import random

    rng = random.Random(seed)
    # Only countries with at least one dish that has symbolism, so the finale is full.
    pool = run_query(
        "SELECT DISTINCT d.iso3 FROM dish d JOIN dinner_symbolism s ON s.dish_id = d.dish_id"
    )["iso3"].tolist()
    if len(pool) < 5:
        return {"error": "fewer_than_five", "available": len(pool)}

    prev = set(exclude or [])
    pick = rng.sample(pool, 5)
    for _ in range(30):
        if not prev or set(pick) != prev:
            break
        pick = rng.sample(pool, 5)

    names = dict(zip(list_countries()["iso3"], list_countries()["name"]))
    used: set[str] = set()
    courses_out: list[dict[str, Any]] = []

    for course in ("starter", "main", "dessert", "drink"):
        assigned = None
        # Prefer a distinct country with a dish of exactly this course.
        for iso in pick:
            if iso in used:
                continue
            d = run_query(
                "SELECT d.dish_id, d.name FROM dish d "
                "JOIN dinner_symbolism s ON s.dish_id = d.dish_id "
                "WHERE d.iso3 = :i AND d.course = :c ORDER BY d.name LIMIT 1",
                {"i": iso, "c": course},
            )
            if not d.empty:
                assigned = (iso, int(d.iloc[0]["dish_id"]), d.iloc[0]["name"])
                break
        # Fallback: any symbolism-bearing dish from an unused country.
        if assigned is None:
            for iso in pick:
                if iso in used:
                    continue
                d = run_query(
                    "SELECT d.dish_id, d.name FROM dish d "
                    "JOIN dinner_symbolism s ON s.dish_id = d.dish_id "
                    "WHERE d.iso3 = :i ORDER BY d.name LIMIT 1",
                    {"i": iso},
                )
                if not d.empty:
                    assigned = (iso, int(d.iloc[0]["dish_id"]), d.iloc[0]["name"])
                    break
        if assigned:
            iso, did, dname = assigned
            used.add(iso)
            courses_out.append({
                "course": course, "iso3": iso, "country": names.get(iso, iso),
                "dish": dname, **get_dinner_symbolism(did),
            })

    # Festival from a remaining country (Req 15.2).
    festival = None
    for iso in pick:
        if iso in used:
            continue
        f = run_query(
            "SELECT name FROM festival WHERE iso3 = :i ORDER BY name LIMIT 1", {"i": iso}
        )
        used.add(iso)
        festival = {"iso3": iso, "country": names.get(iso, iso),
                    "festival": (f.iloc[0]["name"] if not f.empty else None)}
        break

    return {"error": None, "countries": pick, "courses": courses_out, "festival": festival}


def random_dinner(exclude: list[str] | None = None, seed: int | None = None) -> dict[str, Any]:
    """Pick 5 distinct countries and assign courses (Req 15.1, 15.2, 15.5).

    Returns {"countries": [...], "table": {course: iso3}} or {"error": ...} if
    fewer than 5 countries exist. If a previous set is supplied via `exclude`,
    retries to ensure the new set differs by at least one country.
    """
    import random

    rng = random.Random(seed)
    total = country_count()
    if total < 5:
        return {"error": "fewer_than_five", "available": total}

    countries = run_query("SELECT iso3 FROM country_profile")["iso3"].tolist()
    prev = set(exclude or [])

    for _ in range(20):
        pick = rng.sample(countries, 5)
        if not prev or set(pick) != prev:
            break

    courses = ["starter", "main", "dessert", "drink", "festival"]
    table = {course: iso3 for course, iso3 in zip(courses, pick)}
    return {"countries": pick, "table": table}
