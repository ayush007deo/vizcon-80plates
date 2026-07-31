"""Flavor_Wheel — cluster countries by cuisine, not geography (Req 11)."""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from data import repository as repo
from viz.circle_pack import build_flavor_wheel


def render() -> None:
    cards.page_header("flavor_wheel")
    body()


def body() -> None:
    try:
        clusters = repo.get_clusters()  # iso3, country, cluster_name (Req 11.1, 11.4)
    except Exception:  # noqa: BLE001
        st.warning("The flavor wheel could not be loaded right now.")
        return

    if clusters.empty:
        st.info("Not enough food-profile data yet to group countries by cuisine.")
        citation.cite("flavor_wheel")
        return

    fig, alt = build_flavor_wheel(clusters)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(alt)  # descriptive alt text (Req 18.2)

    # Text list of clusters and members (non-color channel + accessibility, Req 18.5).
    st.markdown("#### Cuisine clusters")
    for cname, grp in clusters.groupby("cluster_name"):
        members = ", ".join(sorted(grp["country"]))
        st.markdown(f"**{cname}** — {members}")

    citation.cite("flavor_wheel")
