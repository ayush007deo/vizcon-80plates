"""Food & Sustainability — The Weight of a Plate."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import cards
from data.db import run_query


_EMISSIONS_CSV = Path(__file__).resolve().parents[1] / "data" / "food_emissions.csv"


def render() -> None:
    cards.page_header("sustainability")

    # Discovery hook
    st.markdown(
        """
        <div class="atw-dark-card" style="background:linear-gradient(135deg,#1a4a3a 0%,#0d2e1f 100%);
            border-radius:20px;padding:28px 32px;margin:0 0 20px 0;
            box-shadow:0 16px 40px rgba(13,46,31,0.30);position:relative;overflow:hidden;">
            <div style="position:absolute;right:20px;top:50%;transform:translateY(-50%);
                font-size:4rem;opacity:0.15;">🌱</div>
            <div style="font-weight:700;font-size:0.7rem;text-transform:uppercase;
                letter-spacing:0.12em;color:#4ade80;margin-bottom:8px;">✦ The weight of a plate</div>
            <div style="font-family:'Playfair Display',Georgia,serif;font-weight:800;
                font-size:1.5rem;color:#FFFFFF;line-height:1.3;max-width:700px;">
                A plate of beef emits 99x more CO2 than a plate of lentils.
                The lightest plates on Earth are also the ones where people live longest.</div>
            <div style="font-size:0.9rem;color:#a7f3d0;margin-top:10px;">
                Poore & Nemecek (2018) - Science</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Chart 1: Emissions per food
    st.markdown("#### Carbon footprint per kilogram of food")
    st.markdown('<p style="color:#574B42;font-size:0.9rem;">Some foods cost the planet 100x more than others.</p>', unsafe_allow_html=True)

    try:
        emissions = pd.read_csv(_EMISSIONS_CSV)

        # Interactive: let the viewer filter which food categories to compare.
        all_cats = ["Meat", "Dairy", "Seafood", "Grain", "Plant", "Other"]
        cats = [c for c in all_cats if c in set(emissions["category"])]
        chosen = st.multiselect(
            "Show food groups", cats, default=cats,
            help="Add or remove categories to compare what you like.",
            key="emis_cats",
        )
        if chosen:
            emissions = emissions[emissions["category"].isin(chosen)]
        emissions = emissions.sort_values("ghg_kg", ascending=True)

        colors = emissions["category"].map({
            "Meat": "#C0392B", "Dairy": "#E8A317", "Seafood": "#4A72B0",
            "Grain": "#2A9D8F", "Plant": "#1F6F5C", "Other": "#574B42"
        })

        fig = go.Figure(go.Bar(
            x=emissions["ghg_kg"],
            y=emissions["food"],
            orientation="h",
            marker=dict(color=colors.tolist()),
            hovertemplate="%{y}: %{x:.1f} kg CO2eq/kg<extra></extra>",
        ))
        fig.update_layout(
            height=600, margin=dict(l=150, r=20, t=20, b=40),
            xaxis_title="kg CO2-equivalents per kg of food",
            yaxis=dict(tickfont=dict(size=11)),
            plot_bgcolor="rgba(255,248,241,0.5)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False})

        st.markdown(
            '<div style="display:flex;gap:16px;flex-wrap:wrap;font-size:0.8rem;color:#574B42;">'
            '<span style="color:#C0392B;">&#9679; Meat</span>'
            '<span style="color:#E8A317;">&#9679; Dairy</span>'
            '<span style="color:#4A72B0;">&#9679; Seafood</span>'
            '<span style="color:#1F6F5C;">&#9679; Plant</span>'
            '<span style="color:#2A9D8F;">&#9679; Grain</span></div>',
            unsafe_allow_html=True,
        )

        # Compute the headline comparison from the full data so it's stable regardless
        # of which categories are currently filtered in the chart above.
        _full = pd.read_csv(_EMISSIONS_CSV)
        _beef = _full[_full["food"] == "Beef (beef herd)"]["ghg_kg"]
        _lentil = _full[_full["food"] == "Lentils"]["ghg_kg"]
        if not _beef.empty and not _lentil.empty and float(_lentil.iloc[0]) > 0:
            beef_val, lentil_val = float(_beef.iloc[0]), float(_lentil.iloc[0])
            cards.insight_callout(
                f"One kilogram of beef produces {beef_val/lentil_val:.0f}x more greenhouse "
                f"gases than one kilogram of lentils ({beef_val:.0f} kg CO2 vs "
                f"{lentil_val:.1f} kg)."
            )
    except Exception as e:
        st.warning(f"Emissions chart could not be loaded: {e}")

    st.divider()

    # Chart 2: Plant-heavy countries live longer
    st.markdown("#### Light plates, long lives")
    st.markdown('<p style="color:#574B42;font-size:0.9rem;">Average lifespan across meat-consumption tiers. The climb tracks wealth as much as diet — yet the world&rsquo;s longevity hotspots all eat meat sparingly.</p>', unsafe_allow_html=True)

    try:
        fg = run_query("SELECT iso3, pct FROM country_food_group WHERE food_group = 'Meat'")
        countries = run_query("SELECT iso3, name, life_expectancy FROM country_profile WHERE life_expectancy IS NOT NULL")
        merged = countries.merge(fg.rename(columns={"pct": "meat_pct"}), on="iso3", how="inner")
        merged = merged.dropna(subset=["meat_pct", "life_expectancy"])

        if not merged.empty and len(merged) > 10:
            # Group countries into meat-consumption tiers and show the average
            # lifespan of each — clearer and more informative than a dot cloud.
            m = merged.copy()
            m["meat_pct"] = m["meat_pct"].astype(float)
            m["life_expectancy"] = m["life_expectancy"].astype(float)
            edges = [0, 5, 10, 15, 20, 999]
            labels = ["Under 5%", "5–10%", "10–15%", "15–20%", "Over 20%"]
            m["tier"] = pd.cut(m["meat_pct"], bins=edges, labels=labels, right=False)
            agg = (m.groupby("tier", observed=True)
                     .agg(avg_life=("life_expectancy", "mean"), n=("iso3", "count"))
                     .reindex(labels).dropna().reset_index())

            tier_color = {"Under 5%": "#1F6F5C", "5–10%": "#5B8C3E", "10–15%": "#E8A317",
                          "15–20%": "#D9772B", "Over 20%": "#C0392B"}
            bar_colors = [tier_color[t] for t in agg["tier"]]

            fig2 = go.Figure(go.Bar(
                x=agg["tier"], y=agg["avg_life"],
                marker=dict(color=bar_colors, line=dict(width=0)),
                text=[f"{v:.0f}" for v in agg["avg_life"]],
                textposition="outside",
                textfont=dict(size=18, color="#2A2320", family="Playfair Display"),
                customdata=agg["n"],
                hovertemplate=("Meat = %{x} of the plate<br>"
                               "Average life expectancy: %{y:.1f} yrs<br>"
                               "%{customdata} countries<extra></extra>"),
            ))
            # Country counts sitting just above each bar's base.
            for _, r in agg.iterrows():
                fig2.add_annotation(x=r["tier"], y=0, yshift=16,
                                    text=f"{int(r['n'])} countries", showarrow=False,
                                    font=dict(size=11, color="#FFFFFF"))
            ymax = float(agg["avg_life"].max())
            fig2.update_layout(
                height=430, margin=dict(l=50, r=20, t=30, b=50),
                xaxis_title="Share of the everyday plate that is meat",
                yaxis_title="Avg life expectancy (years)",
                yaxis=dict(range=[0, ymax * 1.15], gridcolor="#EFE6D6"),
                xaxis=dict(tickfont=dict(size=13)),
                plot_bgcolor="rgba(255,248,241,0.5)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                bargap=0.28,
            )
            st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False, "scrollZoom": False})

            top_meat = float(merged.nlargest(20, "meat_pct")["life_expectancy"].mean())
            low_meat = float(merged.nsmallest(20, "meat_pct")["life_expectancy"].mean())
            corr = float(merged["meat_pct"].astype(float).corr(merged["life_expectancy"].astype(float)))

            c1, c2, c3 = st.columns(3)
            with c1:
                cards.big_stat("High-meat countries", f"{top_meat:.0f} yr avg", icon="🥩")
            with c2:
                cards.big_stat("Low-meat countries", f"{low_meat:.0f} yr avg", icon="🌱")
            with c3:
                cards.big_stat("Correlation", f"{corr:+.2f}", icon="📊")

            st.markdown(
                '<p style="color:#574B42;font-size:0.85rem;font-style:italic;">'
                'Note: this reflects broader development factors. But Blue Zone cultures '
                '(Japan, Sardinia, Okinawa) share one thing: plants first, meat sparingly.</p>',
                unsafe_allow_html=True,
            )
    except Exception as e:
        st.warning(f"Scatter chart could not be loaded: {e}")

    st.divider()

    # Spotlight: Sustainable cuisines
    st.markdown("#### The planet's lightest cuisines")

    spotlights = [
        ("\U0001f1ef\U0001f1f5", "Japan", "Fish, rice, fermented soy, vegetables. Minimal beef. One of the longest-lived nations."),
        ("\U0001f1ee\U0001f1f3", "India", "30% of the world's vegetarians. Lentils, spices, and cereals power a billion plates."),
        ("\U0001f1ec\U0001f1f7", "Greece", "Mediterranean diet: olive oil, vegetables, legumes. Low meat, high longevity."),
    ]
    cols = st.columns(3)
    for col, (flg, name, desc) in zip(cols, spotlights):
        with col:
            st.markdown(
                f'<div style="background:#FFFFFF;border:1px solid #EFE6D8;border-radius:16px;'
                f'padding:18px;border-left:4px solid #1F6F5C;height:100%;">'
                f'<div style="font-size:1.8rem;">{flg}</div>'
                f'<div style="font-weight:800;font-size:1.1rem;color:#2A2320;margin:6px 0 4px 0;">{name}</div>'
                f'<div style="color:#574B42;font-size:0.88rem;line-height:1.4;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div style="background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;'
        'border-radius:16px;padding:20px 24px;margin-top:20px;">'
        '<p style="color:#166534;font-size:1rem;font-weight:600;margin:0;">'
        'The same plates that feed us longest also feed the planet lightest. '
        'Culture, not sacrifice, is the recipe for sustainability.</p></div>',
        unsafe_allow_html=True,
    )
