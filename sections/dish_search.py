"""Dish_Search — find a dish by name and see its countries (Req 13)."""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from data import repository as repo

_MAX_LEN = 100


def render() -> None:
    cards.page_header("dish_search")
    body()


def body() -> None:
    st.markdown('<p style="color:#2A2320;font-weight:700;">Search any dish <span style="font-weight:400;">(e.g., Sushi, Biryani, Paella)</span></p>', unsafe_allow_html=True)
    raw = st.text_input("Search any dish", max_chars=_MAX_LEN, label_visibility="collapsed",
                        placeholder="Type a dish name here...")
    query = (raw or "").strip()

    # Empty/whitespace-only input -> prompt, no results (Req 13.3).
    if not query:
        st.markdown('<p style="color:#574B42;font-style:italic;">Enter a dish name to discover where it feels at home.</p>', unsafe_allow_html=True)
        return

    try:
        results = repo.search_dishes(query)  # case-insensitive substring (Req 13.1, 13.2)
    except Exception:  # noqa: BLE001
        st.warning("Search could not run right now.")
        return

    # No matches -> message (Req 13.4).
    if results.empty:
        st.info(f"No dishes matched “{query}”. Try another name.")
        return

    st.caption(f"{len(results)} match(es) for “{query}”.")
    # Group by dish so a dish shows all its countries.
    for dish, grp in results.groupby("dish"):
        countries = ", ".join(sorted(grp["country"]))
        cards.card(dish, f"Popular in: <b>{countries}</b>", icon="🍽️")

