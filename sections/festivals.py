"""Festivals_View — 'Festivals Around the Table' month timeline (Req 9)."""
from __future__ import annotations

import calendar

import streamlit as st

from components import cards, citation
from data import repository as repo
from viz.timeline import build_month_timeline

MONTH_NAMES = [calendar.month_name[m] for m in range(1, 13)]


def render() -> None:
    cards.page_header("festivals")
    body()


def body() -> None:
    try:
        counts = repo.festival_counts_by_month()
    except Exception:  # noqa: BLE001
        st.warning("The festival calendar could not be loaded right now.")
        return

    # Month selector across all twelve months in order (Req 9.1).
    month_name = st.select_slider("Choose a month", options=MONTH_NAMES, value=MONTH_NAMES[0])
    month = MONTH_NAMES.index(month_name) + 1

    fig, alt = build_month_timeline(counts, month)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(alt)  # Req 18.2

    festivals = repo.get_festivals_by_month(month)

    # A month with no festivals -> message (Req 9.5).
    if festivals.empty:
        st.info(f"No festivals are recorded for {month_name}.")
        citation.cite("festivals")
        return

    st.markdown(f"#### Celebrating in {month_name}")
    # For each celebrating country: foods and annual tourists (Req 9.2, 9.3);
    # missing fields -> placeholder (Req 9.4).
    for _, row in festivals.iterrows():
        foods = list(row["traditional_foods"] or [])
        foods_html = (
            " ".join(
                f'<span style="background:#F2E9DA;border-radius:999px;padding:2px 10px;'
                f'margin:2px;display:inline-block">{f}</span>'
                for f in foods
            )
            if foods else cards.unavailable_html()
        )
        tourists = row["annual_tourists"]
        tourists_html = f"{int(tourists):,} visitors/yr" if tourists is not None \
            else cards.unavailable_html()
        body = (
            f"<b>{row['festival']}</b><br>"
            f"<div style='margin:6px 0'>{foods_html}</div>"
            f"<div style='color:#574B42'>✈️ {tourists_html}</div>"
        )
        cards.card(row["country"], body, icon="🎉")

    citation.cite("festivals")
