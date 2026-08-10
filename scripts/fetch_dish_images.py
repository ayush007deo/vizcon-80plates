"""Fill in missing dish photos from Wikimedia (open source, CC-licensed).

Finds every dish in the database that has no local image under assets/food/ and
downloads a representative photo from Wikimedia, saving it as assets/food/<slug>.jpg
(the same slug scheme components.images._local_image already resolves). Idempotent:
dishes that already have a local image are skipped.

Usage:
    python -m scripts.fetch_dish_images
    python -m scripts.fetch_dish_images --force   # refetch even if present
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import requests

from components.images import _local_image, _slug
from data.db import run_query

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FOOD_DIR = PROJECT_ROOT / "assets" / "food"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "AroundTheWorldIn80Plates/1.0 (VizCon2026 project)"}


def _fetch(term: str, size: int = 1000, retries: int = 4):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": term, "gsrlimit": 1, "prop": "pageimages|info",
        "inprop": "url", "piprop": "thumbnail", "pithumbsize": size, "redirects": 1,
    }
    for attempt in range(retries):
        try:
            r = requests.get(API, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                pages = (r.json().get("query") or {}).get("pages") or {}
                for page in pages.values():
                    thumb = (page.get("thumbnail") or {}).get("source")
                    if thumb:
                        return thumb, page.get("fullurl", "")
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def _download(url: str, retries: int = 4):
    for attempt in range(retries):
        try:
            img = requests.get(url, headers=HEADERS, timeout=25)
            if img.status_code == 200 and img.content:
                return img.content
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    dishes = run_query("SELECT DISTINCT name FROM dish ORDER BY name")["name"].tolist()
    missing = dishes if args.force else [d for d in dishes if not _local_image(d)]
    print(f"{len(missing)} dish image(s) to fetch.")

    credits: list[str] = []
    made = 0
    for dish in missing:
        out = FOOD_DIR / f"{_slug(dish)}.jpg"
        # Try a couple of query phrasings for a better hit.
        hit = _fetch(f"{dish} dish") or _fetch(f"{dish} food") or _fetch(dish)
        if not hit:
            print(f"  ✗ {dish}: no image found")
            time.sleep(1.0)
            continue
        url, page = hit
        content = _download(url)
        if not content:
            print(f"  ✗ {dish}: download failed")
            time.sleep(1.0)
            continue
        out.write_bytes(content)
        made += 1
        credits.append(f"{dish}: {page}")
        print(f"  ✓ {out.name}  ({len(content)//1024} KB)")
        time.sleep(1.0)

    if credits:
        creditfile = FOOD_DIR / "WIKIMEDIA_CREDITS.txt"
        existing = creditfile.read_text() if creditfile.exists() else ""
        creditfile.write_text(existing + "\n".join(credits) + "\n")
    print(f"\nDone. Downloaded {made} of {len(missing)}. -> {FOOD_DIR}")


if __name__ == "__main__":
    main()
