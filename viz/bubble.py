"""Food-vs-health bubble chart (Req 10).

build_health_bubble(points, group_label) plots a chosen food group's share of the
plate (x) against life expectancy (y), bubble size by population, color by region,
with a line of best fit so the "does food predict health?" relationship is visible.
Region is conveyed in the legend and hover (non-color channel, Req 18.5).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from components import theme


def build_health_bubble(points: pd.DataFrame,
                        group_label: str = "Vegetables") -> tuple["object", str]:
    df = points.copy()
    xlabel = f"{group_label} — share of the plate (%)"

    fig = px.scatter(
        df, x="supply", y="life_expectancy", size="population", color="region",
        color_discrete_map=theme.REGION_COLORS, hover_name="name", size_max=58,
        labels={"supply": xlabel, "life_expectancy": "Life expectancy (years)",
                "region": "Region", "population": "Population"},
        custom_data=["region", "supply", "life_expectancy", "population"],
    )
    fig.update_traces(
        marker=dict(opacity=0.82, line=dict(width=0.5, color="rgba(255,255,255,0.6)")),
        hovertemplate=(
            "<b>%{hovertext}</b><br>Region: %{customdata[0]}<br>"
            + group_label + " on the plate: %{customdata[1]:.0f}%<br>"
            "Life expectancy: %{customdata[2]:.0f} yrs<br>"
            "Population: %{customdata[3]:,}<extra></extra>"
        ),
    )

    # Line of best fit (numpy — no statsmodels dependency).
    corr = None
    d = df.dropna(subset=["supply", "life_expectancy"])
    if len(d) >= 3 and d["supply"].nunique() > 1 and d["life_expectancy"].nunique() > 1:
        corr = float(d["supply"].corr(d["life_expectancy"]))
        m, b = np.polyfit(d["supply"], d["life_expectancy"], 1)
        xs = np.linspace(d["supply"].min(), d["supply"].max(), 50)
        fig.add_trace(go.Scatter(
            x=xs, y=m * xs + b, mode="lines", name="Trend",
            line=dict(color=theme.PRIMARY, width=3, dash="dot"),
            hovertemplate="Trend line<extra></extra>", showlegend=False,
        ))

    fig.update_layout(
        template=theme.plotly_template(), height=560, legend_title_text="Region",
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(gridcolor="#EFE6D6"), xaxis=dict(gridcolor="#EFE6D6"),
    )
    corr_txt = f" The overall correlation is {corr:+.2f}." if corr is not None else ""
    alt = (f"A bubble chart of {len(df)} countries plotting {group_label.lower()} share of "
           "the plate against life expectancy; bubble size shows population, color shows "
           "region, and a dotted trend line shows the overall relationship." + corr_txt)
    return fig, alt
