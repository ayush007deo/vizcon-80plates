"""Country_Story — a card-based profile of a country's food culture (Req 4).

Renders the selected country's Country_Profile as cards (never a table). Missing
fields show an "unavailable" placeholder while available fields still render. A
control navigates to the Plate_View for the selected country.
"""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from components import cards, citation
from components.navigation import go_to, label_for
from data import repository as repo


import html as _html

_TASTE_META = {
    "spicy": ("🌶️", "Spicy"), "sweet": ("🍬", "Sweet"), "seafood": ("🐟", "Seafood"),
    "street food": ("🍢", "Street food"), "vegetarian": ("🥬", "Vegetarian"),
    "healthy": ("🥗", "Healthy"), "savory": ("🥩", "Savory"), "sour": ("🍋", "Sour"),
}


def _tagline(iso3: str, profile: dict) -> str:
    """A one-line personality for the country (curated for featured, else derived)."""
    from viz.choropleth import FEATURED

    if iso3 in FEATURED:
        return FEATURED[iso3][1]
    try:
        groups = repo.get_food_groups(iso3)
        if not groups.empty:
            top = groups.sort_values("pct", ascending=False).iloc[0]["food_group"]
            return f"Where {top.lower()} anchor the table."
    except Exception:  # noqa: BLE001
        pass
    region = profile.get("region")
    return f"A {region} food culture." if region else "A world of flavor."


def _facts(profile: dict, iso3: str) -> list[str]:
    """A rotating deck of data-derived 'Did you know?' facts for this country."""
    name = profile.get("name", iso3)
    facts: list[str] = []
    try:
        groups = repo.get_food_groups(iso3)
        if not groups.empty:
            top = groups.sort_values("pct", ascending=False).iloc[0]
            facts.append(f"{top['food_group']} make up {float(top['pct']):.0f}% of the "
                         f"average plate in {name}.")
    except Exception:  # noqa: BLE001
        pass
    try:
        ins = repo.get_insights()
        life, avg = profile.get("life_expectancy"), ins.get("avg_life_expectancy")
        if life is not None and avg is not None:
            d = float(life) - float(avg)
            facts.append(f"Life expectancy in {name} is {float(life):.0f} years — "
                         f"{abs(d):.0f} {'above' if d >= 0 else 'below'} the world average.")
    except Exception:  # noqa: BLE001
        pass
    try:
        hr = repo.heritage_rank(iso3)
        h = profile.get("unesco_heritage_count")
        if hr and h:
            facts.append(f"{name} guards {int(h)} UNESCO World Heritage sites — "
                         f"#{hr['region_rank']} in {hr['region']}.")
    except Exception:  # noqa: BLE001
        pass
    try:
        culinary = repo.get_country_culinary(iso3)
        if culinary is not None and not culinary.empty:
            el = culinary.iloc[0]["element"]
            facts.append(f"{el} is recognized by UNESCO as living cultural heritage of {name}.")
    except Exception:  # noqa: BLE001
        pass
    sim = None
    try:
        sim = repo.most_similar(iso3, 1)
    except Exception:  # noqa: BLE001
        sim = None
    if sim is not None and not sim.empty:
        r = sim.iloc[0]
        facts.append(f"{name}'s plate is {float(r['score']):.0f}% similar to {r['name']}'s — "
                     "distant kitchens, shared ingredients.")
    return [f for f in facts if f]


def _country_switcher(current_iso3: str | None) -> None:
    """A compact clickable world map: click any country to switch the whole story."""
    from viz.choropleth import build_explore_map

    try:
        countries = repo.countries_for_map()
    except Exception:  # noqa: BLE001
        return
    if countries.empty:
        return
    story = countries[countries["has_story"].astype(bool)]

    with st.expander("🗺️  Jump to another country (click the map)", expanded=False):
        fig, _ = build_explore_map(countries, highlight=[current_iso3] if current_iso3 else None)
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=0, b=0))
        event = st.plotly_chart(
            fig, width="stretch", on_select="rerun",
            selection_mode="points", key="story_switch_map",
            config={"displayModeBar": False},
        )
        try:
            pts = event["selection"]["points"]
        except (KeyError, TypeError):
            pts = []
        if pts:
            p = pts[0]
            new_iso3 = p.get("location") or (p.get("text") if isinstance(p.get("text"), str) else None)
            if new_iso3 and new_iso3 != current_iso3:
                if bool(story["iso3"].eq(new_iso3).any()):
                    st.session_state["selected_country"] = new_iso3
                    st.rerun()
                else:
                    row = countries[countries["iso3"] == new_iso3]
                    nm = row.iloc[0]["name"] if not row.empty else new_iso3
                    st.info(f"No food story for {nm} yet — try a highlighted country.")


def render() -> None:
    iso3 = st.session_state.get("selected_country")

    # In single-page flow, auto-select a featured country so the section isn't empty.
    if not iso3:
        try:
            from viz.choropleth import FEATURED
            iso3 = list(FEATURED.keys())[0] if FEATURED else None
            if iso3:
                st.session_state["selected_country"] = iso3
        except Exception:  # noqa: BLE001
            pass

    from components.narrative import narrative
    cards.section_band("Country Story", narrative("country_story"), emoji="📖")

    # The map is the navigation: switch countries without leaving the story.
    # Country switcher removed - uses Explore map selection

    if not iso3:
        st.info("Choose a country on the Explore Map above to read its food story.")
        return

    try:
        profile = repo.get_country_profile(iso3)
    except Exception:  # noqa: BLE001 - app-level banner also guards this
        st.warning("This country's story could not be loaded right now.")
        return

    # Requested country not present (Req 1.6): message, stay on section.
    if profile is None:
        st.warning("This country's data is unavailable.")
        return

    # Title with flag for a sense of place.
    from components.flags import flag
    from components.images import get_food_image

    name = profile.get("name", iso3)
    dishes = profile.get("dishes") or []

    # Hero: country landmark image if available, else signature-dish photo.
    signature = dishes[0] if dishes else name
    try:
        dish_rows = repo.get_dishes(iso3)
        mains = dish_rows[dish_rows["course"] == "main"]["name"].tolist()
        if mains:
            signature = mains[0]
    except Exception:  # noqa: BLE001
        pass

    # Try country landmark image first (assets/country/<ISO3>.jpg)
    _COUNTRY_DIR = Path(__file__).resolve().parents[1] / "assets" / "country"
    # Fallback path for Streamlit Cloud
    if not _COUNTRY_DIR.exists():
        _alt_country = Path(os.getcwd()) / "assets" / "country"
        if _alt_country.exists():
            _COUNTRY_DIR = _alt_country
    _country_img = None
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        _cp = _COUNTRY_DIR / f"{iso3}{ext}"
        if _cp.exists() and _cp.stat().st_size > 0:
            _country_img = str(_cp)
            break
    if _country_img:
        img = (_country_img, "Landmark photo · Wikimedia Commons")
    else:
        img = get_food_image(signature, f"{name} cuisine", name)

    region = profile.get("region") or ""
    tagline = _tagline(iso3, profile)

    # Clean hero card: photo left, info right, compact and well-proportioned
    img_src = img[0] if img else None

    # Convert local file paths to base64 data URIs (CSS url() can't access local filesystem)
    if img_src and not img_src.startswith(("http://", "https://", "data:")):
        import base64
        _img_path = Path(img_src)
        if _img_path.exists():
            _suffix = _img_path.suffix.lower()
            _mime = "image/jpeg" if _suffix in (".jpg", ".jpeg") else f"image/{_suffix.lstrip('.')}"
            _b64 = base64.b64encode(_img_path.read_bytes()).decode("ascii")
            img_src = f"data:{_mime};base64,{_b64}"
        else:
            img_src = None

    if img_src:
        st.markdown(
            f'''
            <div style="display:flex;gap:0;align-items:stretch;margin:12px auto 20px auto;
                max-width:720px;height:200px;
                background:#FFFFFF;border:1px solid #EFE6D8;border-radius:18px;overflow:hidden;
                box-shadow:0 8px 24px rgba(43,33,24,0.10);">
                <div style="flex:0 0 200px;
                    background:url(\'{img_src}\') top center/cover no-repeat;"></div>
                <div style="flex:1;padding:18px 22px;display:flex;flex-direction:column;
                    justify-content:center;overflow:hidden;">
                    <div style="display:flex;align-items:center;gap:10px;">
                        <span style="font-size:1.8rem;line-height:1;">{flag(iso3)}</span>
                        <h2 style="margin:0;font-family:Playfair Display,Georgia,serif;
                            font-weight:800;font-size:1.5rem;color:#2A2320;">{_html.escape(name)}</h2>
                    </div>
                    <div style="font-size:0.75rem;color:#574B42;text-transform:uppercase;
                        letter-spacing:0.06em;font-weight:600;margin-top:4px;">{_html.escape(region)}</div>
                    <div style="font-family:Georgia,serif;font-style:italic;color:#574B42;
                        font-size:0.92rem;margin-top:8px;line-height:1.35;">
                        &ldquo;{_html.escape(tagline)}&rdquo;</div>
                    <div style="margin-top:8px;font-size:0.78rem;color:#9A8C7A;">
                        🍽 {_html.escape(signature)}</div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'''
            <div style="margin:12px auto 20px auto;padding:18px 22px;max-width:720px;
                background:#FFFFFF;border:1px solid #EFE6D8;border-radius:18px;
                box-shadow:0 6px 18px rgba(43,33,24,0.08);">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:1.8rem;line-height:1;">{flag(iso3)}</span>
                    <h2 style="margin:0;font-family:Playfair Display,Georgia,serif;
                        font-weight:800;font-size:1.5rem;color:#2A2320;">{_html.escape(name)}</h2>
                </div>
                <div style="font-size:0.75rem;color:#574B42;text-transform:uppercase;
                    letter-spacing:0.06em;font-weight:600;margin-top:4px;">{_html.escape(region)}</div>
                <div style="font-family:Georgia,serif;font-style:italic;color:#574B42;
                    font-size:0.92rem;margin-top:8px;">&ldquo;{_html.escape(tagline)}&rdquo;</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    # A rotating deck of data-derived "Did you know?" facts (Req 17.2/17.4).
    facts = _facts(profile, iso3)
    if facts:
        fkey = f"cs_fact::{iso3}"
        idx = st.session_state.get(fkey, 0) % len(facts)
        cards.insight_callout(facts[idx])
        if len(facts) > 1 and st.button("🔀 Another fact", key=f"cs_more::{iso3}"):
            st.session_state[fkey] = (idx + 1) % len(facts)
            st.rerun()

    # UNESCO food traditions — how culture shapes this country's food (if any).
    try:
        culinary = repo.get_country_culinary(iso3)
    except Exception:  # noqa: BLE001
        culinary = None
    if culinary is not None and not culinary.empty:
        pills = " ".join(
            f'<span class="atw-pill">{r["element"]}'
            + (f' · {int(r["year"])}' if r["year"] and str(r["year"]).strip() else "")
            + "</span>"
            for _, r in culinary.iterrows()
        )
        cards.card("UNESCO Food Traditions (Intangible Heritage)", pills, icon="🍲")

    # Row 1: staple foods, famous dishes, festivals (lists) — Req 4.2
    c1, c2, c3 = st.columns(3)
    with c1:
        cards.list_card("Staple Foods", profile.get("staple_foods"), icon="🌾")
    with c2:
        cards.list_card("Famous Dishes", profile.get("dishes"), icon="🍛")
    with c3:
        cards.list_card("Festivals", profile.get("festivals"), icon="🎉")

    # Row 2: bold hero stats with a one-line story context under each.
    def _sub(text: str) -> None:
        st.markdown(f"<div class='cs-substat'>{_html.escape(text)}</div>",
                    unsafe_allow_html=True)

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        h = profile.get("unesco_heritage_count")
        cards.big_stat("🏛 Cultural Heritage", h, icon="")
        hr = repo.heritage_rank(iso3)
        if h is not None and hr:
            _sub(f"#{hr['region_rank']} in {hr['region']}")
    with d2:
        life = profile.get("life_expectancy")
        cards.big_stat("❤️ Healthy Living",
                       f"{float(life):.0f} yrs" if life is not None else None, icon="")
        if life is not None:
            ins = repo.get_insights()
            avg = ins.get("avg_life_expectancy")
            if avg:
                d = float(life) - float(avg)
                _sub(f"{'+' if d >= 0 else ''}{d:.0f} yrs vs world average")
    with d3:
        nutri = profile.get("nutrition_score")
        cards.big_stat("🥗 Nutrition Score",
                       f"{float(nutri):.0f}/100" if nutri is not None else None, icon="")
        if nutri is not None:
            _sub("higher = more balanced plate")
    with d4:
        tourists = profile.get("annual_tourists")
        cards.big_stat("✈️ Food Tourism",
                       f"{int(tourists):,}" if tourists is not None else None, icon="")
        if tourists is not None:
            _sub("international visitors / year")

    # Taste profile — the country's flavor fingerprint, derived from its dishes.
    _taste_profile(iso3)

    # Who shares my plate? — the connection feature (Req theme: how the world connects).
    _who_shares_my_plate(iso3, name)

    # Narrative insight — comparative food story
    try:
        groups = repo.get_food_groups(iso3)
        if not groups.empty:
            top_group = groups.sort_values("pct", ascending=False).iloc[0]
            avg_pct = 100.0 / len(groups) if len(groups) > 0 else 0
            if float(top_group["pct"]) > avg_pct * 1.5:
                cards.insight_callout(
                    f"{name}'s plate tells a story: {top_group['food_group'].lower()} makes up "
                    f"{float(top_group['pct']):.0f}% of the diet — that's what geography, climate, "
                    f"and centuries of tradition put on the table."
                )
    except Exception:
        pass

    # Plate and comparison folded in as tabs so a country's story lives on one page.
    st.markdown("###")
    from sections import plate as plate_section
    from sections import similarity as similarity_section

    tab_plate, tab_compare = st.tabs(["🍽️ What's on the Plate?", "🤝 Compare Plates"])
    with tab_plate:
        plate_section.body()
    with tab_compare:
        similarity_section.body()


def _taste_profile(iso3: str) -> None:
    """A flavor fingerprint (stars) derived from the country's dishes' taste tags."""
    try:
        tp = repo.taste_profile(iso3)
    except Exception:  # noqa: BLE001
        return
    if tp is None or tp.empty:
        return
    top = int(tp["n"].max())
    rows = []
    for _, r in tp.iterrows():
        emoji, label = _TASTE_META.get(r["tag"], ("🍽️", str(r["tag"]).title()))
        filled = max(1, round(float(r["n"]) / top * 5))
        stars = ("★" * filled) + f"<span class='off'>{'★' * (5 - filled)}</span>"
        rows.append(f"<div class='row'><span class='lab'>{emoji} {_html.escape(label)}</span>"
                    f"<span class='stars'>{stars}</span></div>")
    st.markdown("#### 🎨 Taste profile")
    st.markdown(f"<div class='cs-taste'>{''.join(rows)}</div>", unsafe_allow_html=True)
    st.caption("Derived from the flavors of this country's signature dishes.")


def _who_shares_my_plate(iso3: str, name: str) -> None:
    """Countries with the most similar plate + the ingredients they share."""
    try:
        sim = repo.most_similar(iso3, 4)
    except Exception:  # noqa: BLE001
        return
    if sim is None or sim.empty:
        return
    from components.flags import flag

    st.markdown("#### 🤝 Who shares my plate?")
    st.caption(f"Distant kitchens that cook like {name} — by shared staples and flavors.")
    cards_html = []
    for _, r in sim.iterrows():
        shared = [str(x) for x in (r["common_foods"] or [])][:5]
        shared_txt = ", ".join(shared) if shared else "shared staples & climate"
        cards_html.append(
            f"<div class='c'><span class='pct'>{float(r['score']):.0f}%</span>"
            f"<div class='name'>{flag(r['iso3'])} {_html.escape(r['name'])}</div>"
            f"<div class='shared'>Shared: {_html.escape(shared_txt)}</div></div>"
        )
    st.markdown(f"<div class='cs-share'>{''.join(cards_html)}</div>", unsafe_allow_html=True)
