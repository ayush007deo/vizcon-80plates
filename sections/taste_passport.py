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
        st.session_state["journey_stage"] = "country"
        st.session_state["tp_opened"] = country
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

    # Taste preference cards (multi-select via toggle buttons)
    _TASTE_EMOJI = {"vegetarian": "🥬", "street food": "🍢", "seafood": "🐟",
                    "spicy": "🌶️", "sweet": "🍬", "healthy": "🥗"}
    
    st.markdown('<p style="color:#2A2320;font-weight:700;">I\'m in the mood for… <span style="color:#574B42;font-weight:400;font-size:0.85rem;">(select one or more)</span></p>', unsafe_allow_html=True)
    
    current_prefs = set(st.session_state.get("taste_prefs", set()))
    cols = st.columns(len(config.TASTE_PREFERENCES))
    for col, taste in zip(cols, config.TASTE_PREFERENCES):
        with col:
            is_selected = taste in current_prefs
            emoji = _TASTE_EMOJI.get(taste, "🍽️")
            btn_type = "primary" if is_selected else "secondary"
            label = f"{emoji} {taste}"
            if st.button(label, key=f"taste_{taste}", type=btn_type, use_container_width=True):
                if is_selected:
                    current_prefs.discard(taste)
                else:
                    current_prefs.add(taste)
                st.session_state["taste_prefs"] = current_prefs
                st.rerun()
    
    prefs = list(current_prefs)

    # No preferences submitted -> prompt
    if not prefs:
        st.markdown('<p style="color:#574B42;font-style:italic;">Pick at least one taste you love and we\'ll map your ideal food trip.</p>', unsafe_allow_html=True)
        return

    try:
        recs = repo.recommend_countries(tuple(prefs))
    except Exception:  # noqa: BLE001
        st.warning("Recommendations could not be loaded right now.")
        return

    # Nothing matches -> message (Req 12.5).
    if recs.empty:
        st.info("No countries matched those tastes. Try a different combination.")
        return

    # Heading (Req 12.6) and ranked poster wall (Req 12.2, 12.3).
    st.subheader("Your Culinary Passport")

    # Show feedback when a country is opened
    opened = st.session_state.pop("tp_opened", None)
    if opened:
        st.success(f"🌍 Exploring **{opened}**! Scroll up to the Country Story section to see its full profile.")

    st.caption(
        f"{len(recs)} destinations, ranked by how many of your {len(prefs)} tastes each "
        "matches. Click a poster to open its story."
    )

    prefs_t = tuple(prefs)
    per_row = 4
    max_rows = 2  # Show 2 rows initially
    rows = recs.reset_index(drop=True)
    
    # Pagination
    page = st.session_state.get("tp_page", 0)
    start_idx = page * (per_row * max_rows)
    end_idx = start_idx + (per_row * max_rows)
    visible = rows.iloc[start_idx:end_idx]
    
    for start in range(0, len(visible), per_row):
        chunk = visible.iloc[start:start + per_row]
        col_objs = st.columns(per_row)
        for j, (_, row) in enumerate(chunk.iterrows()):
            with col_objs[j]:
                _poster(start_idx + start + j + 1, row, prefs_t, len(prefs))

    # Show more / Show previous buttons
    total_pages = (len(rows) + per_row * max_rows - 1) // (per_row * max_rows)
    if total_pages > 1:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            col_prev, col_next = st.columns(2)
            with col_prev:
                if page > 0:
                    if st.button("← Previous", key="tp_prev"):
                        st.session_state["tp_page"] = page - 1
                        st.rerun()
            with col_next:
                if end_idx < len(rows):
                    if st.button(f"Show more →  ({len(rows) - end_idx} remaining)", key="tp_next"):
                        st.session_state["tp_page"] = page + 1
                        st.rerun()

