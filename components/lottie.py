"""Lottie animation slots (local-first, reliable, license-free).

show(key) renders assets/lottie/<key>.json if present via streamlit-lottie. Drop a
free LottieFiles JSON at that path and it appears automatically — no code change.
Skipped under tests and degrades silently if the component/file is unavailable.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1] / "assets" / "lottie"


@lru_cache(maxsize=None)
def _load(key: str):
    path = _DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:  # noqa: BLE001
        return None


def show(key: str, height: int = 150, speed: float = 1.0) -> bool:
    """Render the animation for `key` if available. Returns True if rendered."""
    if os.environ.get("ATW_TESTING") == "1":
        return False
    data = _load(key)
    if data is None:
        return False
    try:
        from streamlit_lottie import st_lottie

        st_lottie(data, height=height, speed=speed, key=f"lottie_{key}")
        return True
    except Exception:  # noqa: BLE001
        return False
