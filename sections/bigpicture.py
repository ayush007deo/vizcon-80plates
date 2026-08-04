"""Food, Health & Flavor — the big picture."""
from __future__ import annotations

import traceback
import streamlit as st

from components import cards


def render() -> None:
    cards.page_header("bigpicture")
    tab_health, tab_happy, tab_insights = st.tabs(
        ["\u2764\ufe0f Food, Culture & Longevity", "\U0001f60a The Happiest Tables", "\U0001f4ca Global Insights"]
    )
    with tab_health:
        try:
            from sections import health
            health.body()
        except Exception as e:
            st.error(f"Health error: {type(e).__name__}: {e}")
            st.code(traceback.format_exc())
    with tab_happy:
        try:
            from sections import happiness
            happiness.body()
        except Exception as e:
            st.error(f"Happiness error: {type(e).__name__}: {e}")
            st.code(traceback.format_exc())
    with tab_insights:
        try:
            from sections import insights
            insights.body()
        except Exception as e:
            st.error(f"Insights error: {type(e).__name__}: {e}")
            st.code(traceback.format_exc())
