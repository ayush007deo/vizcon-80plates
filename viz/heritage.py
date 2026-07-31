"""Cultural-heritage visualizations (UNESCO World Heritage).

Two builders, each returning (figure, alt_text):
- build_heritage_map: a choropleth of heritage-site counts by country.
- build_heritage_tourism_scatter: heritage sites vs. tourist arrivals, colored by region,
  testing whether culture drives travel.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from components import theme


CATEGORY_COLORS = {"Cultural": "#B23A2E", "Natural": "#1F6F5C", "Mixed": "#8E6BB0"}


def build_sites_map(sites: pd.DataFrame) -> tuple[go.Figure, str]:
    """A world map of individual UNESCO sites, colored by category."""
    df = sites.copy()
    fig = px.scatter_geo(
        df, lat="latitude", lon="longitude", color="category",
        color_discrete_map=CATEGORY_COLORS, hover_name="name",
        custom_data=["country", "category", "year_inscribed"],
    )
    fig.update_traces(
        marker=dict(size=6, opacity=0.8, line=dict(width=0.3, color="#FFFFFF")),
        hovertemplate=("<b>%{hovertext}</b><br>%{customdata[0]}<br>"
                       "%{customdata[1]} · inscribed %{customdata[2]}<extra></extra>"),
    )
    fig.update_layout(
        template=theme.plotly_template(), height=520, legend_title_text="Category",
        margin=dict(l=0, r=0, t=0, b=0),
        geo=dict(projection=dict(type="natural earth"), showocean=True,
                 oceancolor="#DCEBF2", showland=True, landcolor="#F2E4C9",
                 showcountries=True, countrycolor="#FFFFFF", bgcolor="rgba(0,0,0,0)"),
    )
    n_cult = int((df["category"] == "Cultural").sum())
    alt = (
        f"A world map plotting {len(df)} UNESCO World Heritage sites as points colored by "
        f"category — {n_cult} cultural, plus natural and mixed sites."
    )
    return fig, alt


def build_heritage_map(points: pd.DataFrame) -> tuple[go.Figure, str]:
    df = points.copy()
    fig = go.Figure(
        go.Choropleth(
            locations=df["iso3"],
            z=df["heritage"],
            text=df["name"],
            locationmode="ISO-3",
            colorscale="YlOrBr",
            colorbar_title="Sites",
            marker=dict(line=dict(color="#FFFFFF", width=0.4)),
            hovertemplate="<b>%{text}</b><br>%{z} World Heritage sites<extra></extra>",
        )
    )
    fig.update_layout(
        template=theme.plotly_template(),
        height=460, margin=dict(l=0, r=0, t=0, b=0),
        geo=dict(projection=dict(type="natural earth"), showocean=True,
                 oceancolor="#DCEBF2", showcountries=True, countrycolor="#FFFFFF",
                 bgcolor="rgba(0,0,0,0)"),
    )
    top = df.sort_values("heritage", ascending=False).head(3)
    top_desc = ", ".join(f"{r['name']} ({int(r['heritage'])})" for _, r in top.iterrows())
    alt = (
        f"A world map shading {len(df)} countries by their number of UNESCO World "
        f"Heritage sites; the richest are {top_desc}."
    )
    return fig, alt


def build_heritage_tourism_scatter(points: pd.DataFrame) -> tuple[go.Figure, str]:
    df = points.copy()
    fig = px.scatter(
        df, x="heritage", y="annual_tourists", color="region",
        color_discrete_map=theme.REGION_COLORS, hover_name="name",
        labels={"heritage": "UNESCO World Heritage sites",
                "annual_tourists": "Annual tourist arrivals", "region": "Region"},
        custom_data=["region", "heritage", "annual_tourists"],
    )
    fig.update_traces(
        marker=dict(size=11, line=dict(width=0.5, color="#FFFFFF")),
        hovertemplate=("<b>%{hovertext}</b><br>Region: %{customdata[0]}<br>"
                       "Heritage sites: %{customdata[1]}<br>"
                       "Tourists/yr: %{customdata[2]:,}<extra></extra>"),
    )
    fig.update_layout(template=theme.plotly_template(), height=520,
                      legend_title_text="Region", margin=dict(l=10, r=10, t=10, b=10))

    corr_txt = ""
    if len(df) >= 5 and df["heritage"].nunique() > 1 and df["annual_tourists"].nunique() > 1:
        corr = df["heritage"].corr(df["annual_tourists"])
        if pd.notna(corr):
            corr_txt = f" Heritage and tourism correlate at {corr:+.2f}."
    alt = (
        f"A scatter of {len(df)} countries plotting UNESCO heritage sites against annual "
        "tourist arrivals, colored by region." + corr_txt
    )
    return fig, alt
