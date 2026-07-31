"""Migration_View — animated ingredient-origin journeys (Req 7, 17.2)."""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from components.narrative import insight
from data import repository as repo
from viz.routes import build_route_map


def render() -> None:
    cards.page_header("migration")
    body()


def body() -> None:
    try:
        ingredients = repo.list_migration_ingredients()
    except Exception:  # noqa: BLE001
        st.warning("Migration stories could not be loaded right now.")
        return

    # No stories at all -> message (Req 7.5).
    if not ingredients:
        st.info("No migration stories are available yet.")
        citation.cite("migration")
        return

    ingredient = st.selectbox("Choose an ingredient to follow", ingredients, index=0)

    # Data-derived discovery insight, visually distinct (Req 17.2, 17.4).
    cards.insight_callout(insight("migration", ingredient=ingredient))

    steps = repo.get_migration_story(ingredient)  # ordered by seq / time (Req 7.3)
    if steps.empty:
        st.info(f"No journey is recorded for {ingredient}.")
        citation.cite("migration")
        return

    fig, alt = build_route_map(steps, subject=ingredient)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(alt)  # descriptive alt text (Req 18.2)

    # Ordered list of stops with their time period (Req 7.3, 7.4).
    st.markdown("#### The journey, step by step")
    trail = " &nbsp; → &nbsp; ".join(
        f"<b>{r['location_name']}</b>"
        + (f" <span style='color:#9A8C7A'>({r['time_period']})</span>"
           if isinstance(r["time_period"], str) and r["time_period"] else "")
        for _, r in steps.iterrows()
    )
    st.markdown(trail, unsafe_allow_html=True)

    citation.cite("migration")
