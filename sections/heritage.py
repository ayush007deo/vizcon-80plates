"""Cultural Heritage — UNESCO sites and whether culture drives tourism (Theme: Culture, Tourism)."""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from components.flags import flag
from components.narrative import insight
from data import repository as repo
from viz.heritage import build_heritage_map, build_heritage_tourism_scatter


def render() -> None:
    cards.page_header("heritage")
    body()


def body() -> None:
    try:
        points = repo.heritage_points()
        scatter_pts = repo.heritage_tourism_points()
        sites = repo.heritage_site_points()
        cat_counts = repo.heritage_category_counts()
    except Exception:  # noqa: BLE001
        st.warning("Heritage data could not be loaded right now.")
        return

    if points.empty and sites.empty:
        st.info("No UNESCO World Heritage data is available yet.")
        citation.cite("heritage")
        return

    # Data-derived discovery insight (culture -> tourism).
    cards.insight_callout(insight("heritage"))

    # Map of individual heritage sites, colored by category.
    if not sites.empty:
        from viz.heritage import build_sites_map
        sfig, salt = build_sites_map(sites)
        st.plotly_chart(sfig, width="stretch", config={"displayModeBar": False})
        st.caption(salt)

        # Category breakdown (Cultural / Natural / Mixed) — a cultural insight.
        if cat_counts:
            cols = st.columns(len(cat_counts))
            icons = {"Cultural": "🏛", "Natural": "🌿", "Mixed": "🌏"}
            for col, (cat, n) in zip(cols, cat_counts.items()):
                with col:
                    cards.big_stat(f"{cat} sites", n, icon=icons.get(cat, "🏛"))
    elif not points.empty:
        fig, alt = build_heritage_map(points)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption(alt)

    # Richest-heritage ranking as bold cards.
    st.markdown("#### Where the world keeps its treasures")
    top = points.head(6)
    cols = st.columns(len(top))
    for col, (_, r) in zip(cols, top.iterrows()):
        with col:
            cards.big_stat(f"{flag(r['iso3'])} {r['name']}", int(r["heritage"]), icon="🏛")

    # Does culture drive tourism?
    if not scatter_pts.empty:
        st.markdown("#### Do travelers follow culture?")
        sfig, salt = build_heritage_tourism_scatter(scatter_pts)
        st.plotly_chart(sfig, width="stretch", config={"displayModeBar": False})
        st.caption(salt)

    citation.cite("heritage")
