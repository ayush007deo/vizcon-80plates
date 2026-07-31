"""Food, Health & Flavor — the big picture: health, cuisine clusters, global insights."""
from __future__ import annotations

import streamlit as st

from components import cards
from sections import happiness, health, insights


def render() -> None:
    cards.page_header("bigpicture")
    tab_health, tab_happy, tab_insights = st.tabs(
        ["❤️ Food, Culture & Longevity", "😊 The Happiest Tables", "📊 Global Insights"]
    )
    with tab_health:
        health.body()
    with tab_happy:
        happiness.body()
    with tab_insights:
        insights.body()
