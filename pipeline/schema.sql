-- Around the World in 80 Plates — PostgreSQL schema (Req 16.1, 16.2, 19.4, 21.2)
-- Countries are keyed by ISO 3166-1 alpha-3 (iso3), the consistent country identifier.
-- All create statements are idempotent (IF NOT EXISTS) so this file is safe to re-run.

-- ---------------------------------------------------------------------------
-- Sources & attribution (Req 16.6, 19.2, 19.4)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS source (
    source_id     SERIAL PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    reference_url TEXT,
    precedence    INTEGER NOT NULL DEFAULT 100  -- lower = higher priority in conflicts
);

CREATE TABLE IF NOT EXISTS section_source (
    section   TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    PRIMARY KEY (section, source_id)
);

CREATE TABLE IF NOT EXISTS load_log (
    load_id   SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES source(source_id) ON DELETE SET NULL,
    status    TEXT NOT NULL,               -- 'success' | 'failure'
    message   TEXT,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Country profile — one row per country (Req 16.1, 16.2)
-- Scalar fields are nullable; missing values render as placeholders in the app.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS country_profile (
    iso3                  CHAR(3) PRIMARY KEY,
    name                  TEXT NOT NULL,
    region                TEXT,
    unesco_heritage_count INTEGER,
    life_expectancy       NUMERIC,
    nutrition_score       NUMERIC,
    annual_tourists       BIGINT,
    population            BIGINT,
    staple_foods          TEXT[],
    neighbors             TEXT[]            -- iso3 codes of land-border neighbors (Req 3.4)
);
-- Tourism receipts (US$) from the world tourism-economy dataset (latest year).
-- NOTE: the interactive Travel dashboard reads the full time series straight from the
-- tourism CSV (data/tourism_data.py) — no table load — so only this scalar is stored.
ALTER TABLE country_profile ADD COLUMN IF NOT EXISTS tourism_receipts NUMERIC;

-- Plate composition: food-group supply proportions (Req 5)
CREATE TABLE IF NOT EXISTS country_food_group (
    iso3       CHAR(3) NOT NULL REFERENCES country_profile(iso3) ON DELETE CASCADE,
    food_group TEXT NOT NULL,
    pct        NUMERIC NOT NULL,           -- 0..100
    PRIMARY KEY (iso3, food_group)
);

-- Dishes (Req 4, 6, 12, 13). ai_* columns record AI-derived tags (Req 21.2).
CREATE TABLE IF NOT EXISTS dish (
    dish_id      SERIAL PRIMARY KEY,
    iso3         CHAR(3) REFERENCES country_profile(iso3) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    course       TEXT,                      -- starter | main | dessert | drink
    taste_tags   TEXT[],
    ai_derived   BOOLEAN NOT NULL DEFAULT FALSE,
    ai_technique TEXT
);
CREATE INDEX IF NOT EXISTS idx_dish_name_lower ON dish (lower(name));
CREATE INDEX IF NOT EXISTS idx_dish_iso3 ON dish (iso3);

-- Festivals by month (Req 9)
CREATE TABLE IF NOT EXISTS festival (
    festival_id       SERIAL PRIMARY KEY,
    iso3              CHAR(3) REFERENCES country_profile(iso3) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    month             INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    traditional_foods TEXT[]
);
CREATE INDEX IF NOT EXISTS idx_festival_month ON festival (month);

-- Precomputed cuisine similarity (Req 6). Stored one direction; accessor handles either order.
CREATE TABLE IF NOT EXISTS similarity (
    iso3_a       CHAR(3) NOT NULL REFERENCES country_profile(iso3) ON DELETE CASCADE,
    iso3_b       CHAR(3) NOT NULL REFERENCES country_profile(iso3) ON DELETE CASCADE,
    score        NUMERIC NOT NULL CHECK (score BETWEEN 0 AND 100),
    common_foods TEXT[],
    unique_a     TEXT[],
    unique_b     TEXT[],
    PRIMARY KEY (iso3_a, iso3_b)
);

-- Cuisine clusters for the flavor wheel (Req 11)
CREATE TABLE IF NOT EXISTS cuisine_cluster (
    cluster_id   SERIAL PRIMARY KEY,
    cluster_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS country_cluster (
    iso3       CHAR(3) PRIMARY KEY REFERENCES country_profile(iso3) ON DELETE CASCADE,
    cluster_id INTEGER NOT NULL REFERENCES cuisine_cluster(cluster_id) ON DELETE CASCADE
);

-- Food migration stories (Req 7) — curated
CREATE TABLE IF NOT EXISTS migration_story (
    story_id   SERIAL PRIMARY KEY,
    ingredient TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS migration_step (
    story_id      INTEGER NOT NULL REFERENCES migration_story(story_id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,
    location_name TEXT NOT NULL,
    lat           NUMERIC,
    lon           NUMERIC,
    time_period   TEXT,
    PRIMARY KEY (story_id, seq)
);

-- Spice routes across centuries (Req 8) — curated
CREATE TABLE IF NOT EXISTS spice_route (
    route_id SERIAL PRIMARY KEY,
    spice    TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS spice_step (
    route_id      INTEGER NOT NULL REFERENCES spice_route(route_id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,
    location_name TEXT NOT NULL,
    lat           NUMERIC,
    lon           NUMERIC,
    time_period   TEXT,
    PRIMARY KEY (route_id, seq)
);

-- Individual UNESCO World Heritage sites (WHC 2019, CC0) — for the sites map
CREATE TABLE IF NOT EXISTS heritage_site (
    site_id        SERIAL PRIMARY KEY,
    name           TEXT NOT NULL,
    iso3           CHAR(3),
    country        TEXT,
    category       TEXT,              -- Cultural | Natural | Mixed
    region         TEXT,
    latitude       NUMERIC,
    longitude      NUMERIC,
    year_inscribed INTEGER,
    in_danger      BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_heritage_site_iso3 ON heritage_site (iso3);

-- UNESCO Intangible Cultural Heritage — culinary/food traditions (CC BY 4.0)
CREATE TABLE IF NOT EXISTS culinary_heritage (
    id      SERIAL PRIMARY KEY,
    element TEXT NOT NULL,
    year    INTEGER,
    link    TEXT,
    iso3    CHAR(3),
    country TEXT
);
CREATE INDEX IF NOT EXISTS idx_culinary_iso3 ON culinary_heritage (iso3);

-- Global Dinner Party symbolism (Req 15) — curated
CREATE TABLE IF NOT EXISTS dinner_symbolism (
    dish_id               INTEGER PRIMARY KEY REFERENCES dish(dish_id) ON DELETE CASCADE,
    symbolism             TEXT,
    connecting_ingredients TEXT[],
    trade_routes          TEXT[],
    cultural_values       TEXT[]
);
