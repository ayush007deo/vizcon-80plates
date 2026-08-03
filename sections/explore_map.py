"""Explore_Map — a living world map that is the app's navigation (Req 3).

Click a country to reveal a rich preview card (food photo, personality, stats), then
"Explore" to enter its full story. Featured cuisines carry food icons; story countries
glow amber.
"""
from __future__ import annotations

import base64
import html as _html
import random
from pathlib import Path

import streamlit as st

from components import cards, citation
from components.flags import flag
from components.navigation import go_to
from data import repository as repo
from viz.choropleth import FEATURED, build_explore_map

_POPULAR = [("🥔", "Potato"), ("☕", "Coffee"), ("🌶️", "Chili Pepper"),
            ("🍫", "Chocolate"), ("🍵", "Tea"), ("🍅", "Tomato")]

# Short teasers for each journey to give the user a reason to click.
_JOURNEY_TEASER = {
    "Potato": "From the Andes to every plate on Earth",
    "Coffee": "Ethiopia's gift to the sleepless world",
    "Chili Pepper": "Born in the Americas, now defines Asian cuisine",
    "Chocolate": "Sacred Aztec drink turned global indulgence",
    "Tea": "A Chinese leaf that conquered continents",
    "Tomato": "Italy's favorite import from Peru",
}


def _inject_journey_css() -> None:
    """CSS for the food-journey selector cards and inline preview."""
    st.markdown("""
    <style>
    .pj-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
        gap:14px; margin:16px 0 20px 0; }
    .pj-card { position:relative; background:#FFFFFF; border:1.5px solid #EFE6D8;
        border-radius:16px; padding:18px 14px; text-align:center;
        transition:all 0.22s ease; box-shadow:0 3px 12px rgba(43,33,24,0.06); }
    .pj-card:hover { transform:translateY(-5px); box-shadow:0 16px 32px rgba(43,33,24,0.14);
        border-color:#E8A317; }
    .pj-card.active { border-color:#C0392B; background:linear-gradient(135deg,#FFF8F1,#FFF0E0);
        box-shadow:0 12px 28px rgba(192,57,43,0.18); transform:translateY(-3px); }
    .pj-card .pj-emoji { font-size:2.2rem; line-height:1;
        filter:drop-shadow(0 3px 6px rgba(0,0,0,0.12)); }
    .pj-card .pj-name { font-family:'Playfair Display',Georgia,serif; font-weight:800;
        font-size:1.05rem; color:#2A2320; margin:8px 0 4px 0; }
    .pj-card .pj-sub { font-family:'Inter',sans-serif; font-size:0.75rem;
        color:#574B42; line-height:1.35; }
    .pj-card .pj-dot { position:absolute; top:10px; right:10px; width:9px; height:9px;
        border-radius:50%; background:#C0392B; box-shadow:0 0 8px rgba(192,57,43,0.5); }

    /* Inline journey reveal */
    .pj-reveal { background:linear-gradient(135deg,#FFF8F1 0%,#FFF3E5 100%);
        border:1px solid #EFDFC4; border-radius:20px; padding:28px 30px;
        margin:20px 0 10px 0; box-shadow:0 12px 36px rgba(43,33,24,0.10);
        animation:atwRise 0.5s ease both; }
    .pj-reveal-head { display:flex; align-items:center; gap:14px; margin-bottom:16px; }
    .pj-reveal-head .emoji { font-size:2.6rem; }
    .pj-reveal-head .title { font-family:'Playfair Display',Georgia,serif; font-weight:800;
        font-size:1.5rem; color:#2A2320; }
    .pj-reveal-head .subtitle { font-size:0.9rem; color:#574B42; font-style:italic; margin-top:2px; }
    .pj-stats-row { display:flex; gap:12px; flex-wrap:wrap; margin:14px 0; }
    .pj-stat { flex:1 1 110px; background:#FFFFFF; border:1px solid #EFE6D8;
        border-radius:12px; padding:14px 10px; text-align:center;
        box-shadow:0 3px 10px rgba(43,33,24,0.05); }
    .pj-stat .val { font-family:'Playfair Display',Georgia,serif; font-weight:800;
        font-size:1.2rem; color:#C0392B; }
    .pj-stat .lab { font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em;
        color:#574B42; margin-top:2px; }
    .pj-stops { display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 6px 0; }
    .pj-stop { display:inline-flex; align-items:center; gap:6px; background:#FFFFFF;
        border:1px solid #EFE6D8; border-radius:999px; padding:5px 14px;
        font-size:0.84rem; color:#2A2320; font-weight:500;
        transition:all 0.15s ease; }
    .pj-stop:hover { border-color:#E8A317; background:#FFFBF3; }
    .pj-stop .num { background:linear-gradient(135deg,#F59E0B,#F0592B); color:#fff;
        width:20px; height:20px; border-radius:50%; display:inline-flex; align-items:center;
        justify-content:center; font-size:0.68rem; font-weight:800; flex-shrink:0; }
    </style>
    """, unsafe_allow_html=True)


def _render_popular_journeys(story_countries) -> None:
    """Render food journey selection as visual cards with an inline preview."""
    _inject_journey_css()

    st.markdown("#### 🔥 Popular journeys")
    st.markdown('<p style="color:#574B42;font-size:0.9rem;">Every ingredient on your plate once crossed oceans. Pick one to see its story unfold.</p>', unsafe_allow_html=True)

    # Render visual food cards as HTML grid + Streamlit buttons for interactivity
    active_pick = st.session_state.get("journey_pick")

    # The visual cards (HTML for looks, Streamlit buttons for actual interaction)
    cards_html = ""
    for emoji, subject in _POPULAR:
        is_active = active_pick == subject
        active_cls = " active" if is_active else ""
        dot = '<div class="pj-dot"></div>' if is_active else ""
        teaser = _JOURNEY_TEASER.get(subject, "")
        cards_html += (
            f'<div class="pj-card{active_cls}">{dot}'
            f'<div class="pj-emoji">{emoji}</div>'
            f'<div class="pj-name">{_html.escape(subject)}</div>'
            f'<div class="pj-sub">{_html.escape(teaser)}</div></div>'
        )
    st.markdown(f'<div class="pj-grid">{cards_html}</div>', unsafe_allow_html=True)

    # Actual clickable buttons (compact row beneath the visual cards)
    cols = st.columns(len(_POPULAR) + 1)
    for col, (emoji, subject) in zip(cols, _POPULAR):
        with col:
            is_active = active_pick == subject
            label = f"✓ {subject}" if is_active else f"{emoji} {subject}"
            if st.button(label, key=f"pop_{subject}", width="stretch",
                         type="primary" if is_active else "secondary"):
                if active_pick == subject:
                    # Toggle off
                    st.session_state.pop("journey_pick", None)
                else:
                    st.session_state["journey_pick"] = subject
                st.rerun()
    with cols[-1]:
        if st.button("🎲 Surprise", key="explore_surprise", width="stretch"):
            # Pick a random food journey to show inline
            journey_options = [s for _, s in _POPULAR]
            pick = random.choice(journey_options)
            st.session_state["journey_pick"] = pick
            st.rerun()

    # Inline journey reveal
    if active_pick:
        _inline_journey_preview(active_pick)


def _inline_journey_preview(subject: str) -> None:
    """Show a polished animated route map + key stats inline."""
    from viz.routes import build_route_map

    steps = repo.get_migration_story(subject)
    if steps is None or steps.empty:
        steps = repo.get_spice_route(subject)
    if steps is None or steps.empty:
        st.info(f"No journey recorded for {subject}.")
        return

    # Filter out (0,0) global pseudo-stops
    real = steps[~((steps["lat"] == 0) & (steps["lon"] == 0))
                 & (steps["location_name"].str.lower() != "global")].reset_index(drop=True)
    went_global = len(real) < len(steps)

    # Metadata
    origin = real.iloc[0]["location_name"].split("(")[0].strip() if not real.empty else "Unknown"
    n_stops = len(real)
    periods = [p for p in real["time_period"].tolist() if p]
    span = f"{periods[0]} → {periods[-1]}" if len(periods) >= 2 else (periods[0] if periods else "Centuries")
    teaser = _JOURNEY_TEASER.get(subject, "A food that changed the world.")

    _ICONS = {"Potato": "🥔", "Coffee": "☕", "Chili Pepper": "🌶️",
              "Chocolate": "🍫", "Tea": "🍵", "Tomato": "🍅"}
    emoji = _ICONS.get(subject, "🍽️")

    # Reveal card header + stats
    st.markdown(
        f'<div class="pj-reveal">'
        f'<div class="pj-reveal-head">'
        f'<span class="emoji">{emoji}</span>'
        f'<div><div class="title">The Journey of {_html.escape(subject)}</div>'
        f'<div class="subtitle">{_html.escape(teaser)}</div></div></div>'
        f'<div class="pj-stats-row">'
        f'<div class="pj-stat"><div class="val">{_html.escape(origin)}</div><div class="lab">Origin</div></div>'
        f'<div class="pj-stat"><div class="val">{n_stops}</div><div class="lab">Stops crossed</div></div>'
        f'<div class="pj-stat"><div class="val">{_html.escape(span)}</div><div class="lab">Time span</div></div>'
        f'<div class="pj-stat"><div class="val">{"🌍 Yes" if went_global else "Regional"}</div>'
        f'<div class="lab">Went global</div></div></div></div>',
        unsafe_allow_html=True,
    )

    # The animated route map
    fig, alt = build_route_map(real, subject=subject, icon="🚢")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(f"▶ Press play to follow {subject.lower()} across centuries and oceans.")

    # Stop pills
    stops_html = "".join(
        f'<span class="pj-stop"><span class="num">{i}</span>{_html.escape(str(r["location_name"]))}</span>'
        for i, (_, r) in enumerate(real.iterrows(), start=1)
    )
    if went_global:
        stops_html += '<span class="pj-stop"><span class="num">🌍</span>Worldwide</span>'
    st.markdown(f'<div class="pj-stops">{stops_html}</div>', unsafe_allow_html=True)

    # Anchor to full journeys section
    st.markdown(
        '<a href="#journeys" style="display:inline-block;margin-top:14px;padding:10px 22px;'
        'background:linear-gradient(135deg,#C0392B,#D64B34);color:#fff;border-radius:999px;'
        'font-weight:700;text-decoration:none;font-size:0.85rem;font-family:Inter,sans-serif;'
        'box-shadow:0 6px 18px rgba(192,57,43,0.25);transition:all 0.18s ease;">'
        '🧭 Explore all food journeys ↓</a>',
        unsafe_allow_html=True,
    )


def _selected_iso3(event) -> str | None:
    try:
        points = event["selection"]["points"]
    except (KeyError, TypeError):
        return None
    if not points:
        return None
    p = points[0]
    return p.get("location") or (p.get("text") if isinstance(p.get("text"), str) else None)


def _photo_data_uri(profile: dict) -> str | None:
    """A signature-dish photo for the preview card, as a CSS-usable src."""
    from components.images import _local_image, get_food_image

    name = profile.get("name", "")
    dishes = profile.get("dishes") or []
    mains: list[str] = []
    try:
        d = repo.get_dishes(profile["iso3"])
        mains = d[d["course"] == "main"]["name"].tolist()
    except Exception:  # noqa: BLE001
        pass

    ordered = mains + [x for x in dishes if x not in mains]
    for dish in ordered:
        local = _local_image(dish)
        if local:
            try:
                return "data:image/jpeg;base64," + base64.b64encode(
                    Path(local).read_bytes()).decode("ascii")
            except Exception:  # noqa: BLE001
                break
    signature = ordered[0] if ordered else name
    img = get_food_image(*[t for t in (signature, f"{name} cuisine", name) if t])
    if img and img[0].startswith("http"):
        return img[0]
    return None


def _preview_card(iso3: str) -> None:
    """Rich click-preview card: photo + personality + stats + an Explore button."""
    profile = repo.get_country_profile(iso3)
    if not profile:
        return
    name = profile.get("name", iso3)
    tagline = FEATURED[iso3][1] if iso3 in FEATURED else (profile.get("region") or "")
    dishes = [d for d in (profile.get("dishes") or [])][:4]
    fests = [f for f in (profile.get("festivals") or [])][:3]

    def _stat(v, label, fmt=str, suffix=""):
        if v is None or (isinstance(v, float) and v != v):
            return ""
        return (f'<div class="xp-stat"><div class="v">{fmt(v)}{suffix}</div>'
                f'<div class="l">{label}</div></div>')

    life = profile.get("life_expectancy")
    tour = profile.get("annual_tourists")
    herit = profile.get("unesco_heritage_count")
    stats = "".join([
        _stat(int(life) if life is not None else None, "Life exp", suffix=" yrs"),
        _stat(herit, "Heritage sites"),
        _stat(f"{int(tour):,}" if tour is not None else None, "Tourists/yr"),
    ])
    pills = "".join(f'<span class="xp-pill">🍽 {_html.escape(d)}</span>' for d in dishes)
    pills += "".join(f'<span class="xp-pill">🎉 {_html.escape(f)}</span>' for f in fests)

    photo = _photo_data_uri(profile)
    photo_html = (f'<div class="xp-photo" style="background-image:url(\'{photo}\')"></div>'
                  if photo else '<div class="xp-photo"></div>')
    st.markdown(
        f'<div class="xp-card">{photo_html}<div class="xp-info">'
        f'<div class="xp-title">{flag(iso3)} {_html.escape(name)}'
        f'<span class="xp-tag">{_html.escape(tagline)}</span></div>'
        f'<div class="xp-pills">{pills or "A food story awaits."}</div>'
        f'<div class="xp-stats">{stats}</div></div></div>',
        unsafe_allow_html=True,
    )
    if st.button(f"Explore {name}  →", type="primary", key=f"xp_go_{iso3}"):
        st.session_state["selected_country"] = iso3
        st.rerun()


def render() -> None:
    cards.page_header("explore_map")

    try:
        countries = repo.countries_for_map()
        stats = repo.map_hover_stats()
    except Exception:  # noqa: BLE001
        st.warning("The map is unavailable right now — country data could not be loaded.")
        return
    if countries.empty:
        st.info("No countries are available to explore yet.")
        return

    story_countries = countries[countries["has_story"].astype(bool)]

    st.markdown(
        "<div style='display:flex;gap:18px;flex-wrap:wrap;align-items:center;"
        "font-size:0.9rem;color:#574B42;margin:2px 0 6px 0'>"
        "<span>🟠 <b>Featured food story</b></span>"
        "<span>🍽️ Iconic cuisine</span>"
        "<span>⚫ Coming soon</span>"
        "<span>✨ Click a glowing country to preview it</span></div>",
        unsafe_allow_html=True,
    )

    selected = st.session_state.get("explore_selected")
    fig, alt = build_explore_map(countries, selected=selected, hover_stats=stats)
    event = st.plotly_chart(
        fig, width="stretch", on_select="rerun", selection_mode="points",
        key="explore_map_select", config={"displayModeBar": False, "scrollZoom": False},
    )

    iso3 = _selected_iso3(event)
    if iso3 and iso3 != selected:
        if bool(story_countries["iso3"].eq(iso3).any()):
            st.session_state["explore_selected"] = iso3
            st.rerun()
        else:
            row = countries[countries["iso3"] == iso3]
            name = row.iloc[0]["name"] if not row.empty else iso3
            st.info(f"No food story is available for {name} yet. Try a glowing country.")

    # Preview card for the selected country (click → preview → explore).
    if selected:
        _preview_card(selected)
    else:
        st.markdown(f'<p style="color:#574B42;font-size:0.9rem;">{alt}</p>',
                    unsafe_allow_html=True)

    # Popular journeys — visual cards with inline journey reveal
    _render_popular_journeys(story_countries)


    # Prominent search section
    st.markdown(
        """
        <div style="background:#FFFFFF;border:2px solid #E8A317;border-radius:16px;
            padding:20px 24px;margin:24px 0 16px 0;box-shadow:0 4px 16px rgba(232,163,23,0.12);">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <span style="font-size:1.4rem;">🔎</span>
                <span style="font-weight:700;font-size:1.05rem;color:#2A2320;">Search for a dish</span>
                <span style="font-size:0.8rem;color:#9A8C7A;">Type any dish name to find where it belongs</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    from sections import dish_search
    dish_search.body()
