"""The World's Happiest Tables — World Happiness Report, tied to food culture.

CSV-derived (no database). Shows where the world feels best, lets you inspect what
drives a country's happiness, and connects it to food via each nation's signature
dish. Framed honestly: we show what the data says, not spurious food-causes-joy claims.
"""
from __future__ import annotations

import streamlit as st

from components import cards, citation
from components.flags import flag
from components.narrative import insight
from data import wellbeing_data as wb
from viz import wellbeing as viz


def body() -> None:
    df = wb.happiness()
    if df.empty:
        st.info("World Happiness Report data is not available yet.")
        return
    year = wb.latest_year()

    cards.insight_callout(insight("happiness"))

    # Map of happiness scores.
    mfig, malt = viz.build_happiness_map(df, year)
    st.plotly_chart(mfig, width="stretch", config={"displayModeBar": False})
    st.caption(malt)

    # The happiest tables — top nations with their signature dish.
    st.markdown("#### The world's happiest tables")
    st.caption("The happiest-ranked nations — and a dish you'd find on their table.")
    from components.images import get_food_image
    from data import repository as repo

    top = wb.happiest(5)
    cols = st.columns(len(top))
    for col, (_, r) in zip(cols, top.iterrows()):
        with col:
            iso3 = r["iso3"]
            dish = None
            try:
                sig = repo.signature_dish_for(iso3, ())
                dish = sig["dish"] if sig else None
            except Exception:  # noqa: BLE001
                dish = None
            img = get_food_image(dish, f"{r['country']} cuisine", r["country"]) if dish else None
            if img:
                st.image(img[0], width="stretch")
            cards.big_stat(f"{flag(iso3)} {r['country']}", f"{r['score']:.2f}", icon="😊")
            if dish:
                st.caption(f"On the table: {dish}")

    # What makes a country happy? (factor breakdown, straight from the data)
    st.markdown("#### What makes a country happy?")
    names = df.sort_values("score", ascending=False)["country"].tolist()
    pick = st.selectbox("Inspect a country", names, index=0)
    row = df[df["country"] == pick]
    if not row.empty:
        f = wb.factors(row.iloc[0]["iso3"])
        if f and f.get("factors"):
            ffig, falt = viz.build_factor_bars(f)
            st.plotly_chart(ffig, width="stretch", config={"displayModeBar": False})
            st.caption(falt)

    # Honest correlation: happiness vs healthy life expectancy.
    st.markdown("#### Longer, healthier lives — and happiness")
    sfig, salt = viz.build_happiness_vs_life(df)
    st.plotly_chart(sfig, width="stretch", config={"displayModeBar": False})
    st.caption(salt)

    citation.cite("happiness")
