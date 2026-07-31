"""Central configuration for Around the World in 80 Plates.

Settings are read from environment variables (optionally loaded from a local .env)
so the same code runs locally and in deployment. Nothing here connects to the
database; see data/db.py for the engine.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Load a local .env if present (no hard dependency on python-dotenv).
# ---------------------------------------------------------------------------
def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


PROJECT_ROOT = Path(__file__).resolve().parent
_load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{PROJECT_ROOT / 'data' / 'plates.db'}",
)

# Cache time-to-live (seconds) for the read-only data-access layer.
CACHE_TTL: int = int(os.environ.get("CACHE_TTL", "3600"))

# App constants.
APP_TITLE = "Around the World in 80 Plates"
APP_TAGLINE = "Every meal tells a story. Every tradition leaves a footprint."

# The consistent country identifier used across the data layer.
COUNTRY_ID = "iso3"

# Journey order (Req 1.1, 17.1): introduction -> exploration -> culmination.
SECTION_ORDER = [
    "home",
    "explore_map",
    "country_story",
    "journeys",
    "traditions",
    "travel",
    "bigpicture",
    "taste_passport",
    "dinner_party",
    "sources",
]

# Taste preferences offered by the Taste Passport (Req 12.1).
TASTE_PREFERENCES = [
    "vegetarian",
    "street food",
    "seafood",
    "spicy",
    "sweet",
    "healthy",
]
