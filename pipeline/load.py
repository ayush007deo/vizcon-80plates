"""Load stage: upserts into PostgreSQL (Req 16.2 — partial records retained).

Functions take normalized data and write it, keyed by iso3 / natural keys. Scalar
country fields are updated only when a non-null value is provided (COALESCE), so a
later source cannot erase an earlier value with NULL.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def upsert_country_base(engine: Engine, rows: pd.DataFrame) -> None:
    """Insert iso3/name/region base rows (from the ISO reference)."""
    with engine.begin() as conn:
        for _, r in rows.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO country_profile (iso3, name, region)
                    VALUES (:iso3, :name, :region)
                    ON CONFLICT (iso3) DO UPDATE
                        SET name = EXCLUDED.name,
                            region = COALESCE(country_profile.region, EXCLUDED.region)
                    """
                ),
                {"iso3": r["iso3"], "name": r["name"],
                 "region": (None if pd.isna(r["region"]) else r["region"])},
            )


def update_scalar(engine: Engine, iso3: str, field: str, value) -> None:
    """Update one scalar field only if the new value is non-null (COALESCE keeps old)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return
    # field is from a fixed allowlist controlled by the pipeline, not user input.
    allowed = {
        "life_expectancy", "population", "annual_tourists",
        "unesco_heritage_count", "nutrition_score", "tourism_receipts",
    }
    if field not in allowed:
        raise ValueError(f"Refusing to update unknown field {field!r}")
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE country_profile SET {field} = :v WHERE iso3 = :iso3"),
            {"v": value, "iso3": iso3},
        )


def fill_scalar_if_null(engine: Engine, iso3: str, field: str, value) -> None:
    """Set a scalar field only if it is currently NULL (curated gap-fill).

    Keeps higher-precedence public values already loaded (Req 16.8).
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return
    allowed = {"life_expectancy", "population", "annual_tourists",
               "unesco_heritage_count", "nutrition_score"}
    if field not in allowed:
        raise ValueError(f"Refusing to update unknown field {field!r}")
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE country_profile SET {field} = :v "
                 f"WHERE iso3 = :iso3 AND {field} IS NULL"),
            {"v": value, "iso3": iso3},
        )


def set_staple_foods(engine: Engine, iso3: str, foods: list[str]) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE country_profile SET staple_foods = :f WHERE iso3 = :iso3"),
            {"f": foods, "iso3": iso3},
        )


def reset_rebuilt_tables(engine: Engine) -> None:
    """Clear tables that are fully rebuilt each run so re-running is idempotent.

    Dishes/festivals/curated routes have no natural upsert key, so without this a
    re-run would duplicate them (e.g., a dish appearing multiple times).
    """
    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE dinner_symbolism, dish, festival, migration_step, migration_story, "
            "spice_step, spice_route, heritage_site, culinary_heritage "
            "RESTART IDENTITY CASCADE"
        ))


def load_culinary_heritage(engine: Engine, rows: pd.DataFrame) -> None:
    """Insert UNESCO culinary intangible-heritage rows (rebuilt each run)."""
    with engine.begin() as conn:
        for _, r in rows.iterrows():
            conn.execute(
                text(
                    "INSERT INTO culinary_heritage (element, year, link, iso3, country) "
                    "VALUES (:e, :y, :l, :iso3, :c)"
                ),
                {"e": r["element"], "y": (int(r["year"]) if pd.notna(r.get("year")) else None),
                 "l": r.get("link"), "iso3": r.get("iso3"), "c": r["country"]},
            )


def load_heritage_sites(engine: Engine, rows: pd.DataFrame) -> None:
    """Insert individual UNESCO heritage sites (rebuilt each run)."""
    with engine.begin() as conn:
        for _, r in rows.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO heritage_site
                        (name, iso3, country, category, region, latitude, longitude,
                         year_inscribed, in_danger)
                    VALUES (:name, :iso3, :country, :cat, :region, :lat, :lon, :yr, :danger)
                    """
                ),
                {"name": r["name"], "iso3": r.get("iso3"), "country": r["country"],
                 "cat": r.get("category"), "region": r.get("region"),
                 "lat": float(r["latitude"]), "lon": float(r["longitude"]),
                 "yr": (int(r["year_inscribed"]) if pd.notna(r.get("year_inscribed")) else None),
                 "danger": bool(r.get("in_danger", False))},
            )


def load_neighbors(engine: Engine, neighbors: dict[str, list[str]]) -> None:
    """Store land-border neighbor iso3 arrays on country_profile (Req 3.4)."""
    with engine.begin() as conn:
        for iso3, nbrs in neighbors.items():
            conn.execute(
                text("UPDATE country_profile SET neighbors = :n WHERE iso3 = :iso3"),
                {"n": nbrs, "iso3": iso3},
            )


def load_food_groups(engine: Engine, rows: pd.DataFrame) -> None:
    with engine.begin() as conn:
        for _, r in rows.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO country_food_group (iso3, food_group, pct)
                    VALUES (:iso3, :g, :pct)
                    ON CONFLICT (iso3, food_group) DO UPDATE SET pct = EXCLUDED.pct
                    """
                ),
                {"iso3": r["iso3"], "g": r["food_group"], "pct": float(r["pct"])},
            )


def load_dishes(engine: Engine, rows: pd.DataFrame) -> dict[tuple[str, str], int]:
    """Insert dishes; return {(iso3, dish_name): dish_id} for later linking."""
    ids: dict[tuple[str, str], int] = {}
    with engine.begin() as conn:
        for _, r in rows.iterrows():
            did = conn.execute(
                text(
                    """
                    INSERT INTO dish (iso3, name, course, taste_tags, ai_derived, ai_technique)
                    VALUES (:iso3, :name, :course, :tags, :ai, :tech)
                    RETURNING dish_id
                    """
                ),
                {"iso3": r["iso3"], "name": r["dish"], "course": r.get("course"),
                 "tags": list(r.get("taste_tags") or []),
                 "ai": bool(r.get("ai_derived", False)),
                 "tech": r.get("ai_technique")},
            ).scalar()
            ids[(r["iso3"], r["dish"])] = did
    return ids


def load_festivals(engine: Engine, rows: pd.DataFrame) -> None:
    with engine.begin() as conn:
        for _, r in rows.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO festival (iso3, name, month, traditional_foods)
                    VALUES (:iso3, :name, :month, :foods)
                    """
                ),
                {"iso3": r["iso3"], "name": r["festival"], "month": int(r["month"]),
                 "foods": list(r.get("foods") or [])},
            )


def load_similarity(engine: Engine, rows: list[dict]) -> None:
    with engine.begin() as conn:
        for r in rows:
            conn.execute(
                text(
                    """
                    INSERT INTO similarity (iso3_a, iso3_b, score, common_foods, unique_a, unique_b)
                    VALUES (:a, :b, :score, :common, :ua, :ub)
                    ON CONFLICT (iso3_a, iso3_b) DO UPDATE
                        SET score = EXCLUDED.score,
                            common_foods = EXCLUDED.common_foods,
                            unique_a = EXCLUDED.unique_a,
                            unique_b = EXCLUDED.unique_b
                    """
                ),
                {"a": r["iso3_a"], "b": r["iso3_b"], "score": r["score"],
                 "common": r["common_foods"], "ua": r["unique_a"], "ub": r["unique_b"]},
            )


def load_clusters(engine: Engine, assignments: pd.DataFrame, names: dict[int, str]) -> None:
    with engine.begin() as conn:
        cid_map: dict[int, int] = {}
        for raw_id, cname in names.items():
            cid = conn.execute(
                text(
                    """
                    INSERT INTO cuisine_cluster (cluster_name) VALUES (:n)
                    ON CONFLICT (cluster_name) DO UPDATE SET cluster_name = EXCLUDED.cluster_name
                    RETURNING cluster_id
                    """
                ),
                {"n": cname},
            ).scalar()
            cid_map[raw_id] = cid
        for _, r in assignments.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO country_cluster (iso3, cluster_id)
                    VALUES (:iso3, :cid)
                    ON CONFLICT (iso3) DO UPDATE SET cluster_id = EXCLUDED.cluster_id
                    """
                ),
                {"iso3": r["iso3"], "cid": cid_map[int(r["cluster_id"])]},
            )


def load_migration(engine: Engine, rows: pd.DataFrame) -> None:
    with engine.begin() as conn:
        for ingredient, grp in rows.groupby("ingredient"):
            sid = conn.execute(
                text(
                    """
                    INSERT INTO migration_story (ingredient) VALUES (:i)
                    ON CONFLICT (ingredient) DO UPDATE SET ingredient = EXCLUDED.ingredient
                    RETURNING story_id
                    """
                ),
                {"i": ingredient},
            ).scalar()
            conn.execute(text("DELETE FROM migration_step WHERE story_id = :s"), {"s": sid})
            for _, r in grp.iterrows():
                conn.execute(
                    text(
                        """
                        INSERT INTO migration_step (story_id, seq, location_name, lat, lon, time_period)
                        VALUES (:s, :seq, :loc, :lat, :lon, :tp)
                        """
                    ),
                    {"s": sid, "seq": int(r["seq"]), "loc": r["location_name"],
                     "lat": r["lat"], "lon": r["lon"], "tp": r["time_period"]},
                )


def load_spice_routes(engine: Engine, rows: pd.DataFrame) -> None:
    with engine.begin() as conn:
        for spice, grp in rows.groupby("spice"):
            rid = conn.execute(
                text(
                    """
                    INSERT INTO spice_route (spice) VALUES (:s)
                    ON CONFLICT (spice) DO UPDATE SET spice = EXCLUDED.spice
                    RETURNING route_id
                    """
                ),
                {"s": spice},
            ).scalar()
            conn.execute(text("DELETE FROM spice_step WHERE route_id = :r"), {"r": rid})
            for _, r in grp.iterrows():
                conn.execute(
                    text(
                        """
                        INSERT INTO spice_step (route_id, seq, location_name, lat, lon, time_period)
                        VALUES (:r, :seq, :loc, :lat, :lon, :tp)
                        """
                    ),
                    {"r": rid, "seq": int(r["seq"]), "loc": r["location_name"],
                     "lat": r["lat"], "lon": r["lon"], "tp": r["time_period"]},
                )


def load_dinner_symbolism(engine: Engine, rows: pd.DataFrame, dish_ids: dict[tuple[str, str], int]) -> None:
    # Map by dish name across any country that has it.
    name_to_id: dict[str, int] = {}
    for (iso3, name), did in dish_ids.items():
        name_to_id.setdefault(name, did)
    with engine.begin() as conn:
        for _, r in rows.iterrows():
            did = name_to_id.get(r["dish"])
            if did is None:
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO dinner_symbolism
                        (dish_id, symbolism, connecting_ingredients, trade_routes, cultural_values)
                    VALUES (:d, :sym, :ing, :routes, :vals)
                    ON CONFLICT (dish_id) DO UPDATE
                        SET symbolism = EXCLUDED.symbolism
                    """
                ),
                {"d": did, "sym": r["symbolism"],
                 "ing": list(r["connecting_ingredients"]),
                 "routes": list(r["trade_routes"]),
                 "vals": list(r["cultural_values"])},
            )
