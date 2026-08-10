"""Spice-consumption visuals (FAOSTAT 'Global spice consumption', CSV-derived).

Each builder returns (figure, alt_text). A log color scale keeps the map readable
despite China/India dwarfing everyone else.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from components import theme

_SCALE = [
    [0.0, "#FFF3D9"], [0.3, "#F6C453"], [0.6, "#E8892B"],
    [0.82, "#C0392B"], [1.0, "#7A1F3D"],
]
_GEO = dict(projection=dict(type="natural earth"), showocean=True, oceancolor="#EAF4F4",
            showland=True, landcolor="#F3ECDD", showcountries=True, countrycolor="#FFFFFF",
            showframe=False, coastlinecolor="#D8E6E6", bgcolor="rgba(0,0,0,0)")


def _fmt(n: float) -> str:
    n = float(n)
    if n >= 1e6:
        return f"{n / 1e6:.1f}M t"
    if n >= 1e3:
        return f"{n / 1e3:.0f}K t"
    return f"{n:,.0f} t"


def build_spice_map(df: pd.DataFrame, year: int) -> tuple[go.Figure, str]:
    """World map shaded by total spice consumption (log scale for readability)."""
    d = df.copy()
    d["logc"] = np.log10(d["consumption"].clip(lower=1))
    fig = go.Figure(go.Choropleth(
        locations=d["iso3"], z=d["logc"], text=d["name"], locationmode="ISO-3",
        customdata=d["consumption"], colorscale=_SCALE, showscale=False,
        marker=dict(line=dict(color="#FFFFFF", width=0.4)),
        hovertemplate="<b>%{text}</b><br>Spice consumed: %{customdata:,.0f} tonnes<extra></extra>",
    ))
    fig.update_layout(template=theme.plotly_template(), height=460,
                      margin=dict(l=0, r=0, t=0, b=0), geo=_GEO)
    top = df.sort_values("consumption", ascending=False).head(3)
    desc = ", ".join(f"{r['name']} ({_fmt(r['consumption'])})" for _, r in top.iterrows())
    alt = (f"A world map shading countries by total spice consumption in {year}; "
           f"the biggest are {desc}.")
    return fig, alt


def build_top_consumers(df: pd.DataFrame, year: int) -> tuple[go.Figure, str]:
    """Horizontal bar of the top spice-consuming nations, colored by region."""
    d = df.sort_values("consumption", ascending=True)
    colors = [theme.region_color(r) for r in d["region"]]
    fig = go.Figure(go.Bar(
        x=d["consumption"], y=d["name"], orientation="h",
        marker=dict(color=colors), text=[_fmt(v) for v in d["consumption"]],
        textposition="auto",
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} tonnes<extra></extra>",
    ))
    fig.update_layout(template=theme.plotly_template(), height=max(320, 32 * len(d)),
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis_title="Spice consumed (tonnes)", yaxis_title=None,
                      xaxis=dict(gridcolor="#EFE6D6"))
    lead = d.iloc[-1]
    alt = f"Top spice-consuming countries in {year}; {lead['name']} leads at {_fmt(lead['consumption'])}."
    return fig, alt


_PIE_COLORS = ["#C0392B", "#E8892B", "#F6C453", "#1F6F5C", "#4A72B0",
               "#8E6BB0", "#E9A03B", "#2A9D8F", "#7A1F3D"]


def build_breakdown(df: pd.DataFrame, year: int) -> tuple[go.Figure, str]:
    """Donut pie of global consumption by spice type — what the world seasons with."""
    d = df.sort_values("consumption", ascending=False).reset_index(drop=True)
    # Drop the uncategorized "Other spices" bucket (it dwarfs everything) so the pie
    # reveals the split among the *named* spices the world actually seasons with.
    named = d[d["item"] != "Other spices"].reset_index(drop=True)
    if len(named) >= 2:
        d = named
    colors = [_PIE_COLORS[i % len(_PIE_COLORS)] for i in range(len(d))]
    pull = [0.07 if i == 0 else 0.0 for i in range(len(d))]  # lift the leading spice
    total = float(d["consumption"].sum())

    fig = go.Figure(go.Pie(
        labels=d["item"], values=d["consumption"], hole=0.52, sort=False,
        direction="clockwise", pull=pull,
        marker=dict(colors=colors, line=dict(color="#FFF8F1", width=2)),
        textinfo="percent", textfont=dict(size=12, color="#2A2320"),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} tonnes<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        template=theme.plotly_template(), height=380,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="v", x=1.0, y=0.5, font=dict(size=11)),
        annotations=[dict(text=f"<b>{year}</b><br>{_fmt(total)}", x=0.5, y=0.5,
                          showarrow=False, font=dict(size=14, color="#574B42"))],
    )
    top = d.iloc[0]
    share = top["consumption"] / total * 100 if total else 0
    alt = (f"A donut chart of the world's named spices in {year} (excluding the "
           f"uncategorized 'other' bucket); {top['item']} leads at {share:.0f}%. "
           "Click a legend item to isolate a spice.")
    return fig, alt


def build_trend(df: pd.DataFrame) -> tuple[go.Figure, str]:
    """Global spice consumption over time — the world's growing appetite."""
    d = df.copy()
    fig = go.Figure(go.Scatter(
        x=d["year"], y=d["consumption"], mode="lines",
        line=dict(color=theme.PRIMARY, width=3, shape="spline"),
        fill="tozeroy", fillcolor="rgba(192,57,43,0.12)",
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} tonnes<extra></extra>",
    ))
    fig.update_layout(template=theme.plotly_template(), height=340,
                      margin=dict(l=10, r=10, t=10, b=10),
                      yaxis_title="Spice consumed (tonnes)", xaxis_title=None,
                      yaxis=dict(gridcolor="#EFE6D6"), xaxis=dict(dtick=5))
    y0, y1 = d.iloc[0], d.iloc[-1]
    mult = y1["consumption"] / y0["consumption"] if y0["consumption"] else 0
    alt = (f"An area chart of world spice consumption from {int(y0['year'])} to "
           f"{int(y1['year'])}, rising about {mult:.1f} times.")
    return fig, alt


def build_regional_intensity(df: pd.DataFrame) -> tuple[go.Figure, str]:
    """Average spice consumption per country, by region."""
    d = df.sort_values("avg_consumption", ascending=True)
    colors = [theme.region_color(r) for r in d["region"]]
    fig = go.Figure(go.Bar(
        x=d["avg_consumption"], y=d["region"], orientation="h",
        marker=dict(color=colors), text=[_fmt(v) for v in d["avg_consumption"]],
        textposition="auto",
        hovertemplate="<b>%{y}</b><br>Avg per country: %{x:,.0f} tonnes<extra></extra>",
    ))
    fig.update_layout(template=theme.plotly_template(), height=300,
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis_title="Avg spice consumed per country (tonnes)",
                      yaxis_title=None, xaxis=dict(gridcolor="#EFE6D6"))
    lead = d.iloc[-1]
    alt = f"Average spice consumption per country by region; {lead['region']} seasons the most."
    return fig, alt


def build_longevity_tiers(summary: dict) -> tuple[go.Figure, str]:
    """Average life expectancy across Low/Medium/High spice-consuming countries."""
    tiers = summary.get("tiers", {})
    order = ["Low", "Medium", "High"]
    xs = [t for t in order if t in tiers]
    ys = [tiers[t] for t in xs]
    fig = go.Figure(go.Bar(
        x=[f"{t} spice" for t in xs], y=ys,
        marker=dict(color=[theme.GOLD, theme.GRAD_B, theme.PRIMARY][:len(xs)]),
        text=[f"{v:.0f} yrs" for v in ys], textposition="outside",
        hovertemplate="<b>%{x}</b><br>Avg life expectancy: %{y:.1f} yrs<extra></extra>",
    ))
    fig.update_layout(template=theme.plotly_template(), height=340,
                      margin=dict(l=10, r=10, t=30, b=10),
                      yaxis_title="Avg life expectancy (years)",
                      yaxis=dict(gridcolor="#EFE6D6", range=[60, max(ys) + 4]),
                      xaxis=dict(showgrid=False), showlegend=False)
    alt = (f"A bar chart comparing average life expectancy across low, medium and high "
           f"spice-consuming countries ({summary.get('n', 0)} countries).")
    return fig, alt
