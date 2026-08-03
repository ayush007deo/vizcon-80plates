"""Plate_View — 'What's on the Plate?' for the selected country (Req 5)."""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from components.navigation import go_to
from data import repository as repo
from viz.plate_chart import build_plate


def render() -> None:
    cards.page_header("plate")
    body()


def body() -> None:
    iso3 = st.session_state.get("selected_country")
    if not iso3:
        st.info("Pick a country on the Explore Map to see what fills its plate.")
        if st.button("← Back to the map"):
            go_to("explore_map")
            st.rerun()
        return

    try:
        profile = repo.get_country_profile(iso3)
        groups = repo.get_food_groups(iso3)
    except Exception:  # noqa: BLE001
        st.warning("The plate could not be loaded right now.")
        return

    from components.flags import flag
    name = (profile or {}).get("name", iso3)
    st.subheader(f"{flag(iso3)} {name}")

    # No proportions available -> unavailable message (Req 5.4).
    if groups is None or groups.empty:
        st.info(f"The plate composition is unavailable for {name}.")
        return

    # Plate chart beside a photo of the country's signature dish.
    from components.images import get_food_image
    dishes = (profile or {}).get("dishes") or []
    plate_col, dish_col = st.columns([3, 2])
    with plate_col:
        fig, alt = build_plate(groups, country_name=name)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption(alt)  # descriptive alt text (Req 18.2)
    with dish_col:
        img = get_food_image(dishes[0], f"{name} cuisine") if dishes else None
        if img:
            st.image(img[0], width="stretch", caption=dishes[0])

