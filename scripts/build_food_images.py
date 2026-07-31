"""Curate appealing dish photos from the Kaggle food-recipe-images dataset (CC BY-SA 3.0).

Matches each curated dish name to a recipe image, copies the chosen image into
assets/food/<slug>.jpg, and writes assets/food/manifest.csv (slug -> file). The app
prefers these local images and falls back to Wikipedia for any dish not matched.

Usage (one-off, after downloading the Kaggle dataset):
    python scripts/build_food_images.py /path/to/kaggle_food_dir
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
CURATED_DISHES = REPO / "pipeline" / "curated" / "famous_dishes.csv"
OUT_DIR = REPO / "assets" / "food"

STOP = {"al", "the", "of", "a", "with", "and"}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _score(dish: str, title: str) -> tuple[int, int]:
    """Higher is better. Requires whole-token matches and a close title length so we
    avoid wrong dishes (e.g., 'Matcharita' for Matcha, 'Puff Pastry' for Puff Puff)."""
    d, t = dish.lower().strip(), str(title).lower().strip()
    if d == t:
        return (100, 0)
    d_tokens = [w for w in re.split(r"\W+", d) if w and w not in STOP]
    t_tokens = [w for w in re.split(r"\W+", t) if w and w not in STOP]
    d_set, t_set = set(d_tokens), set(t_tokens)
    if not d_tokens:
        return (0, 0)
    # Every dish token must appear as a WHOLE token in the title.
    if not d_set.issubset(t_set):
        return (0, 0)
    # And the title must not be much longer than the dish (keeps it the same dish).
    if len(t_tokens) > len(d_set) + 1:
        return (0, 0)
    # Prefer titles closest in length to the dish name.
    return (80, -len(t))


def main(kaggle_dir: str) -> None:
    kdir = Path(kaggle_dir)
    csv = next(kdir.glob("*.csv"))
    img_dir = kdir / "Food Images" / "Food Images"
    df = pd.read_csv(csv)
    df = df.dropna(subset=["Title", "Image_Name"])

    dishes = pd.read_csv(CURATED_DISHES)["dish"].unique().tolist()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    for dish in dishes:
        scored = df.assign(_s=df["Title"].map(lambda t: _score(dish, t)))
        scored = scored[scored["_s"].map(lambda s: s[0] >= 80)]  # exact/close matches only
        if scored.empty:
            continue
        best = scored.sort_values("_s", ascending=False).iloc[0]
        src = img_dir / f"{best['Image_Name']}.jpg"
        if not src.exists():
            continue
        dst = OUT_DIR / f"{slug(dish)}.jpg"
        shutil.copyfile(src, dst)
        manifest.append({"slug": slug(dish), "dish": dish, "file": dst.name,
                         "source_title": best["Title"]})

    pd.DataFrame(manifest).to_csv(OUT_DIR / "manifest.csv", index=False)
    print(f"Copied {len(manifest)} dish images to {OUT_DIR}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(REPO.parent / "data" / "_kaggle_food"))
