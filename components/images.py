"""Dish imagery: curated Kaggle food photos first, Wikipedia as fallback.

get_food_image(query, *fallbacks) returns (image_src, credit_markdown) or None.
- image_src is a local file path (curated Kaggle images under assets/food/) or a
  Wikipedia thumbnail URL.
- credit_markdown is a ready-to-render attribution string.
Fetches are skipped under tests; network failures degrade to None.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

_API = "https://en.wikipedia.org/w/api.php"
_HEADERS = {"User-Agent": "AroundTheWorldIn80Plates/1.0 (VizCon2026 project)"}

_FOOD_DIR = Path(__file__).resolve().parents[1] / "assets" / "food"
_KAGGLE_CREDIT = "Food photo: Epicurious recipe dataset via Kaggle · CC BY-SA 3.0"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


@lru_cache(maxsize=1)
def _manifest() -> dict[str, str]:
    """slug -> absolute image path for curated Kaggle dish photos."""
    manifest = _FOOD_DIR / "manifest.csv"
    if not manifest.exists():
        return {}
    import csv

    out: dict[str, str] = {}
    with manifest.open() as f:
        for row in csv.DictReader(f):
            path = _FOOD_DIR / row["file"]
            if path.exists():
                out[row["slug"]] = str(path)
    return out


def _local_image(query: str) -> str | None:
    slug = _slug(query)
    # 1) Manifest (auto-matched Kaggle photos).
    hit = _manifest().get(slug)
    if hit:
        return hit
    # 2) Any hand-dropped file named <slug>.<ext> in assets/food/ — no manifest needed.
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = _FOOD_DIR / f"{slug}{ext}"
        if p.exists() and p.stat().st_size > 0:
            return str(p)
    return None


def _cache(func):
    try:
        import streamlit as st

        if os.environ.get("ATW_TESTING") == "1":
            return func
        return st.cache_data(ttl=86400, show_spinner=False)(func)
    except Exception:  # noqa: BLE001
        return func


def _search_wikipedia(term: str):
    import requests

    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": term, "gsrlimit": 1, "prop": "pageimages|info",
        "inprop": "url", "piprop": "thumbnail", "pithumbsize": 800, "redirects": 1,
    }
    r = requests.get(_API, params=params, headers=_HEADERS, timeout=5)
    if r.status_code != 200:
        return None
    pages = (r.json().get("query") or {}).get("pages") or {}
    for page in pages.values():
        thumb = (page.get("thumbnail") or {}).get("source")
        if thumb:
            return thumb, page.get("fullurl", "")
    return None


@_cache
def get_food_image(query: str, *fallbacks: str) -> tuple[str, str] | None:
    """Return (image_src, credit_markdown). Local Kaggle photo first, else Wikipedia."""
    if os.environ.get("ATW_TESTING") == "1":
        return None

    # 1) Curated Kaggle image for the primary dish name.
    local = _local_image(query)
    if local:
        return local, _KAGGLE_CREDIT

    # 2) Wikipedia fallback across the candidate terms.
    for term in [t for t in ([query] + list(fallbacks)) if t and t.strip()]:
        try:
            hit = _search_wikipedia(term)
        except Exception:  # noqa: BLE001
            hit = None
        if hit:
            thumb, page = hit
            credit = f"Image: [Wikipedia]({page}) · CC BY-SA" if page else "Image: Wikipedia · CC BY-SA"
            return thumb, credit
    return None
