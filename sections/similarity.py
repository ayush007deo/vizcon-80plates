"""Similarity_View — 'How Similar Is Your Plate?' compare two countries (Req 6)."""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from components.navigation import go_to
from data import repository as repo

_PROMPT = "Choose a country…"


def render() -> None:
    cards.page_header("similarity")
    body()


def body() -> None:
    base = st.session_state.get("selected_country")
    if not base:
        st.info("Pick a country on the Explore Map first, then compare it with another.")
        if st.button("← Back to the map"):
            go_to("explore_map")
            st.rerun()
        return

    try:
        countries = repo.list_countries()
    except Exception:  # noqa: BLE001
        st.warning("Comparison data could not be loaded right now.")
        return

    name_by_iso = dict(zip(countries["iso3"], countries["name"]))
    base_name = name_by_iso.get(base, base)
    st.subheader(f"{base_name} compared with…")

    # Second-country selector (a selector here is allowed; the no-dropdown rule is
    # specific to entering a country from the Explore Map, Req 3.6).
    options = [_PROMPT] + [
        n for i, n in zip(countries["iso3"], countries["name"]) if i != base
    ]
    choice = st.selectbox("Compare with", options, index=0, label_visibility="collapsed")

    # Before a second country is chosen: prompt, and show no score (Req 6.2).
    if choice == _PROMPT:
        st.info("Select a second country to see how alike their plates are.")
        return

    iso_by_name = {n: i for i, n in zip(countries["iso3"], countries["name"])}
    other = iso_by_name.get(choice)
    st.session_state["compare_country"] = other

    result = repo.get_similarity(base, other)
    score = result.get("score") or 0.0

    # Similarity score 0-100 with a text value (non-color channel) (Req 6.3, 18.5).
    st.metric("Similarity", f"{score:.0f}%")
    st.progress(min(1.0, max(0.0, score / 100.0)))

    common = result.get("common_foods") or []
    unique_a = result.get("unique_a") or []
    unique_b = result.get("unique_b") or []

    # Common vs unique (Req 6.4, 6.5); no overlap -> message (Req 6.6).
    if not common:
        st.info(f"{base_name} and {choice} share no common foods in our data.")
    else:
        cards.list_card("Common Foods", common, icon="🤝")

    left, right = st.columns(2)
    with left:
        cards.list_card(f"Unique to {base_name}", unique_a, icon="🍽️")
    with right:
        cards.list_card(f"Unique to {choice}", unique_b, icon="🍽️")

