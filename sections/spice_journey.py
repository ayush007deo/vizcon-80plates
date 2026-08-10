"""Spice_Journey — follow a spice's route across centuries (Req 8, 17.2)."""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from components.narrative import insight
from data import repository as repo
from viz.routes import build_route_map

_PROMPT = "Choose a spice…"


def render() -> None:
    cards.page_header("spice_journey")
    body()


def body() -> None:
    try:
        spices = repo.list_spices()
    except Exception:  # noqa: BLE001
        st.warning("Spice journeys could not be loaded right now.")
        return

    if not spices:
        st.info("No spice journeys are available yet.")
        return

    choice = st.selectbox("Pick a spice", [_PROMPT] + spices, index=0)

    # Before a spice is chosen: prompt to select one (Req 8.4).
    if choice == _PROMPT:
        st.info("Select a spice to watch it travel across the centuries.")
        return

    steps = repo.get_spice_route(choice)
    # Selected spice has no recorded route -> unavailable message (Req 8.5).
    if steps.empty:
        st.info(f"The journey data for {choice} is unavailable.")
        return

    cards.insight_callout(insight("spice_journey", spice=choice))  # Req 17.2/17.4

    fig, alt = build_route_map(steps, subject=choice)  # ordered earliest->latest (Req 8.2)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(alt)  # Req 18.2

    # Each step with its time period (Req 8.3).
    st.markdown("#### Across the centuries")
    trail = " &nbsp; → &nbsp; ".join(
        f"<b>{r['location_name']}</b>"
        + (f" <span style='color:#9A8C7A'>({r['time_period']})</span>"
           if isinstance(r["time_period"], str) and r["time_period"] else "")
        for _, r in steps.iterrows()
    )
    st.markdown(trail, unsafe_allow_html=True)



def world_map_body() -> None:
    """The world's spice consumption today + a deeper analysis (FAOSTAT, CSV-derived)."""
    from data import spice_data as sp
    from viz import spice as viz

    years = [int(y) for y in sp.global_trend()["year"].tolist()]
    if not years:
        st.info("Spice-consumption data is not available yet.")
        return
    latest = years[-1]
    if len(years) > 1:
        year = st.select_slider(
            "Explore a year", options=years, value=latest,
            help="Drag to watch how the world's spice appetite shifts over time.",
            key="spice_year",
        )
    else:
        year = latest

    cards.insight_callout(insight("spice_map"))

    mp = sp.consumption_map(year)
    if not mp.empty:
        fig, alt = viz.build_spice_map(mp, year)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption(alt)

    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### The world's biggest spice consumers")
        top = sp.top_consumers(year, limit=12)
        if not top.empty:
            bfig, balt = viz.build_top_consumers(top, year)
            st.plotly_chart(bfig, width="stretch", config={"displayModeBar": False})
            st.caption(balt)
    with right:
        st.markdown("#### What the world seasons with")
        brk = sp.spice_breakdown(year)
        if not brk.empty:
            tfig, talt = viz.build_breakdown(brk, year)
            st.plotly_chart(tfig, width="stretch", config={"displayModeBar": False})
            st.caption(talt)

    st.divider()
    st.markdown("### Digging deeper into the world's spice appetite")

    # 1) The 30-year growing appetite.
    trend = sp.global_trend()
    if not trend.empty and len(trend) > 3:
        y0, y1 = trend.iloc[0], trend.iloc[-1]
        mult = (y1["consumption"] / y0["consumption"]) if y0["consumption"] else 0
        cards.insight_callout(
            f"The world's appetite for spice has grown about {mult:.1f}× since "
            f"{int(y0['year'])} — from {y0['consumption'] / 1e6:.1f}M to "
            f"{y1['consumption'] / 1e6:.1f}M tonnes a year.")
        st.markdown("#### A growing appetite (1993–%d)" % int(y1["year"]))
        tfig, talt = viz.build_trend(trend)
        st.plotly_chart(tfig, width="stretch", config={"displayModeBar": False})
        st.caption(talt)

    # 2) Which regions season the boldest.
    reg = sp.regional_intensity(year)
    if not reg.empty:
        st.markdown("#### Which regions season the boldest?")
        rfig, ralt = viz.build_regional_intensity(reg)
        st.plotly_chart(rfig, width="stretch", config={"displayModeBar": False})
        st.caption(ralt + " (Average per reporting country.)")

    # 3) Cross-dataset: spice vs. longevity.
    lon = sp.spice_vs_longevity(year)
    if lon and lon.get("tiers"):
        tiers = lon["tiers"]
        low, high = tiers.get("Low"), tiers.get("High")
        st.markdown("#### Do spice-loving nations live longer?")
        if low and high:
            cards.insight_callout(
                f"Across {lon['n']} countries, the third that season the most average "
                f"{high:.0f} years of life expectancy versus {low:.0f} for the third that "
                f"season the least — a positive pattern (correlation {lon['corr']:+.2f}). "
                "Spice isn't a cure, but bold, plant-and-spice-rich diets keep good company.")
        lfig, lalt = viz.build_longevity_tiers(lon)
        st.plotly_chart(lfig, width="stretch", config={"displayModeBar": False})
        st.caption(lalt + " Life expectancy: OWID. Correlation is not causation.")

