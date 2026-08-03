"""How Food Traveled — one animated journey of ingredients & spices, plus the spice map."""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from data import repository as repo
from sections import spice_journey
from viz.routes import build_route_map

# A food icon for each traveler (falls back to a generic plate).
_ICON = {
    "tomato": "🍅", "coffee": "☕", "tea": "🍵", "potato": "🥔", "chili": "🌶️",
    "chilli": "🌶️", "chile": "🌶️", "pepper": "🫑", "black pepper": "🌶️",
    "corn": "🌽", "maize": "🌽", "chocolate": "🍫", "cacao": "🍫", "cocoa": "🍫",
    "sugar": "🍬", "sugarcane": "🍬", "rice": "🍚", "wheat": "🌾", "vanilla": "🌸",
    "cinnamon": "🪵", "nutmeg": "🌰", "clove": "🌿", "cloves": "🌿", "ginger": "🫚",
    "banana": "🍌", "citrus": "🍊", "apple": "🍎", "noodle": "🍜", "noodles": "🍜",
}


def _icon_for(name: str) -> str:
    return _ICON.get(name.strip().lower(), "🍽️")


def render() -> None:
    cards.page_header("journeys")

    # Big discovery hook — the "I didn't know that!" moment
    st.markdown(
        """
        <div class="atw-dark-card" style="background:linear-gradient(135deg,#0B1F33 0%,#16324B 100%);
            border-radius:20px;padding:28px 32px;margin:0 0 20px 0;
            box-shadow:0 16px 40px rgba(11,31,51,0.30);position:relative;overflow:hidden;">
            <div style="position:absolute;right:20px;top:50%;transform:translateY(-50%);
                font-size:4rem;opacity:0.15;">🌍</div>
            <div style="font-family:'Inter',sans-serif;font-weight:700;font-size:0.7rem;
                text-transform:uppercase;letter-spacing:0.12em;color:#F59E0B;
                margin-bottom:8px;">✦ Did you know?</div>
            <div style="font-family:'Playfair Display',Georgia,serif;font-weight:800;
                font-size:1.5rem;color:#FFFFFF;line-height:1.3;max-width:700px;">
                Italy had no tomatoes until 1548. Thailand had no chili peppers
                until the 1600s. India's "native" spices traveled from Indonesia.</div>
            <div style="font-family:'Inter',sans-serif;font-size:0.9rem;color:#CBB89A;
                margin-top:10px;">
                The foods we call "ours" were once strangers. Follow their journeys below.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_journey, tab_map = st.tabs(
        ["🧭 The Journey of Food", "🌍 The World's Spice Map"]
    )
    with tab_journey:
        _journey_body()
    with tab_map:
        spice_journey.world_map_body()


def _journey_body() -> None:
    """One selector for both ingredient migrations and spice routes → animated map."""
    try:
        ingredients = repo.list_migration_ingredients()
        spices = repo.list_spices()
    except Exception:  # noqa: BLE001
        st.warning("Food journeys could not be loaded right now.")
        return

    # Build a combined, labeled menu; remember whether each item is a spice.
    options: list[str] = []
    kind: dict[str, str] = {}
    for ing in ingredients:
        label = f"{_icon_for(ing)}  {ing}"
        options.append(label)
        kind[label] = "ingredient"
    for sp in spices:
        if sp in ingredients:
            continue
        label = f"{_icon_for(sp)}  {sp}  ·  spice"
        options.append(label)
        kind[label] = "spice"

    if not options:
        st.info("No food journeys are available yet.")
        citation.cite("migration")
        return

    st.markdown('<p style="color:#574B42;">Every ingredient on your plate once crossed oceans and centuries. Pick one and press play to follow it home. <strong style="color:#2A2320;">Follow a food across the world:</strong></p>', unsafe_allow_html=True)

    # Honor a pick coming from the Explore map's "Popular journeys" shortcuts.
    default_idx = 0
    pick = st.session_state.pop("journey_pick", None)
    if pick:
        for i, opt in enumerate(options):
            if f" {pick}" in opt or opt.split("  ")[1:2] == [pick]:
                default_idx = i
                break
    choice = st.selectbox("Follow a food", options, index=default_idx, label_visibility="collapsed")
    subject = choice.split("  ")[1] if "  " in choice else choice
    is_spice = kind.get(choice) == "spice"

    if is_spice:
        steps = repo.get_spice_route(subject)
    else:
        steps = repo.get_migration_story(subject)

    if steps is None or steps.empty:
        st.info(f"No journey is recorded for {subject}.")
        citation.cite("migration")
        return

    # Drop (0,0) "Global" pseudo-stops from the map; note worldwide spread instead.
    real = steps[~((steps["lat"] == 0) & (steps["lon"] == 0))
                 & (steps["location_name"].str.lower() != "global")].reset_index(drop=True)
    went_global = len(real) < len(steps)

    _journey_stats(subject, real, went_global)

    # The moving marker is a ship (the voyage), while the menu keeps each food's icon.
    fig, alt = build_route_map(real, subject=subject, icon="🚢")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False})
    st.markdown(f"*▶ Press play to sail the route — " + alt.split(" — ", 1)[-1] + "*")

    # Per-stop "Did You Know?" voyage cards (the scroll-through story).
    st.markdown("#### The voyage, stop by stop")
    _voyage_cards(subject, real, went_global)

    citation.cite("migration")


def _journey_stats(subject: str, steps, went_global: bool) -> None:
    """Explorer-journal KPI cards: origin, stops, travel, today."""
    from sections import journey_facts

    s = journey_facts.summary(subject)
    origin = s.get("origin") or (steps.iloc[0]["location_name"].split("(")[0].strip()
                                 if not steps.empty else "—")
    travel = s.get("travel", "Trade routes")
    today = s.get("today", "Worldwide" if went_global else "Many countries")
    n = len(steps)
    cells = [
        ("🌎", origin, "Origin"),
        ("📍", str(n), "Stops crossed"),
        ("🚢", travel, "How it traveled"),
        ("🍽️", today, "On tables today"),
    ]
    html = "".join(
        f'<div class="vy-stat"><div class="s-ico">{e}</div>'
        f'<div class="s-val">{v}</div><div class="s-lab">{lab}</div></div>'
        for e, v, lab in cells
    )
    st.markdown(f'<div class="vy-stats">{html}</div>', unsafe_allow_html=True)


def _voyage_cards(subject: str, steps, went_global: bool) -> None:
    """A stacked sequence of story cards, one per stop, with a 'Did you know?' line."""
    import html as _html
    import re

    from pipeline.ingest import iso_reference
    from components.flags import flag as _flag
    from sections import journey_facts

    n2i = iso_reference.name_to_iso3()
    for i, (_, r) in enumerate(steps.iterrows(), start=1):
        place = str(r["location_name"])
        iso = n2i.get(re.sub(r"[^a-z]", "", place.lower()))
        fl = (_flag(iso) + " ") if iso else ""
        era = r["time_period"] if isinstance(r["time_period"], str) and r["time_period"] else ""
        fact = journey_facts.stop_fact(subject, place)
        if not fact:
            role = "Where the journey begins." if i == 1 else "A stop on the route."
            fact = role
        era_html = f'<span class="vy-era">{_html.escape(era)}</span>' if era else ""
        st.markdown(
            f'<div class="vy-card"><div class="vy-step">{i}</div>'
            f'<span class="vy-place">{fl}{_html.escape(place)}</span>{era_html}'
            f'<div class="vy-fact">{_html.escape(fact)}</div></div>',
            unsafe_allow_html=True,
        )
    if went_global:
        st.markdown(
            f'<div class="vy-card"><div class="vy-step">🌍</div>'
            f'<span class="vy-place">Around the world</span>'
            f'<div class="vy-fact">From these few stops, {subject.lower()} spread to kitchens '
            "on every continent — a local plant turned global staple.</div></div>",
            unsafe_allow_html=True,
        )
