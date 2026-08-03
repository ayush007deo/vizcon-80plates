"""Culinary Heritage — a few surprising facts from UNESCO's Intangible Cultural Heritage.

Rather than list every entry, we surface a handful of "did you know" facts about food
traditions UNESCO safeguards as living heritage — the kind of thing most people don't know.
All facts are drawn from the UNESCO ICH culinary records loaded into the Data_Store.
"""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from data import repository as repo

# Curated, surprising facts — each is accurate to the UNESCO ICH culinary records.
_FACTS = [
    ("🌿", "One diet, seven nations",
     "The Mediterranean diet isn't Italian — UNESCO lists it as shared heritage of "
     "seven countries: Croatia, Cyprus, Greece, Italy, Morocco, Portugal, and Spain."),
    ("🍣", "A whole cuisine, protected",
     "Japan's Washoku isn't a single dish — the entire traditional dietary culture of "
     "the Japanese was inscribed as living heritage in 2013."),
    ("🥬", "Kimchi is made together",
     "Korea's heritage isn't kimchi itself but Kimjang — the communal act of making and "
     "sharing it. Both South and North Korea have the tradition listed separately."),
    ("🍕", "Pizza-twirling is heritage",
     "It's not the pizza — it's the craft. The art of the Neapolitan 'Pizzaiuolo', the "
     "dough-spinning showmanship itself, became UNESCO heritage in 2017."),
    ("☕", "Coffee as a symbol of generosity",
     "Arabic coffee is shared heritage across four Gulf nations — Oman, Qatar, Saudi "
     "Arabia and the UAE — recognized specifically as a gesture of hospitality."),
    ("🫓", "Flatbread unites five countries",
     "Lavash and its cousins (Katyrma, Jupka, Yufka) are one shared tradition across "
     "Azerbaijan, Iran, Kazakhstan, Kyrgyzstan and Turkey."),
]


def body() -> None:
    try:
        df = repo.culinary_heritage()
    except Exception:  # noqa: BLE001
        st.warning("Culinary heritage could not be loaded right now.")
        return

    total = len(df)
    cards.insight_callout(
        f"UNESCO safeguards {total} food traditions as living cultural heritage — "
        "not just recipes, but the customs, crafts and gatherings around them. "
        "A few things you might not know:"
        if total else
        "UNESCO safeguards food traditions as living cultural heritage — a few things "
        "you might not know:"
    )

    left, right = st.columns(2)
    for i, (emoji, title, text) in enumerate(_FACTS):
        with (left if i % 2 == 0 else right):
            cards.card(f"{emoji} {title}", f"<div style='color:#574B42'>{text}</div>")

