"""Taste_Passport — Netflix-style country recommendations by taste (Req 12).

Pick the flavors you love and get back a poster wall of countries to explore, each
with a signature-dish photo, the tastes it matches, and a data-derived "why you'll
love it" line. Click a poster to jump straight into that country's food story.
"""
from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

import config
from components import cards, citation, lottie
from components.flags import flag
from components.navigation import go_to
from data import repository as repo


def _poster_src(country: str, dish: str | None) -> str | None:
    """A CSS-usable image src for a country's signature dish (data URI or URL)."""
    from components.images import get_food_image

    terms = [t for t in (dish, f"{country} cuisine", country) if t]
    if not terms:
        return None
    img = get_food_image(*terms)
    if not img:
        return None
    src = img[0]
    if src.startswith("http"):
        return src
    try:
        data = Path(src).read_bytes()
        return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
    except Exception:  # noqa: BLE001
        return None


def _why_line(country: str, tags: list[str], dish: str | None) -> str:
    """A short, data-derived 'why you'll love it' sentence."""
    pretty = [t for t in tags if t]
    if len(pretty) >= 2:
        taste = f"<b>{html.escape(pretty[0])}</b> and <b>{html.escape(pretty[1])}</b> flavors"
    elif pretty:
        taste = f"<b>{html.escape(pretty[0])}</b> flavors"
    else:
        taste = "flavors you love"
    start = f" Start with {html.escape(dish)}." if dish else ""
    return f"You'll love {html.escape(country)} for its {taste}.{start}"


def _poster(rank: int, row, prefs: tuple[str, ...], total: int) -> None:
    """Render one Netflix-style poster + an 'open story' button."""
    iso3 = row["iso3"]
    country = row["country"]
    matched = list(row.get("matched_tags") or [])
    sig = repo.signature_dish_for(iso3, prefs)
    dish = sig["dish"] if sig else None

    src = _poster_src(country, dish)
    bg_style = f'style="background-image:url(\'{src}\');"' if src else ""
    fallback = "" if src else '<div class="tp-fallback">🍽️</div>'
    chips = "".join(f'<span class="tp-chip">{html.escape(t)}</span>' for t in matched[:3])
    why = _why_line(country, matched, dish)

    st.markdown(
        f'<div class="tp-poster" {bg_style}>{fallback}'
        f'<div class="tp-overlay"></div>'
        f'<div class="tp-rank">{rank}</div>'
        f'<div class="tp-match">matches {int(row["match_count"])}/{total}</div>'
        f'<div class="tp-body"><div class="tp-flag">{flag(iso3)}</div>'
        f'<div class="tp-name">{html.escape(country)}</div>'
        f'<div class="tp-chips">{chips}</div>'
        f'<div class="tp-why">{why}</div></div></div>',
        unsafe_allow_html=True,
    )
    if st.button(f"Open {country}  →", key=f"tp_open_{iso3}", width="stretch"):
        st.session_state["selected_country"] = iso3
        st.rerun()


def render() -> None:
    cards.page_header("taste_passport")

    # Personalized recommendation prompt — engaging and clear
    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#FFFFFF,#FFF8F1);border:1px solid #EFE6D8;
            border-radius:16px;padding:24px;margin:8px 0 16px 0;box-shadow:0 4px 16px rgba(43,33,24,0.06);">
            <div style="font-size:1.4rem;margin-bottom:4px;">🛂✨</div>
            <div style="font-weight:800;font-size:1.1rem;color:#2A2320;">Build your taste passport</div>
            <div style="color:#574B42;font-size:0.9rem;margin-top:4px;">
                Select the flavors you love below and we'll recommend countries whose cuisines match your cravings.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Multi-select of taste preferences (Req 12.1).
    st.markdown('<p style="color:#2A2320;font-weight:700;">I\'m in the mood for…</p>', unsafe_allow_html=True)
    prefs = st.multiselect(
        "Taste preferences",
        options=config.TASTE_PREFERENCES,
        default=list(st.session_state.get("taste_prefs", set())),
        label_visibility="collapsed",
    )
    st.session_state["taste_prefs"] = set(prefs)

    # No preferences submitted -> prompt, no list (Req 12.4).
    if not prefs:
        st.markdown('<p style="color:#574B42;font-style:italic;">Pick at least one taste you love and we\'ll map your ideal food trip.</p>', unsafe_allow_html=True)
        citation.cite("taste_passport")
        return

    try:
        recs = repo.recommend_countries(tuple(prefs))
    except Exception:  # noqa: BLE001
        st.warning("Recommendations could not be loaded right now.")
        return

    # Nothing matches -> message (Req 12.5).
    if recs.empty:
        st.info("No countries matched those tastes. Try a different combination.")
        citation.cite("taste_passport")
        return

    # Heading (Req 12.6) and ranked poster wall (Req 12.2, 12.3).
    st.subheader("Your Culinary Passport")
    st.caption(
        f"{len(recs)} destinations, ranked by how many of your {len(prefs)} tastes each "
        "matches. Click a poster to open its story."
    )

    prefs_t = tuple(prefs)
    per_row = 4
    rows = recs.reset_index(drop=True)
    for start in range(0, len(rows), per_row):
        chunk = rows.iloc[start:start + per_row]
        col_objs = st.columns(per_row)
        for j, (_, row) in enumerate(chunk.iterrows()):
            with col_objs[j]:
                _poster(start + j + 1, row, prefs_t, len(prefs))

    citation.cite("taste_passport")
