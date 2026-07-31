"""User-visible source citations (Req 19).

cite(section) renders the sources behind a section from section_source + source.
all_sources() backs the consolidated Sources & Credits page (Req 19.3).
"""
from __future__ import annotations

import pandas as pd

from data.db import run_query


def sources_for_section(section: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT s.name, s.reference_url
        FROM section_source ss
        JOIN source s ON s.source_id = ss.source_id
        WHERE ss.section = :section
        ORDER BY s.name
        """,
        {"section": section},
    )


def all_sources() -> pd.DataFrame:
    return run_query(
        "SELECT name, reference_url, precedence FROM source ORDER BY name"
    )


def cite(section: str) -> None:
    """Render a compact citation line for a data-driven section."""
    import streamlit as st

    try:
        df = sources_for_section(section)
    except Exception:  # noqa: BLE001 - never break a view over a citation
        return
    if df.empty:
        return
    parts = []
    for _, r in df.iterrows():
        if isinstance(r["reference_url"], str) and r["reference_url"]:
            parts.append(f"[{r['name']}]({r['reference_url']})")
        else:
            parts.append(r["name"])
    st.caption("Sources: " + " · ".join(parts))


def ai_badge() -> None:
    """Inline 'AI-assisted' indicator for AI-derived content (Req 21.3)."""
    import streamlit as st

    st.markdown('<span class="atw-badge">AI-assisted</span>', unsafe_allow_html=True)
