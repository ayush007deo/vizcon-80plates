"""Traditions & Heritage — festivals and UNESCO heritage (culture + tourism)."""
from __future__ import annotations

import streamlit as st

from components import cards, lottie
from sections import culinary, festivals, heritage


def render() -> None:
    cards.page_header("traditions")
    lottie.show("festival", height=140)  # auto-appears when assets/lottie/festival.json exists
    tab_culinary, tab_fest, tab_herit = st.tabs(
        ["🍲 Culinary Heritage", "🎉 Festivals Around the Table", "🏛 Heritage & Tourism"]
    )
    with tab_culinary:
        culinary.body()
    with tab_fest:
        festivals.body()
    with tab_herit:
        heritage.body()
