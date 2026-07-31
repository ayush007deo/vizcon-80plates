"""Sources & Credits — consolidated list of every data source (Req 19.3)."""
from __future__ import annotations

import streamlit as st

from components import cards
from components.theme import TEXT_SECONDARY
from data import repository as repo  # noqa: F401 - kept for symmetry
from components import citation


def render() -> None:
    cards.page_header("sources")

    try:
        sources = citation.all_sources()
    except Exception:  # noqa: BLE001
        st.warning("The source list could not be loaded right now.")
        return

    if sources.empty:
        st.info("No sources are recorded yet.")
        return

    st.caption(
        "Every figure in this journey traces back to a public dataset. "
        "All data is used under its original open license and cited below."
    )
    for _, r in sources.iterrows():
        url = r["reference_url"]
        if isinstance(url, str) and url:
            body = f'<a href="{url}" target="_blank">{url}</a>'
        else:
            body = "Reference location not recorded."
        cards.card(r["name"], body, icon="📚")

    st.caption(
        "Curated storytelling data (ingredient migrations, spice routes, festivals, "
        "and dinner symbolism) was compiled by the project team from public references."
    )
    st.caption(
        "Dish photographs are sourced from the Kaggle Food Ingredients & Recipes dataset "
        "(CC BY-SA 3.0) and from Wikipedia / Wikimedia Commons (CC BY-SA), used with "
        "attribution."
    )

    # --- How this was built with AI (Best Use of GenAI) --------------------
    st.markdown("### 🤖 How this was built with AI")
    st.caption(
        "Generative AI was used as a collaborator throughout, always over trusted public "
        "data — every number still traces to a cited source above."
    )
    ai_uses = [
        ("🧹 Data discovery & cleaning",
         "Reconciling country names to ISO-3 codes across FAOSTAT, World Bank, UNESCO and "
         "OWID, filtering World-Bank aggregate rows, and normalizing food groups."),
        ("📊 Code generation for visuals",
         "Drafting the Plotly choropleths, the rotating globe, the animated tourism map, "
         "and the CSS-only animated KPI counters."),
        ("🧮 Analysis & derived metrics",
         "Computing cuisine-similarity (Jaccard), clustering countries into flavor families, "
         "spend-per-visitor, and the COVID-era tourism-collapse panel."),
        ("✍️ Narrative & insight drafting",
         "Turning each dataset into a data-derived 'Did you know?' line and the storytelling "
         "copy that guides the journey."),
    ]
    left, right = st.columns(2)
    for i, (title, text) in enumerate(ai_uses):
        with (left if i % 2 == 0 else right):
            cards.card(title, f"<div style='color:{TEXT_SECONDARY}'>{text}</div>")
    st.caption(
        "AI-assisted figures are labeled with an “AI-assisted” badge where they appear. "
        "All source data is used under its original open license."
    )
