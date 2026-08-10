"""Fetch iconic scenery / heritage photos per country for the story hero banner.

The country hero used to show a dish photo, which sometimes clashed with the
narration (e.g. Ethiopia's coffee story over a fried-food image). A landmark or
scenic/heritage image is always on-context for the country and far more evocative.

This one-off script downloads a CC-licensed image from Wikimedia for each curated
landmark and saves it to assets/country/<iso3>.jpg. The app then prefers that image
for the hero background. Run once; files are cached and committed.

Usage:
    python -m scripts.fetch_country_images
    python -m scripts.fetch_country_images --force
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "assets" / "country"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "AroundTheWorldIn80Plates/1.0 (VizCon2026 project)"}

# iso3 -> a scenery/heritage search term. Ethiopia uses its coffee ceremony so the
# hero also matches that country's narration; the rest are iconic landmarks.
LANDMARKS: dict[str, str] = {
    "IND": "Taj Mahal",
    "ITA": "Colosseum Rome",
    "JPN": "Mount Fuji Chureito Pagoda",
    "MEX": "Chichen Itza pyramid",
    "FRA": "Eiffel Tower Paris",
    "ESP": "Alhambra Granada",
    "CHN": "Great Wall of China Jinshanling",
    "THA": "Wat Arun Bangkok",
    "MAR": "Koutoubia Mosque Marrakesh",
    "BRA": "Christ the Redeemer Rio de Janeiro",
    "KOR": "Gyeongbokgung Palace Seoul",
    "ETH": "Ethiopian coffee ceremony",
    "GRC": "Santorini Oia",
    "VNM": "Ha Long Bay",
    "TUR": "Cappadocia hot air balloons",
    "PER": "Machu Picchu",
}


def _fetch(term: str, size: int = 1600, retries: int = 4) -> tuple[str, str] | None:
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
        time.sleep(1.5 * (attempt + 1))  # back off and retry (Wikipedia throttles bursts)
    return None


def _download(url: str, retries: int = 4) -> bytes | None:
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

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    credits: list[str] = []
    made = skipped = 0
    for iso3, term in LANDMARKS.items():
        out = OUT_DIR / f"{iso3}.jpg"
        if out.exists() and out.stat().st_size > 0 and not args.force:
            skipped += 1
            continue
        hit = _fetch(term)
        if not hit:
            print(f"  ✗ {iso3}: no image for '{term}'")
            time.sleep(1.0)
            continue
        url, page = hit
        content = _download(url)
        if not content:
            print(f"  ✗ {iso3}: download failed")
            time.sleep(1.0)
            continue
        out.write_bytes(content)
        made += 1
        credits.append(f"{iso3}: {term} — {page}")
        print(f"  ✓ {iso3}.jpg  ({len(content)//1024} KB)  [{term}]")
        time.sleep(1.0)  # be polite between countries

    # Write an attribution file for the Sources page / compliance.
    (OUT_DIR / "CREDITS.txt").write_text(
        "Country hero images — scenery/heritage via Wikimedia (CC BY-SA / public domain).\n"
        "Used with attribution for VizCon 2026.\n\n" + "\n".join(credits) + "\n"
    )
    print(f"\nDone. Downloaded {made}, skipped {skipped}. -> {OUT_DIR}")


if __name__ == "__main__":
    main()
