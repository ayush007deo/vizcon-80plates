"""Home_Page — video hero, narrative intro, animated KPIs, curiosity hooks (Req 2)."""
from __future__ import annotations

import streamlit as st

import config
from components import cards, citation
from components.navigation import go_to
from data import repository as repo


def _curiosity_facts() -> list[tuple[str, str, str]]:
    """Surprising facts, derived from the migration data where possible."""
    facts = [
        ("🍅", "Italy had no tomatoes until the 1500s", "They're native to the Andes."),
        ("🌶️", "Chili reached Asia only ~500 years ago", "Before that, no spicy curries."),
        ("☕", "Coffee began in Ethiopia", "and now wakes up the whole planet."),
    ]
    try:
        n = repo.country_count()
        facts[2] = ("🌍", f"{n} countries, one table", "Explore how the world eats.")
    except Exception:  # noqa: BLE001
        pass
    return facts


# Curiosity hooks: (emoji, title, teaser, destination section).
_TEASERS = [
    ("🍅", "Pizza owes it all to Peru", "Follow the tomato from the Andes to Naples.", "journeys"),
    ("🏛", "Do travelers follow culture?", "See how heritage pulls tourism.", "traditions"),
    ("🍽️", "Throw a Global Dinner Party", "Five random nations, one surprise table.", "dinner_party"),
    ("🧭", "Get your Taste Passport", "Tell us what you crave; we'll map your trip.", "taste_passport"),
]


def _open_random_country() -> None:
    """Pick a random country that has a food story and set it as selected."""
    import random

    try:
        options = repo.dish_countries()
    except Exception:  # noqa: BLE001
        options = []
    if options:
        pick = random.choice(options)
        st.session_state["selected_country"] = pick
        st.session_state["explore_selected"] = pick
        st.session_state["surprise_picked"] = True
        st.rerun()


def render() -> None:
    # Full-bleed photographic hero with the title overlaid (Req 2.1, 2.2).
    import base64
    from pathlib import Path

    assets = Path(__file__).resolve().parents[1] / "assets"

    # Prefer a cinematic background video served from static folder.
    static_video = Path(__file__).resolve().parents[1] / "static" / "hero.mp4"
    hero_dir = assets / "hero"
    video_file = None
    for cand in ("hero.mp4", "hero.webm", "hero.mov"):
        p = hero_dir / cand
        if p.exists() and p.stat().st_size > 0:
            video_file = p
            break

    if video_file is not None and static_video.exists():
        mime = "video/mp4"
        st.markdown(f"<h1 class='atw-sronly'>{config.APP_TITLE}</h1>", unsafe_allow_html=True)
        # Use static file URL (served by Streamlit's static folder)
        cards.video_hero("app/static/hero.mp4?v=2", config.APP_TITLE,
                         config.APP_TAGLINE, mime=mime)
    else:
        hero_path = assets / "food" / "_hero.jpg"
        hero_src = None
        if hero_path.exists():
            b64 = base64.b64encode(hero_path.read_bytes()).decode("ascii")
            hero_src = f"data:image/jpeg;base64,{b64}"
        cards.hero_banner(hero_src, config.APP_TITLE, config.APP_TAGLINE)

    # A short, punchy hook (keeps the landing airy and curiosity-driven).
    st.markdown(
        "<div class='atw-narrative' style='margin-top:8px'>"
        "Food is never just food — it's how the world lives, celebrates, heals, and "
        "wanders. Come taste the connections.</div>",
        unsafe_allow_html=True,
    )

    # Animated headline counters — the scale of the journey, in real numbers.
    try:
        k = repo.landing_kpis()
        cards.kpi_counters([
            {"emoji": "🌍", "value": k["countries"], "label": "Countries mapped"},
            {"emoji": "🍛", "value": k["dishes"], "label": "Signature dishes"},
            {"emoji": "🏛", "value": k["heritage_sites"], "label": "UNESCO Heritage sites"},
            {"emoji": "🎉", "value": k["festivals"] + k["culinary"], "label": "Festivals & food traditions"},
            {"emoji": "✈️", "value": round(k["tourists"] / 1_000_000),
             "suffix": "M", "label": "Food travelers a year"},
        ])
    except Exception:  # noqa: BLE001
        pass

    left, mid_a, mid_b, right = st.columns([0.6, 1, 1, 0.6])
    with mid_a:
        st.markdown(
            '<a href="#explore_map" style="display:inline-block;width:100%;text-align:center;'
            'padding:12px 24px;background:linear-gradient(135deg,#C0392B,#D64B34);color:#fff;'
            'border-radius:999px;font-weight:700;text-decoration:none;font-family:Inter,sans-serif;'
            'box-shadow:0 6px 18px rgba(138,75,18,0.25);">🗺️  Explore the Map  →</a>',
            unsafe_allow_html=True,
        )
    with mid_b:
        if st.button("🎲  Surprise me", width="stretch"):
            _open_random_country()

    # Show feedback when surprise country is picked
    if st.session_state.pop("surprise_picked", False):
        picked_iso = st.session_state.get("selected_country", "")
        try:
            profile = repo.get_country_profile(picked_iso)
            name = profile.get("name", picked_iso) if profile else picked_iso
        except Exception:
            name = picked_iso
        st.success(f"🎲 Taking you to **{name}**! Scroll down to the Country Story section to explore.")

    st.markdown(
        "<div style='text-align:center;color:#574B42;font-size:0.92rem;margin-top:2px'>"
        "No menus — the world map is your navigation. Click any country to open its story.</div>",
        unsafe_allow_html=True,
    )

    # Surprising, data-derived facts to spark curiosity.
    st.markdown("<div style=\"height:24px\"></div>", unsafe_allow_html=True)
    cards.fact_strip(_curiosity_facts())

    # Curiosity hooks — entice a new visitor to click in (Req 17 spirit).
    st.markdown("<div style=\"height:24px\"></div>", unsafe_allow_html=True)
    # Render all teasers + buttons as a single HTML grid so buttons align perfectly
    teaser_cards = ""
    for emoji, title, sub, dest in _TEASERS:
        teaser_cards += (
            f'<div class="atw-teaser-wrap">'
            f'<div class="atw-teaser">'
            f'<div class="emoji">{emoji}</div>'
            f'<div class="t-title">{title}</div>'
            f'<div class="t-sub">{sub}</div>'
            f'</div>'
            f'<a href="#{dest}" class="atw-teaser-btn" style="color:#FFFFFF !important;">Take me there →</a>'
            f'</div>'
        )
    st.markdown(
        f"""
        <style>
        .atw-teaser-grid {{
            display:grid;
            grid-template-columns:repeat(4, 1fr);
            gap:16px;
            margin:8px 0;
        }}
        .atw-teaser-wrap {{
            display:flex;
            flex-direction:column;
            height:100%;
        }}
        .atw-teaser-wrap .atw-teaser {{
            flex:1;
            display:flex;
            flex-direction:column;
        }}
        .atw-teaser-wrap .atw-teaser .t-sub {{
            flex:1;
        }}
        .atw-teaser-btn, .atw-teaser-btn:link, .atw-teaser-btn:visited {{
            display:block;
            width:100%;
            text-align:center;
            padding:10px 16px;
            background:linear-gradient(135deg, #C0392B, #D64B34);
            border:none;
            color:#FFFFFF !important;
            border-radius:12px;
            font-weight:700;
            text-decoration:none;
            font-size:0.82rem;
            font-family:'Inter',sans-serif;
            margin-top:12px;
            transition:all 0.2s ease;
            box-sizing:border-box;
            box-shadow:0 3px 10px rgba(192,57,43,0.2);
        }}
        .atw-teaser-btn:hover {{
            background:linear-gradient(135deg, #A0301F, #C0392B);
            color:#FFFFFF !important;
            transform:translateY(-2px);
            box-shadow:0 8px 20px rgba(192,57,43,0.35);
        }}
        @media (max-width:768px) {{
            .atw-teaser-grid {{ grid-template-columns:repeat(2, 1fr); }}
        }}
        </style>
        <div class="atw-teaser-grid">{teaser_cards}</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style=\"height:24px\"></div>", unsafe_allow_html=True)
