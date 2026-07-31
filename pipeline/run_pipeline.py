"""Pipeline orchestration: ingest -> reconcile -> derive -> load (Req 16).

Runs end to end and is safe to re-run. Public datasets (FAOSTAT, Kaggle, World Bank,
UNdata) require manual download into pipeline/raw/; if a file is absent the source is
logged as a failure and skipped, and the pipeline still produces a working database
from the ISO reference + curated data (Req 16.4).

Usage:
    python -m pipeline.run_pipeline
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine

from data.db import get_engine
from pipeline import curated, derive, load
from pipeline.ingest import borders, iso_reference, tabular
from pipeline.ingest.base import safe_ingest
from pipeline.reconcile import Reconciler
from pipeline.sources import seed_sources


def _build_food_sets(food_groups: pd.DataFrame, dishes: pd.DataFrame) -> dict[str, set[str]]:
    """Per-country food signal for similarity/clustering.

    Prefer FAOSTAT food groups; always fold in curated dish taste tags so curated-only
    countries still get a meaningful signal.
    """
    sets: dict[str, set[str]] = {}
    if not food_groups.empty:
        for iso3, grp in food_groups.groupby("iso3"):
            top = grp.sort_values("pct", ascending=False).head(6)["food_group"]
            sets.setdefault(iso3, set()).update(x.lower() for x in top)
    for iso3, grp in dishes.groupby("iso3"):
        tags: set[str] = set()
        for t in grp["taste_tags"]:
            tags.update(t or [])
        if tags:
            sets.setdefault(iso3, set()).update(tags)
    return {k: v for k, v in sets.items() if v}


def _proportions_from_sets(food_sets: dict[str, set[str]]) -> pd.DataFrame:
    """Build a proportions-like frame from food-signal sets for clustering."""
    rows = []
    for iso3, items in food_sets.items():
        if not items:
            continue
        pct = 100.0 / len(items)
        for item in items:
            rows.append({"iso3": iso3, "food_group": item, "pct": pct})
    return pd.DataFrame(rows, columns=["iso3", "food_group", "pct"])


def run() -> None:
    engine: Engine = get_engine()
    src_ids = seed_sources(engine)
    print("Seeded sources.")

    # --- Base country profiles from the ISO reference (works offline) ------
    iso_res = safe_ingest(engine, "ISO 3166 reference", iso_reference.ingest,
                          src_ids.get("ISO 3166 countries-with-regional-codes"))
    if not iso_res.ok or iso_res.data is None:
        raise RuntimeError(f"ISO reference is required but failed: {iso_res.message}")
    reference = iso_res.data
    load.upsert_country_base(engine, reference)
    reconciler = Reconciler(reference.to_dict("records"))
    print(f"Loaded {len(reference)} base country profiles.")

    # Clear fully-rebuilt tables so re-running the pipeline is idempotent
    # (prevents duplicate dishes/festivals/routes).
    load.reset_rebuilt_tables(engine)

    # Land-border neighbors (Req 3.4) — failure-isolated.
    borders_res = safe_ingest(engine, "Country borders", borders.ingest)
    if borders_res.ok and borders_res.data is not None:
        neighbors = borders.build_neighbors(borders_res.data, iso_reference.alpha2_to_iso3())
        load.load_neighbors(engine, neighbors)
        print(f"Loaded neighbors for {len(neighbors)} countries.")

    # --- Public sources (optional; failure-isolated) -----------------------
    public = {
        "FAOSTAT Food Balance Sheets": tabular.faostat_food_groups,
        "Kaggle countries-life-expectancy": tabular.life_expectancy,
        "Kaggle world-population-dataset": tabular.population,
        "World Bank ST.INT.ARVL": tabular.tourism,
        "UNdata World Heritage": tabular.unesco,
    }
    results = {name: safe_ingest(engine, name, fn, src_ids.get(name))
               for name, fn in public.items()}

    def _resolve_iso3(df: pd.DataFrame) -> pd.DataFrame:
        """Ensure an iso3 column: use it if present, else reconcile from country name."""
        out = df.copy()
        if "iso3" not in out.columns:
            out["iso3"] = out["country"].map(reconciler.resolve)
        else:
            out["iso3"] = out["iso3"].str.upper()
        return out.dropna(subset=["iso3"])

    # Food groups (FAOSTAT, keyed to iso3 via M49) -> normalized proportions.
    food_groups = pd.DataFrame(columns=["iso3", "food_group", "pct"])
    fao = results["FAOSTAT Food Balance Sheets"]
    if fao.ok and fao.data is not None and not fao.data.empty:
        raw = _resolve_iso3(fao.data)
        food_groups = derive.normalize_food_groups(raw[["iso3", "food_group", "quantity"]])
        load.load_food_groups(engine, food_groups)
        print(f"Loaded food groups from FAOSTAT for {food_groups['iso3'].nunique()} countries.")

    # NOTE: no curated numeric fallback — plate composition comes only from FAOSTAT
    # (a trusted source). Countries FAOSTAT does not cover show "unavailable".

    # Scalar fields from the simple country-level sources.
    scalar_sources = {
        "life_expectancy": results["Kaggle countries-life-expectancy"],
        "population": results["Kaggle world-population-dataset"],
        "annual_tourists": results["World Bank ST.INT.ARVL"],
        "unesco_heritage_count": results["UNdata World Heritage"],
    }
    for field, res in scalar_sources.items():
        if res.ok and res.data is not None and not res.data.empty:
            df = _resolve_iso3(res.data)
            # Keep one value per country (latest/first) to avoid duplicate updates.
            df = df.dropna(subset=[field]).drop_duplicates(subset=["iso3"])
            for _, r in df.iterrows():
                load.update_scalar(engine, r["iso3"], field, r[field])
            print(f"Applied {field} for {len(df)} countries.")

    # NOTE: no curated numeric fallback for life expectancy / population / tourists /
    # heritage — all come from trusted public sources (OWID, World Bank, UNESCO).

    # Individual UNESCO heritage sites (for the sites map) — reconciled to iso3.
    sites_res = safe_ingest(engine, "UNESCO heritage sites", tabular.heritage_sites,
                            src_ids.get("UNdata World Heritage"))
    if sites_res.ok and sites_res.data is not None and not sites_res.data.empty:
        sites = sites_res.data.copy()
        sites["iso3"] = sites["country"].map(reconciler.resolve)
        load.load_heritage_sites(engine, sites)
        print(f"Loaded {len(sites)} UNESCO heritage sites.")

    # World tourism-economy: refresh arrivals + add tourism receipts (food <-> travel).
    tour_res = safe_ingest(engine, "World tourism-economy dataset", tabular.tourism_economy,
                          src_ids.get("World Bank ST.INT.ARVL"))
    if tour_res.ok and tour_res.data is not None and not tour_res.data.empty:
        tdf = tour_res.data
        for _, r in tdf.iterrows():
            if pd.notna(r["annual_tourists"]):
                load.update_scalar(engine, r["iso3"], "annual_tourists", float(r["annual_tourists"]))
            if pd.notna(r["tourism_receipts"]):
                load.update_scalar(engine, r["iso3"], "tourism_receipts", float(r["tourism_receipts"]))
        print(f"Applied tourism arrivals + receipts for {len(tdf)} countries.")

    # NOTE: the full tourism time series (1999-2023) is NOT loaded into Postgres — the
    # Travel dashboard derives it directly from the CSV (data/tourism_data.py) for speed.

    # UNESCO Intangible Cultural Heritage — culinary/food traditions (culture -> food).
    ich_res = safe_ingest(engine, "UNESCO Intangible Cultural Heritage",
                          tabular.culinary_heritage,
                          src_ids.get("UNESCO Intangible Cultural Heritage"))
    if ich_res.ok and ich_res.data is not None and not ich_res.data.empty:
        ich = ich_res.data.copy()
        ich["iso3"] = ich["country"].map(reconciler.resolve)
        load.load_culinary_heritage(engine, ich)
        print(f"Loaded {len(ich)} culinary intangible-heritage rows "
              f"({ich['element'].nunique()} traditions).")

    # --- Curated dishes & content ------------------------------------------
    dishes = curated.famous_dishes()
    dish_ids = load.load_dishes(engine, dishes)
    print(f"Loaded {len(dishes)} curated dishes.")

    load.load_festivals(engine, curated.festivals())
    load.load_migration(engine, curated.migration())
    load.load_spice_routes(engine, curated.spice_routes())
    load.load_dinner_symbolism(engine, curated.dinner_symbolism(), dish_ids)
    print("Loaded curated festivals, migrations, spice routes, dinner symbolism.")

    # --- Derived: similarity, clusters, nutrition, staples -----------------
    food_sets = _build_food_sets(food_groups, dishes)
    if len(food_sets) >= 2:
        sim_rows = derive.compute_similarity({k: v for k, v in food_sets.items()})
        # Keep only pairs with some overlap to avoid a flood of zero-similarity rows.
        sim_rows = [r for r in sim_rows if r["score"] > 0]
        load.load_similarity(engine, sim_rows)
        print(f"Computed {len(sim_rows)} similarity pairs.")

        props = food_groups if not food_groups.empty else _proportions_from_sets(food_sets)
        props = props[props["iso3"].isin(food_sets)]
        assignments = derive.cluster_countries(props, k=min(6, max(2, len(food_sets) // 3)))
        names = derive.name_clusters(props, assignments)
        load.load_clusters(engine, assignments, names)
        print(f"Assigned {len(assignments)} countries to {len(names)} cuisine clusters.")

    # Nutrition score + staple foods from food groups when available.
    # Staples = top actual food groups, excluding pure calorie carriers (oils/sugar/fats).
    _NON_STAPLE = {"Oils", "Sugar", "Animal fats", "Fats"}
    if not food_groups.empty:
        for iso3, grp in food_groups.groupby("iso3"):
            pcts = dict(zip(grp["food_group"], grp["pct"]))
            load.update_scalar(engine, iso3, "nutrition_score", derive.nutrition_score(pcts))
            staple_rows = grp[~grp["food_group"].isin(_NON_STAPLE)]
            staples = staple_rows.sort_values("pct", ascending=False).head(4)["food_group"].tolist()
            load.set_staple_foods(engine, iso3, staples)

    _print_summary(engine)


def _print_summary(engine: Engine) -> None:
    from data.db import run_query

    log = run_query(
        "SELECT status, COUNT(*) AS n FROM load_log GROUP BY status ORDER BY status"
    )
    print("\n=== Load summary (load_log) ===")
    print(log.to_string(index=False))
    counts = run_query(
        """
        SELECT 'countries' AS entity, COUNT(*) AS n FROM country_profile
        UNION ALL SELECT 'with_region', COUNT(*) FROM country_profile WHERE region IS NOT NULL
        UNION ALL SELECT 'dishes', COUNT(*) FROM dish
        UNION ALL SELECT 'festivals', COUNT(*) FROM festival
        UNION ALL SELECT 'similarity_pairs', COUNT(*) FROM similarity
        UNION ALL SELECT 'clusters', COUNT(*) FROM cuisine_cluster
        UNION ALL SELECT 'migration_stories', COUNT(*) FROM migration_story
        UNION ALL SELECT 'spice_routes', COUNT(*) FROM spice_route
        """
    )
    print(counts.to_string(index=False))


if __name__ == "__main__":
    run()
