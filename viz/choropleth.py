"""Explore-map: a dark, interaction-first world map (Req 3).

build_explore_map returns (figure, alt_text). The map drops continent colors for a
neutral dark palette so *interaction* is the focus: every country with a food story
glows amber, a dozen featured cuisines carry a food icon, hovering reveals a rich
preview (dishes, festivals, a one-line personality), and clicking a country enters
its story. A `selected` country is highlighted in orange.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from components import theme

# Neutral palette — interaction over cartography.
_OCEAN = theme.NAVY            # deep navy
_LAND = "#2E3B47"             # dark slate land (no-story countries)
_BORDER = "rgba(255,255,255,0.22)"

# Featured cuisines: iso3 -> (emoji, personality tagline, lat, lon).
FEATURED: dict[str, tuple[str, str, float, float]] = {
    "IND": ("🍛", "Land of Spices", 22.0, 79.0),
    "ITA": ("🍕", "Mediterranean Kitchen", 42.8, 12.5),
    "JPN": ("🍣", "Home of Umami", 36.2, 138.2),
    "MEX": ("🌮", "Birthplace of Chocolate", 23.6, -102.5),
    "FRA": ("🥐", "The Art of the Table", 46.6, 2.2),
    "ESP": ("🥘", "Land of Paella", 40.0, -3.7),
    "CHN": ("🥟", "The Middle Kingdom's Table", 35.9, 104.2),
    "THA": ("🌶️", "Sweet, Sour & Spicy", 15.0, 101.0),
    "MAR": ("🫓", "Where Spice Routes Met", 31.8, -7.1),
    "BRA": ("☕", "Coffee & Carnival", -10.0, -55.0),
    "KOR": ("🍜", "The Kimchi Kingdom", 36.5, 127.9),
    "ETH": ("🫘", "Birthplace of Coffee", 9.1, 40.5),
    "GRC": ("🫒", "Olive & Sea", 39.0, 22.0),
    "VNM": ("🍜", "Street-Food Capital", 16.0, 106.0),
    "TUR": ("🥙", "Bridge of East & West", 39.0, 35.0),
    "PER": ("🥔", "Home of the Potato", -9.2, -75.0),
}


def _neighbor_names(df: pd.DataFrame) -> dict[str, str]:
    name_by_iso = dict(zip(df["iso3"], df["name"]))

    def names(nbrs) -> str:
        if not isinstance(nbrs, (list, tuple)) or len(nbrs) == 0:
            return "—"
        labels = [name_by_iso.get(n, n) for n in nbrs]
        return ", ".join(labels[:5]) + ("…" if len(labels) > 5 else "")

    return {row["iso3"]: names(row["neighbors"]) for _, row in df.iterrows()}


def build_explore_map(countries: pd.DataFrame, highlight=None, selected: str | None = None,
                      hover_stats: pd.DataFrame | None = None):
    df = countries.copy()
    df["has_story"] = df["has_story"].astype(bool)

    # Merge dish / festival counts for the hover preview.
    if hover_stats is not None and not hover_stats.empty:
        df = df.merge(hover_stats, on="iso3", how="left")
    for col in ("dishes", "festivals"):
        if col not in df.columns:
            df[col] = 0
    df[["dishes", "festivals"]] = df[["dishes", "festivals"]].fillna(0).astype(int)

    df["tagline"] = df["iso3"].map(lambda i: FEATURED[i][1] if i in FEATURED else "")
    df["borders"] = df["iso3"].map(_neighbor_names(df))
    df["cta"] = df["has_story"].map({True: "👉 Click to explore", False: "Coming soon"})

    # Base: every country one neutral land color.
    base = go.Choropleth(
        locations=df["iso3"], z=[0] * len(df), locationmode="ISO-3",
        colorscale=[[0, _LAND], [1, _LAND]], showscale=False,
        marker=dict(line=dict(color=_BORDER, width=0.5)),
        hoverinfo="skip",
    )

    # Story countries: warm amber glow (the invitation to click).
    story = df[df["has_story"]]
    story_layer = go.Choropleth(
        locations=story["iso3"], z=[1] * len(story), locationmode="ISO-3",
        text=story["name"],
        colorscale=[[0, "rgba(245,158,11,0.55)"], [1, "rgba(245,158,11,0.55)"]],
        showscale=False, marker=dict(line=dict(color=theme.AMBER_HI, width=0.8)),
        customdata=story[["tagline", "dishes", "festivals", "cta"]].values,
        hovertemplate=(
            "<b>%{text}</b>  <i>%{customdata[0]}</i><br>"
            "🍛 %{customdata[1]} dishes   🎉 %{customdata[2]} festivals<br>"
            "%{customdata[3]}<extra></extra>"
        ),
    )

    data = [base, story_layer]

    # Selected country: orange.
    if selected:
        data.append(go.Choropleth(
            locations=[selected], z=[1], locationmode="ISO-3",
            colorscale=[[0, theme.GRAD_A], [1, theme.GRAD_A]], showscale=False,
            marker=dict(line=dict(color="#FFFFFF", width=1.5)), hoverinfo="skip",
        ))

    # Food icons on featured cuisines.
    feat = [(i, *v) for i, v in FEATURED.items()]
    data.append(go.Scattergeo(
        lon=[f[4] for f in feat], lat=[f[3] for f in feat],
        text=[f[1] for f in feat], mode="text", textfont=dict(size=20),
        hoverinfo="skip",
    ))

    fig = go.Figure(data=data)
    fig.update_layout(
        template=theme.plotly_template(), height=440, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=0, b=0),
        geo=dict(
            projection=dict(type="natural earth"),
            showocean=True, oceancolor=_OCEAN,
            showland=True, landcolor=_LAND,
            showcountries=True, countrycolor=_BORDER,
            showframe=False, showcoastlines=True, coastlinecolor="rgba(245,158,11,0.30)",
            bgcolor="rgba(0,0,0,0)", lakecolor=_OCEAN,
        ),
        dragmode=False,
    )

    n_story = int(df["has_story"].sum())
    alt = f"Click any glowing country to explore its food story. {n_story} countries available."
    return fig, alt
