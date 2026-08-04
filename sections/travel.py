"""Travel & Tourism — an interactive analytics dashboard on world tourism (1999-2023).

Built directly from the world tourism-economy CSV (no database load) via
data.tourism_data. Interactive controls — a metric toggle, a year slider, an animated
year-sweep map, a country picker, and a *clickable* world map that reveals per-country
facts — let the reader explore, while data-derived callouts surface the surprising
findings: the COVID-19 collapse, who earns most per visitor, and which economies live
on tourism.
"""
from __future__ import annotations

import html

import streamlit as st

from components import cards, citation, lottie
from components.flags import flag
from components.narrative import insight
from data import repository as repo
from data import tourism_data as td
from viz import travel as viz


def _human(n: float | None) -> str:
    if n is None or (isinstance(n, float) and n != n):
        return "—"
    n = float(n)
    if abs(n) >= 1e9:
        return f"{n / 1e9:.1f}B"
    if abs(n) >= 1e6:
        return f"{n / 1e6:.1f}M"
    if abs(n) >= 1e3:
        return f"{n / 1e3:.0f}K"
    return f"{n:,.0f}"


def render() -> None:
    cards.page_header("travel")
    _compact_body()


def _compact_body() -> None:
    """A condensed travel section: just the COVID discovery + food-tourism link."""
    yrs = td.years()
    if not yrs:
        st.warning("Tourism data could not be loaded right now.")
        return

    lottie.show("travel", height=100)

    # The surprising discovery: the pandemic collapse
    cards.insight_callout(insight("travel"))
    impact = td.covid_impact()
    if impact.get("crash_pct") is not None:
        arr = impact["arrivals"]
        peak, trough = impact["peak_year"], impact["trough_year"]
        c1, c2, c3 = st.columns(3)
        with c1:
            cards.big_stat(f"Arrivals in {peak}", _human(arr.get(peak)), icon="🛬")
        with c2:
            cards.big_stat(f"Arrivals in {trough}", _human(arr.get(trough)), icon="🚫")
        with c3:
            cards.big_stat("One-year change", f"{impact['crash_pct']:.0f}%", icon="📉")

    # Country comparison chart — top food-culture nations over time
    st.markdown("#### 📈 How food nations fared")
    st.markdown('<p style="color:#574B42;font-size:0.9rem;">Tourist arrivals over time for countries with UNESCO-recognized cuisines.</p>', unsafe_allow_html=True)
    food_countries = ["FRA", "ESP", "ITA", "TUR", "MEX", "THA"]
    try:
        series = td.country_series(tuple(food_countries))
        if not series.empty:
            sfig, salt = viz.build_country_comparison(series, "arrivals")
            st.plotly_chart(sfig, width="stretch", config={"displayModeBar": False, "scrollZoom": False})
            st.caption(salt)
    except Exception:  # noqa: BLE001
        pass

    st.divider()

    # Tie it directly to food: which food-culture countries attract the most travelers
    st.markdown("#### 🍽 Food is why people travel")
    cards.insight_callout(insight("food_travel"))
    try:
        dests = repo.top_food_destinations(limit=6)
    except Exception:  # noqa: BLE001
        dests = None
    if dests is not None and not dests.empty:
        st.markdown('<p style="color:#574B42;font-size:0.9rem;">Countries whose cuisines are UNESCO-recognized consistently top the tourism charts. Food is not just a side dish to travel — it is the main course.</p>', unsafe_allow_html=True)
        cols = st.columns(min(len(dests), 6))
        for col, r in zip(cols, dests.to_dict("records")):
            with col:
                cards.big_stat(f"{flag(r['iso3'])} {r['name']}",
                               f"${_human(r['tourism_receipts'])}", icon="")



def _country_fact_card(iso3: str) -> None:
    """Rich click-to-reveal card summarizing one country's tourism story."""
    f = td.country_facts(iso3)
    if not f:
        st.info("No tourism data recorded for that country.")
        return
    chips: list[str] = []
    if f.get("peak_arrivals") is not None:
        chips.append(("🛬", f"{_human(f['peak_arrivals'])} visitors",
                      f"peak, {f['peak_year']}"))
    if f.get("latest_receipts") is not None:
        chips.append(("💰", f"${_human(f['latest_receipts'])}",
                      f"tourism receipts, {f['receipts_year']}"))
    if f.get("spend_per_visitor") is not None:
        chips.append(("💸", f"${_human(f['spend_per_visitor'])}", "per visitor"))
    if f.get("exports_pct") is not None:
        chips.append(("🧭", f"{f['exports_pct']:.0f}%", "of all exports is tourism"))

    inner = "".join(
        f'<div class="tv-fact"><div class="tv-fe">{e}</div>'
        f'<div class="tv-fb">{html.escape(big)}</div>'
        f'<div class="tv-fs">{html.escape(small)}</div></div>'
        for e, big, small in chips
    )
    st.markdown(
        f'<div class="tv-factcard"><div class="tv-facthead">{flag(iso3)} '
        f'{html.escape(f["name"])}<span>{html.escape(f.get("region") or "")}</span></div>'
        f'<div class="tv-factrow">{inner}</div></div>',
        unsafe_allow_html=True,
    )


def body() -> None:
    yrs = td.years()
    if not yrs:
        st.warning("Tourism data could not be loaded right now.")
        return

    lottie.show("travel", height=130)

    # ---- The surprising discovery: the pandemic collapse --------------------
    cards.insight_callout(insight("travel"))
    impact = td.covid_impact()
    if impact.get("crash_pct") is not None:
        arr = impact["arrivals"]
        peak, trough = impact["peak_year"], impact["trough_year"]
        c1, c2, c3 = st.columns(3)
        with c1:
            cards.big_stat(f"Arrivals in {peak}", _human(arr.get(peak)), icon="🛬")
        with c2:
            cards.big_stat(f"Arrivals in {trough}", _human(arr.get(trough)), icon="🚫")
        with c3:
            cards.big_stat("One-year change", f"{impact['crash_pct']:.0f}%", icon="📉")
        cfig, calt = viz.build_covid_bars(impact)
        st.plotly_chart(cfig, width="stretch", config={"displayModeBar": False})
        st.caption(calt + f" Panel of {impact.get('panel_n', 0)} countries reporting in both years.")

    st.divider()

    # ---- Shared control: which metric are we exploring? ---------------------
    metric_label = st.radio(
        "Explore by", ["Tourist arrivals", "Tourism receipts (US$)"],
        horizontal=True, key="travel_metric",
    )
    metric = "receipts" if "receipts" in metric_label.lower() else "arrivals"

    # ---- Global trend over time --------------------------------------------
    st.markdown("#### The rise — and sudden fall — of global travel")
    trend = td.global_trend()
    if not trend.empty:
        tfig, talt = viz.build_global_trend(trend, metric)
        st.plotly_chart(tfig, width="stretch", config={"displayModeBar": False})
        st.caption(talt)

    # ---- World map: explore a year (clickable) or watch it move -------------
    st.markdown("#### Where the world travels")
    tab_explore, tab_play = st.tabs(["🗺️ Explore a year", "▶️ Watch it move"])

    with tab_explore:
        default_year = 2019 if 2019 in yrs else int(yrs[-1])
        map_year = st.slider("Year", min_value=int(yrs[0]), max_value=int(yrs[-1]),
                             value=default_year, key="travel_map_year")
        points = td.choropleth(map_year, metric)
        if points.empty:
            st.info(f"No {metric} data for {map_year}. Try another year.")
        else:
            mfig, malt = viz.build_choropleth(points, metric, map_year)
            event = st.plotly_chart(mfig, width="stretch", on_select="rerun",
                                    key=f"travel_map_{metric}", config={"displayModeBar": False})
            st.caption("👆 " + malt)
            sel = (event or {}).get("selection", {}) or {}
            pts = sel.get("points", [])
            if pts:
                iso3 = pts[0].get("location") or pts[0].get("customdata")
                if iso3:
                    _country_fact_card(str(iso3))

    with tab_play:
        allpts = td.choropleth_all_years(metric)
        if allpts.empty:
            st.info("No data to animate.")
        else:
            afig, aalt = viz.build_animated_choropleth(allpts, metric)
            st.plotly_chart(afig, width="stretch", config={"displayModeBar": False})
            st.caption(aalt)

    # ---- Country comparison (multiselect) -----------------------------------
    st.markdown("#### Compare countries over time")
    all_countries = td.countries()
    name_to_iso = dict(zip(all_countries["name"], all_countries["iso3"]))
    defaults = [n for n in ["France", "United States", "Spain", "Thailand"]
                if n in name_to_iso][:4]
    picked = st.multiselect("Pick countries to compare", options=list(name_to_iso.keys()),
                            default=defaults, key="travel_compare")
    if picked:
        iso3s = tuple(name_to_iso[n] for n in picked)
        series = td.country_series(iso3s)
        if not series.empty:
            sfig, salt = viz.build_country_comparison(series, metric)
            st.plotly_chart(sfig, width="stretch", config={"displayModeBar": False})
            st.caption(salt)
    else:
        st.caption("Select one or more countries to chart their tourism over time.")

    st.divider()

    # ---- Rankings that reveal something ------------------------------------
    rank_year = st.session_state.get("travel_map_year", 2019 if 2019 in yrs else int(yrs[-1]))
    st.markdown(f"#### The leaders in {rank_year}")
    tab_top, tab_spend, tab_dep = st.tabs(
        ["🏆 Top destinations", "💸 Highest spend per visitor", "🧭 Economies built on tourism"]
    )

    with tab_top:
        top = td.top_destinations(rank_year, metric)
        if top.empty:
            st.info(f"No data for {rank_year}.")
        else:
            is_cur = metric == "receipts"
            label = "Tourism receipts (US$)" if is_cur else "Tourist arrivals"
            bfig, balt = viz.build_ranking_bar(
                top, "value", f"Top destinations {rank_year}", label, is_currency=is_cur)
            st.plotly_chart(bfig, width="stretch", config={"displayModeBar": False})
            st.caption(balt)

    with tab_spend:
        st.caption("Tourism receipts divided by arrivals — where each visitor spends the "
                   "most (countries with at least 1M arrivals).")
        spend = td.spend_per_visitor(rank_year)
        if spend.empty:
            st.info(f"No spend data for {rank_year}.")
        else:
            sfig, salt = viz.build_ranking_bar(
                spend, "spend_per_visitor", f"Spend per visitor {rank_year}",
                "US$ per visitor", is_currency=True)
            st.plotly_chart(sfig, width="stretch", config={"displayModeBar": False})
            st.caption(salt)
            lead = spend.iloc[0]
            cards.insight_callout(
                f"In {rank_year}, each international visitor to {lead['name']} spent about "
                f"${_human(lead['spend_per_visitor'])} on average — far above the typical "
                "destination.")

    with tab_dep:
        st.caption("Tourism as a share of a country's total exports — the economies most "
                   "reliant on travelers.")
        dep = td.dependence(rank_year)
        if dep.empty:
            st.info(f"No export-share data for {rank_year}.")
        else:
            dfig, dalt = viz.build_ranking_bar(
                dep, "exports_pct", f"Tourism dependence {rank_year}",
                "Tourism as % of exports")
            st.plotly_chart(dfig, width="stretch", config={"displayModeBar": False})
            st.caption(dalt)
            lead = dep.iloc[0]
            cards.insight_callout(
                f"For {lead['name']}, tourism made up {lead['exports_pct']:.0f}% of all "
                f"exports in {rank_year} — when travelers stay home, the whole economy feels it.")

    st.divider()

    # ---- Tie it back to food: the cultural driver of travel -----------------
    st.markdown("#### And it comes back to the table")
    cards.insight_callout(insight("food_travel"))
    try:
        dests = repo.top_food_destinations(limit=6)
    except Exception:  # noqa: BLE001
        dests = None
    if dests is not None and not dests.empty:
        st.caption("Countries whose cuisines are UNESCO-recognized, ranked by tourism receipts.")
        for col, r in zip(st.columns(len(dests)), dests.to_dict("records")):
            with col:
                cards.big_stat(f"{flag(r['iso3'])} {r['name']}",
                               f"${_human(r['tourism_receipts'])}", icon="🍽️")

