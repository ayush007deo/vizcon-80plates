"""Insights_View — 'Global Insights' aggregate findings (Req 14, 17.2)."""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from components.narrative import insight
from data import repository as repo


def render() -> None:
    # Opening narrative sentence, before any findings (Req 14.3).
    cards.page_header("insights")
    body()


def body() -> None:
    try:
        data = repo.get_insights()
    except Exception:  # noqa: BLE001
        st.warning("Global insights could not be loaded right now.")
        return

    # No profiles at all -> message (Req 14.4).
    if not data or data.get("country_count", 0) == 0:
        st.info("No global findings are available yet.")
        return

    # Data-derived discovery insight, visually distinct (Req 17.2, 17.4).
    cards.insight_callout(insight("insights"))

    # Aggregate findings — each names its metric and value (Req 14.1),
    # computed only over countries where the metric is available (Req 14.2).
    findings = []
    findings.append(("Countries in the journey", str(data["country_count"]), "🌍"))
    if data.get("avg_life_expectancy") is not None:
        findings.append((
            f"Avg life expectancy (of {int(data['life_n'])} countries)",
            f"{float(data['avg_life_expectancy']):.1f} yrs", "❤️",
        ))
    if data.get("top_heritage_country"):
        findings.append((
            "Most UNESCO heritage sites",
            f"{data['top_heritage_country']} ({data['top_heritage_count']})", "🏛",
        ))
    if data.get("top_nutrition_country"):
        findings.append((
            "Highest nutrition score",
            f"{data['top_nutrition_country']} ({data['top_nutrition_score']:.0f}/100)", "🥗",
        ))
    if data.get("biggest_cluster"):
        findings.append((
            "Largest cuisine family",
            f"{data['biggest_cluster']} ({data['biggest_cluster_size']} countries)", "🍲",
        ))
    if data.get("total_tourists") is not None:
        findings.append((
            f"Total annual tourists (of {int(data['tourists_n'])} countries)",
            f"{int(data['total_tourists']):,}", "✈️",
        ))

    cols = st.columns(3)
    for i, (title, value, icon) in enumerate(findings):
        with cols[i % 3]:
            cards.value_card(title, value, icon=icon)

