"""World Happiness Report visuals (CSV-derived). Each builder returns (figure, alt)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from components import theme

# Cool-to-warm "joy" scale (deep teal -> saffron -> paprika).
_SCALE = [
    [0.0, "#1F6F5C"], [0.4, "#7FB09B"], [0.65, "#F2C14E"],
    [0.85, "#F0932B"], [1.0, "#C0392B"],
]
_GEO = dict(projection=dict(type="natural earth"), showocean=True, oceancolor="#EAF4F4",
            showland=True, landcolor="#F3ECDD", showcountries=True, countrycolor="#FFFFFF",
            showframe=False, coastlinecolor="#D8E6E6", bgcolor="rgba(0,0,0,0)")


def build_happiness_map(df: pd.DataFrame, year: int) -> tuple[go.Figure, str]:
    """World map shaded by happiness (ladder) score, 0-10."""
    d = df.copy()
    fig = go.Figure(go.Choropleth(
        locations=d["iso3"], z=d["score"], text=d["country"], locationmode="ISO-3",
        colorscale=_SCALE, zmin=float(d["score"].min()), zmax=float(d["score"].max()),
        colorbar=dict(title="Score", thickness=12, len=0.7, outlinewidth=0),
        marker=dict(line=dict(color="#FFFFFF", width=0.4)),
        hovertemplate="<b>%{text}</b><br>Happiness score: %{z:.2f}<extra></extra>",
    ))
    fig.update_layout(template=theme.plotly_template(), height=460,
                      margin=dict(l=0, r=0, t=0, b=0), geo=_GEO)
    top = d.sort_values("score", ascending=False).head(3)
    desc = ", ".join(f"{r['country']} ({r['score']:.2f})" for _, r in top.iterrows())
    alt = (f"A world map shading countries by their {year} happiness score; "
           f"the happiest are {desc}.")
    return fig, alt


def build_factor_bars(factors: dict) -> tuple[go.Figure, str]:
    """Horizontal bar of what drives one country's happiness score."""
    items = sorted(factors["factors"].items(), key=lambda kv: kv[1])
    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    palette = [theme.GOLD, theme.ACCENT, theme.PRIMARY, "#4A72B0", "#8E6BB0", "#2A9D8F"]
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h",
        marker=dict(color=palette[:len(labels)]),
        text=[f"{v:.2f}" for v in vals], textposition="auto",
        hovertemplate="<b>%{y}</b><br>Contribution: %{x:.2f}<extra></extra>",
    ))
    fig.update_layout(template=theme.plotly_template(), height=300,
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis_title="Contribution to happiness score", yaxis_title=None,
                      xaxis=dict(gridcolor="#EFE6D6"))
    lead = max(factors["factors"].items(), key=lambda kv: kv[1])
    alt = (f"A bar chart of what drives {factors['country']}'s happiness; "
           f"{lead[0]} contributes most ({lead[1]:.2f}).")
    return fig, alt


def build_happiness_vs_life(df: pd.DataFrame) -> tuple[go.Figure, str]:
    """Scatter of happiness vs healthy life expectancy, colored by region."""
    import plotly.express as px

    d = df.dropna(subset=["life_exp", "score", "region"])
    fig = px.scatter(
        d, x="life_exp", y="score", color="region", hover_name="country",
        color_discrete_map=theme.REGION_COLORS,
        labels={"life_exp": "Healthy life expectancy (contribution)",
                "score": "Happiness score", "region": "Region"},
    )
    fig.update_traces(marker=dict(size=11, line=dict(width=0.5, color="#FFFFFF")))
    fig.update_layout(template=theme.plotly_template(), height=460,
                      margin=dict(l=10, r=10, t=10, b=10), legend_title_text="Region")
    corr = d["life_exp"].corr(d["score"]) if len(d) >= 5 else None
    tail = f" They move together (correlation {corr:+.2f})." if corr is not None and corr == corr else ""
    alt = (f"A scatter of {len(d)} countries plotting happiness against healthy life "
           f"expectancy, colored by region.{tail}")
    return fig, alt
