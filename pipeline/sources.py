"""Source registry: attribution, reference URLs, precedence, and section mapping.

Seeds the `source` and `section_source` tables (Req 16.6, 16.8, 19.2, 19.4).
Lower `precedence` wins when two sources disagree on the same field (Req 16.8).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

# name -> (reference_url, precedence)
SOURCES: dict[str, tuple[str, int]] = {
    "FAOSTAT Food Balance Sheets": ("https://www.fao.org/faostat/en/#data", 10),
    "Kaggle countries-life-expectancy": (
        "https://www.kaggle.com/datasets/brendan45774/countries-life-expectancy", 20),
    "Kaggle world-population-dataset": (
        "https://www.kaggle.com/datasets/iamsouravbanerjee/world-population-dataset", 20),
    "World Bank ST.INT.ARVL": (
        "https://data.worldbank.org/indicator/ST.INT.ARVL", 20),
    "Kaggle tourism-and-economic-impact": (
        "https://www.kaggle.com/datasets/bushraqurban/tourism-and-economic-impact", 30),
    "Kaggle What's Cooking": ("https://www.kaggle.com/c/whats-cooking/data", 20),
    "UNdata World Heritage": ("https://data.un.org/", 20),
    "UNESCO Intangible Cultural Heritage": ("https://ich.unesco.org/en/lists", 20),
    "ISO 3166 countries-with-regional-codes": (
        "https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes", 5),
    "Curated dataset": ("https://github.com/vizcon-2026-team1/pipeline/curated", 50),
    "FAOSTAT Global spice consumption": ("https://www.fao.org/faostat/en/#data", 15),
    "World Happiness Report": (
        "https://www.kaggle.com/datasets/unsdsn/world-happiness", 20),
}

# app section -> list of source names it draws from (Req 19.1)
SECTION_SOURCES: dict[str, list[str]] = {
    "country_story": ["FAOSTAT Food Balance Sheets", "UNESCO Intangible Cultural Heritage",
                      "UNdata World Heritage", "Kaggle countries-life-expectancy",
                      "World Bank ST.INT.ARVL", "Curated dataset"],
    "plate": ["FAOSTAT Food Balance Sheets"],
    "similarity": ["Kaggle What's Cooking", "FAOSTAT Food Balance Sheets"],
    "health": ["FAOSTAT Food Balance Sheets", "Kaggle countries-life-expectancy",
               "Kaggle world-population-dataset"],
    "flavor_wheel": ["FAOSTAT Food Balance Sheets", "Kaggle What's Cooking"],
    "taste_passport": ["Kaggle What's Cooking", "Curated dataset"],
    "dish_search": ["Kaggle What's Cooking", "Curated dataset"],
    "festivals": ["Curated dataset", "World Bank ST.INT.ARVL"],
    "heritage": ["UNdata World Heritage", "World Bank ST.INT.ARVL",
                 "UNESCO Intangible Cultural Heritage"],
    "traditions": ["Curated dataset", "UNESCO Intangible Cultural Heritage",
                   "UNdata World Heritage"],
    "travel": ["Kaggle tourism-and-economic-impact", "World Bank ST.INT.ARVL",
               "UNESCO Intangible Cultural Heritage"],
    "migration": ["Curated dataset"],
    "spice_journey": ["Curated dataset", "FAOSTAT Global spice consumption"],
    "happiness": ["World Happiness Report", "Curated dataset"],
    "dinner_party": ["Curated dataset"],
    "insights": ["FAOSTAT Food Balance Sheets", "Kaggle countries-life-expectancy",
                 "World Bank ST.INT.ARVL", "UNdata World Heritage"],
}


def seed_sources(engine: Engine) -> dict[str, int]:
    """Upsert sources and section mappings; return name -> source_id."""
    ids: dict[str, int] = {}
    with engine.begin() as conn:
        for name, (url, precedence) in SOURCES.items():
            sid = conn.execute(
                text(
                    """
                    INSERT INTO source (name, reference_url, precedence)
                    VALUES (:n, :u, :p)
                    ON CONFLICT (name) DO UPDATE
                        SET reference_url = EXCLUDED.reference_url,
                            precedence = EXCLUDED.precedence
                    RETURNING source_id
                    """
                ),
                {"n": name, "u": url, "p": precedence},
            ).scalar()
            ids[name] = sid

        for section, names in SECTION_SOURCES.items():
            for name in names:
                conn.execute(
                    text(
                        """
                        INSERT INTO section_source (section, source_id)
                        VALUES (:s, :sid) ON CONFLICT DO NOTHING
                        """
                    ),
                    {"s": section, "sid": ids[name]},
                )
    return ids


def precedence_of(name: str) -> int:
    return SOURCES.get(name, ("", 100))[1]
