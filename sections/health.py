"""Food, Culture & Longevity — does the way a culture eats shape how long it lives?

An interactive, story-first take on the diet–health link (Req 10). Pick a food group
and the page leads with a plain-language finding (top third vs bottom third life
expectancy), the countries at each extreme, a cultural spotlight that explains *why*
the long-lived food cultures thrive, and an honest takeaway. The scatter is optional.
"""
from __future__ import annotations

import html as _html

import streamlit as st

from components import cards, citation
from components.flags import flag
from data import repository as repo
from viz.bubble import build_health_bubble

_GROUP_EMOJI = {
    "Vegetables": "🥬", "Fruits": "🍓", "Meat": "🥩", "Seafood": "🐟", "Sugar": "🍬",
    "Cereals": "🌾", "Dairy": "🧀",
}

# Curated cultural spotlights (common-knowledge food culture, not fabricated stats).
# iso3 -> (diet keywords, why-it-matters).
_SPOTLIGHTS = {
    "JPN": (["Fish", "Rice", "Fermented foods", "Small portions"],
            "Japan pairs seafood with vegetables, fermentation and moderation — a recipe "
            "for one of the world's longest lifespans."),
    "ITA": (["Vegetables", "Olive oil", "Seafood", "Whole grains"],
            "Italy's Mediterranean diet — plants, olive oil and fish — underpins some of "
            "Europe's highest life expectancies."),
    "KOR": (["Vegetables", "Kimchi", "Fermented foods", "Seafood"],
            "Korea's vegetable- and ferment-heavy table is credited with fast-rising "
            "longevity."),
    "GRC": (["Olive oil", "Vegetables", "Legumes", "Seafood"],
            "Greece gave the Mediterranean diet its name — and Ikaria its 'Blue Zone' fame."),
    "ESP": (["Seafood", "Vegetables", "Olive oil", "Legumes"],
            "Spain now ranks among the longest-lived nations on Earth, Mediterranean plate "
            "and all."),
}
_SPOTLIGHT_ORDER = ["JPN", "ITA", "KOR", "GRC", "ESP"]


def render() -> None:
    cards.page_header("health")
    body()


def body() -> None:
    try:
        groups = repo.health_food_groups()
    except Exception:  # noqa: BLE001
        st.warning("The health data could not be loaded right now.")
        return
    if not groups:
        st.info("No food-and-health data is available yet.")
        citation.cite("health")
        return

    st.markdown(
        "### Does the way a culture eats shape how long its people live?\n"
        "Pick what fills the plate, and see how the world's longest- and shortest-lived "
        "food cultures compare."
    )
    default = "Vegetables" if "Vegetables" in groups else groups[0]
    group = st.radio(
        "Fill the plate with…", groups, horizontal=True, index=groups.index(default),
        format_func=lambda g: f"{_GROUP_EMOJI.get(g, '🍽')} {g}",
    )

    story = repo.diet_health_story(group, n=5)
    if not story:
        st.info(f"Not enough data to tell {group}'s story yet.")
        citation.cite("health")
        return

    _hero(group, story)
    _extremes(group, story)
    _cultural_spotlight()
    _takeaway(group, story)

    # Details on demand — the full scatter, de-emphasized.
    with st.expander("📈 See the detailed chart (all countries)"):
        points = repo.get_health_points(group)
        fig, alt = build_health_bubble(points, group)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption(alt + " Bubble size = population. Correlation is not causation.")

    citation.cite("health")


def _hero(group: str, s: dict) -> None:
    diff = s["diff"]
    direction = "longer" if diff >= 0 else "shorter"
    emoji = _GROUP_EMOJI.get(group, "🍽")
    st.markdown(
        f'<div class="dh-hero"><div class="em">{emoji}</div><div>'
        f'<div class="big">{diff:+.1f} years</div>'
        f'<div class="cap">Countries where <b>{_html.escape(group.lower())}</b> fill the most '
        f'of the plate live about {abs(diff):.0f} years {direction} than those where they '
        f'fill the least.</div></div></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        cards.big_stat(f"🥇 Most {group.lower()}", f"{s['high_life']:.0f} yr life exp", icon="")
    with c2:
        cards.big_stat(f"🥉 Least {group.lower()}", f"{s['low_life']:.0f} yr life exp", icon="")
    with c3:
        corr = s.get("corr")
        cards.big_stat("🔗 Correlation",
                       f"{corr:+.2f}" if corr is not None else "—", icon="")
        st.markdown("<div style='text-align:center;color:#574B42;font-size:0.8rem;"
                    "margin-top:-6px'>with life expectancy</div>", unsafe_allow_html=True)


def _rank_list(title: str, rows: list, group: str) -> str:
    body = "".join(
        f'<div class="dh-row"><span>{flag(r["iso3"])} {_html.escape(r["name"])}</span>'
        f'<span class="le">{float(r["life_expectancy"]):.0f} yr</span></div>'
        for r in rows
    )
    return f'<div class="dh-list"><div class="h">{title}</div>{body}</div>'


def _extremes(group: str, s: dict) -> None:
    st.markdown("####")
    left, right = st.columns(2)
    with left:
        st.markdown(_rank_list(f"🍽 Eat the most {group.lower()}", s["top"], group),
                    unsafe_allow_html=True)
    with right:
        st.markdown(_rank_list(f"🥄 Eat the least {group.lower()}", s["bottom"], group),
                    unsafe_allow_html=True)


def _cultural_spotlight() -> None:
    st.markdown("#### 🍽 Why the long-lived eat well — culture explains it")
    picks = _SPOTLIGHT_ORDER[:3]
    cols = st.columns(len(picks))
    for col, iso3 in zip(cols, picks):
        kws, why = _SPOTLIGHTS[iso3]
        prof = repo.get_country_profile(iso3) or {}
        name = prof.get("name", iso3)
        life = prof.get("life_expectancy")
        life_html = (f' — <b>{float(life):.0f} yr</b> life expectancy'
                     if life is not None else "")
        chips = "".join(f"<span>{_html.escape(k)}</span>" for k in kws)
        with col:
            st.markdown(
                f'<div class="dh-spot"><div class="n">{flag(iso3)} {_html.escape(name)}</div>'
                f'<div class="k">{chips}</div>'
                f'<div class="why">{why}{life_html}</div></div>',
                unsafe_allow_html=True,
            )


def _takeaway(group: str, s: dict) -> None:
    corr = s.get("corr")
    if group in {"Vegetables", "Fruits", "Seafood"}:
        msg = ("No single food is a magic bullet. The world's longest-lived cultures don't "
               "just eat more " + group.lower() + " — they combine plants, seafood, "
               "fermentation and moderation. Culture, not any one ingredient, is the recipe.")
    elif group in {"Sugar", "Meat"} and corr is not None and corr > 0:
        msg = (f"Surprisingly, more {group.lower()} tracks with *longer* life here — but "
               "that's wealth talking: richer nations both eat more " + group.lower() +
               " and live longer. A reminder that correlation isn't causation.")
    else:
        msg = ("What a culture eats is tangled up with how it lives, works and prospers — "
               "food is one thread in the story of longevity, not the whole cloth.")
    cards.insight_callout(msg)
