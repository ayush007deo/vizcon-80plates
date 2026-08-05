"""
DRAFT: Food & Sustainability Section
=====================================
This is a DRAFT for review — not connected to the app yet.

Section: "The Weight of a Plate"
Story: "Every meal has a footprint. The same foods that keep us healthy also keep the planet lighter."

Data sources:
- food_emissions.csv (Poore & Nemecek 2018, via Our World in Data) — CO2 per kg per food
- country_food_group table — % meat/veg/cereals per country  
- country_profile — life expectancy per country
- pipeline/raw/meat_consumption.csv — per-capita meat by country

Key discoveries:
- Beef emits 99x more CO2 per kg than lentils
- Countries with plant-heavy diets live ~3 years longer AND emit less
- The world's longest-lived cuisines (Japan, Italy, India) are also among the lightest on the planet
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import cards
from components.theme import PRIMARY, ACCENT, GOLD, TEXT_PRIMARY, TEXT_SECONDARY, FONT_STACK_UI
from data import repository as repo
from data.db import run_query


def render() -> None:
    cards.page_header("sustainability")  # Would need narrative added

    # === DISCOVERY HOOK ===
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
                A plate of beef emits 99× more CO₂ than a plate of lentils.
                The lightest plates on Earth are also the ones where people live longest.</div>
            <div style="font-size:0.9rem;color:#a7f3d0;margin-top:10px;">
                Poore & Nemecek (2018) · Science</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # === CHART 1: Emissions per food (horizontal bar) ===
    st.markdown("#### 🌍 Carbon footprint per kilogram of food")
    st.markdown('<p style="color:#574B42;font-size:0.9rem;">Some foods cost the planet 100x more than others.</p>', unsafe_allow_html=True)

    emissions = pd.read_csv("data/food_emissions.csv")
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
        hovertemplate="%{y}: %{x:.1f} kg CO₂eq/kg<extra></extra>",
    ))
    fig.update_layout(
        height=600, margin=dict(l=150, r=20, t=20, b=40),
        xaxis_title="kg CO₂-equivalents per kg of food",
        yaxis=dict(tickfont=dict(size=11)),
        plot_bgcolor="rgba(255,248,241,0.5)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Legend
    st.markdown(
        '<div style="display:flex;gap:16px;flex-wrap:wrap;font-size:0.8rem;color:#574B42;">'
        '<span>🔴 Meat</span><span>🟡 Dairy</span><span>🔵 Seafood</span>'
        '<span>🟢 Plant</span><span>🌾 Grain</span></div>',
        unsafe_allow_html=True,
    )

    # === INSIGHT CALLOUT ===
    beef_val = emissions[emissions["food"] == "Beef (beef herd)"]["ghg_kg"].iloc[0]
    lentil_val = emissions[emissions["food"] == "Lentils"]["ghg_kg"].iloc[0]
    ratio = beef_val / lentil_val
    cards.insight_callout(
        f"One kilogram of beef produces {ratio:.0f}× more greenhouse gases than one kilogram "
        f"of lentils — {beef_val:.0f} kg CO₂ vs {lentil_val:.1f} kg. "
        "Swapping one beef meal a week for lentils saves ~5,000 kg CO₂ a year per person."
    )

    st.divider()

    # === CHART 2: Plant-heavy countries live longer ===
    st.markdown("#### 🌿 Light plates, long lives")
    st.markdown('<p style="color:#574B42;font-size:0.9rem;">Countries where plants dominate the plate tend to live longer — and emit less.</p>', unsafe_allow_html=True)

    # Get meat % + life expectancy per country
    fg = run_query("SELECT iso3, food_group, pct FROM country_food_group WHERE food_group = 'Meat'")
    countries = run_query("SELECT iso3, name, life_expectancy, region FROM country_profile WHERE life_expectancy IS NOT NULL")
    merged = countries.merge(fg[["iso3", "pct"]].rename(columns={"pct": "meat_pct"}), on="iso3", how="inner")

    if not merged.empty:
        fig2 = go.Figure(go.Scatter(
            x=merged["meat_pct"],
            y=merged["life_expectancy"],
            mode="markers",
            marker=dict(
                size=8,
                color=merged["meat_pct"],
                colorscale=[[0, "#1F6F5C"], [0.5, "#E8A317"], [1, "#C0392B"]],
                showscale=True,
                colorbar=dict(title="Meat %", titleside="right"),
            ),
            text=merged["name"],
            hovertemplate="%{text}<br>Meat: %{x:.0f}%<br>Life exp: %{y:.0f} yrs<extra></extra>",
        ))
        fig2.update_layout(
            height=400, margin=dict(l=50, r=20, t=20, b=50),
            xaxis_title="% of diet from meat",
            yaxis_title="Life expectancy (years)",
            plot_bgcolor="rgba(255,248,241,0.5)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})

        # Stat comparison
        top_meat = merged.nlargest(20, "meat_pct")["life_expectancy"].mean()
        low_meat = merged.nsmallest(20, "meat_pct")["life_expectancy"].mean()
        c1, c2, c3 = st.columns(3)
        with c1:
            cards.big_stat("🥩 High-meat countries", f"{top_meat:.0f} yr avg life", icon="")
        with c2:
            cards.big_stat("🌱 Low-meat countries", f"{low_meat:.0f} yr avg life", icon="")
        with c3:
            cards.big_stat("📊 Correlation", f"{merged['meat_pct'].corr(merged['life_expectancy']):+.2f}", icon="")

        st.markdown(
            '<p style="color:#574B42;font-size:0.85rem;font-style:italic;">'
            'Note: this correlation reflects broader development factors — nations with '
            'better healthcare also tend to eat more meat. But the world\'s Blue Zone '
            'cultures (Japan, Sardinia, Okinawa) share one thing: plants first, meat sparingly.</p>',
            unsafe_allow_html=True,
        )

    st.divider()

    # === SPOTLIGHT: Sustainable Cuisines ===
    st.markdown("#### 🍽 The planet's lightest cuisines")
    st.markdown('<p style="color:#574B42;font-size:0.9rem;">These food cultures prove you can eat well, live long, and tread lightly.</p>', unsafe_allow_html=True)

    spotlights = [
        ("🇯🇵", "Japan", "Fish, rice, fermented soy, vegetables. Minimal beef. One of the world's longest-lived nations."),
        ("🇮🇳", "India", "30% of the world's vegetarians. Lentils, spices, and cereals power a billion plates."),
        ("🇬🇷", "Greece", "Mediterranean diet: olive oil, vegetables, legumes. Low meat, high longevity."),
    ]
    cols = st.columns(3)
    for col, (flag, name, desc) in zip(cols, spotlights):
        with col:
            st.markdown(
                f'<div style="background:#FFFFFF;border:1px solid #EFE6D8;border-radius:16px;'
                f'padding:18px;border-left:4px solid #1F6F5C;height:100%;">'
                f'<div style="font-size:1.8rem;">{flag}</div>'
                f'<div style="font-weight:800;font-size:1.1rem;color:#2A2320;margin:6px 0 4px 0;">{name}</div>'
                f'<div style="color:#574B42;font-size:0.88rem;line-height:1.4;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # === CLOSING NARRATIVE ===
    st.markdown(
        '<div style="background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;'
        'border-radius:16px;padding:20px 24px;margin-top:20px;">'
        '<p style="color:#166534;font-size:1rem;font-weight:600;margin:0;">'
        '🌱 The same plates that feed us longest also feed the planet lightest. '
        'Culture, not sacrifice, is the recipe for sustainability.</p></div>',
        unsafe_allow_html=True,
    )
