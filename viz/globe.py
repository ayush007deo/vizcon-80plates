"""Rotating, hoverable globe for the Home page (Req 2.5-2.8).

build_globe returns (figure, alt_text). It uses a choropleth on an orthographic
projection (Plotly's built-in ISO-3 country geometries, so no centroid data is
needed). Countries are filled and colored by world region; animation frames step the
projection longitude so the globe rotates continuously without user input (Req 2.6).
Hovering a country highlights it and moving away restores it (Plotly default) (Req 2.7-2.8).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from components import theme


def build_globe(countries: pd.DataFrame, n_frames: int = 36,
                spin: bool = True) -> tuple[go.Figure, str]:
    """Build an orthographic globe choropleth of countries colored by region.

    countries: DataFrame with iso3, name, region.
    spin: when True, add rotation frames + a "Spin the globe" button (decorative).
          when False, a still, drag-to-rotate globe — better for clicking a country.
    """
    df = countries.copy()
    regions = sorted(r for r in df["region"].dropna().unique())
    region_index = {r: i for i, r in enumerate(regions)}
    df["_z"] = df["region"].map(region_index).fillna(-1)

    # Discrete colorscale mapping each region index to its fixed region color.
    n = max(1, len(regions))
    colorscale = []
    for i, r in enumerate(regions):
        lo, hi = i / n, (i + 1) / n
        colorscale.append([lo, theme.region_color(r)])
        colorscale.append([hi, theme.region_color(r)])

    trace = go.Choropleth(
        locations=df["iso3"],
        z=df["_z"],
        text=df["name"],
        customdata=df["region"].fillna("Unknown"),
        locationmode="ISO-3",
        colorscale=colorscale or [[0, theme.REGION_FALLBACK], [1, theme.REGION_FALLBACK]],
        showscale=False,
        marker=dict(line=dict(color="#FFFFFF", width=0.4)),
        hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>",
    )
    fig = go.Figure(data=[trace])

    updatemenus = []
    if spin:
        fig.frames = [
            go.Frame(
                name=str(i),
                layout=go.Layout(
                    geo=dict(projection=dict(rotation=dict(lon=(360 / n_frames) * i, lat=12)))
                ),
            )
            for i in range(n_frames)
        ]
        updatemenus = [
            dict(
                type="buttons",
                showactive=False,
                x=0.5, y=0.0, xanchor="center",
                bgcolor="#B23A2E", bordercolor="#B23A2E",
                font=dict(color="#FFFFFF", size=13),
                buttons=[
                    dict(
                        label="▶  Spin the globe",
                        method="animate",
                        args=[None, dict(
                            frame=dict(duration=90, redraw=True),
                            transition=dict(duration=0),
                            fromcurrent=True,
                            mode="immediate",
                        )],
                    )
                ],
            )
        ]

    fig.update_layout(
        template=theme.plotly_template(),
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        paper_bgcolor="rgba(0,0,0,0)",
        dragmode="orbit",  # drag to rotate the globe (no chasing a spinner)
        geo=dict(
            projection=dict(type="orthographic", rotation=dict(lon=0, lat=12)),
            showocean=True, oceancolor="#0E2A38",          # deep night-ocean
            showland=True, landcolor="#26424E",
            showcountries=True, countrycolor="rgba(255,255,255,0.65)",
            showcoastlines=True, coastlinecolor="#3C6373",
            showframe=False,
            bgcolor="rgba(0,0,0,0)",
            lataxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            lonaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        ),
        updatemenus=updatemenus,
    )

    motion = "rotating" if spin else "drag-to-rotate"
    alt = (
        f"A {motion} globe of {len(df)} countries, each filled and colored by its world "
        "region; hovering a country reveals its name and region."
    )
    return fig, alt
