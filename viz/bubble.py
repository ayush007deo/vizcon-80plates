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


def build_diet_longevity_dumbbell(points: pd.DataFrame,
                                  group_label: str = "Vegetables") -> tuple["object", str]:
    """Within each region, compare life expectancy of the higher- vs lower-consumers
    of a food group. A dumbbell (two connected dots per region) isolates the diet
    signal from regional wealth differences far better than a raw scatter.
    """
    df = points.dropna(subset=["supply", "life_expectancy", "region"]).copy()

    rows = []
    for region, g in df.groupby("region"):
        if len(g) < 4:  # too few countries to split meaningfully
            continue
        g_sorted = g.sort_values("supply")
        half = len(g_sorted) // 2
        low = g_sorted.head(half)
        high = g_sorted.tail(len(g_sorted) - half)
        rows.append({
            "region": region,
            "low_life": float(low["life_expectancy"].mean()),
            "high_life": float(high["life_expectancy"].mean()),
            "n": int(len(g)),
        })
    dfr = pd.DataFrame(rows)
    if dfr.empty:
        fig = go.Figure()
        fig.update_layout(template=theme.plotly_template(), height=200,
                          annotations=[dict(text="Not enough data to compare regions.",
                                            showarrow=False, x=0.5, y=0.5,
                                            xref="paper", yref="paper")])
        return fig, "Not enough data to compare regions."

    dfr["gap"] = dfr["high_life"] - dfr["low_life"]
    dfr = dfr.sort_values("high_life").reset_index(drop=True)

    low_color = "#C9A15B"     # muted amber — eats least
    high_color = theme.ACCENT  # deep teal — eats most

    # Connectors (one grey line per region, drawn as a single trace with gaps).
    cx, cy = [], []
    for _, r in dfr.iterrows():
        cx += [r["low_life"], r["high_life"], None]
        cy += [r["region"], r["region"], None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cx, y=cy, mode="lines", line=dict(color="#D8C9B4", width=4),
        hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=dfr["low_life"], y=dfr["region"], mode="markers",
        name=f"Eats least {group_label.lower()}",
        marker=dict(size=18, color=low_color, line=dict(width=2, color="#FFFFFF")),
        customdata=dfr["n"],
        hovertemplate=("<b>%{y}</b><br>Lower-" + group_label.lower() +
                       " countries: %{x:.1f} yrs<br>%{customdata} countries<extra></extra>"),
    ))
    fig.add_trace(go.Scatter(
        x=dfr["high_life"], y=dfr["region"], mode="markers",
        name=f"Eats most {group_label.lower()}",
        marker=dict(size=18, color=high_color, line=dict(width=2, color="#FFFFFF")),
        customdata=dfr["n"],
        hovertemplate=("<b>%{y}</b><br>Higher-" + group_label.lower() +
                       " countries: %{x:.1f} yrs<br>%{customdata} countries<extra></extra>"),
    ))

    # Gap labels beside the rightmost dot of each region.
    for _, r in dfr.iterrows():
        gap = r["gap"]
        x = max(r["low_life"], r["high_life"])
        fig.add_annotation(
            x=x, y=r["region"], text=f"{gap:+.1f} yr", showarrow=False,
            xshift=42, font=dict(size=11, color=(high_color if gap >= 0 else theme.PRIMARY),
                                 family=theme.FONT_STACK_UI),
        )

    xmin = float(min(dfr["low_life"].min(), dfr["high_life"].min()))
    xmax = float(max(dfr["low_life"].max(), dfr["high_life"].max()))
    fig.update_layout(
        template=theme.plotly_template(), height=90 + 70 * len(dfr),
        margin=dict(l=10, r=70, t=10, b=30),
        xaxis=dict(title="Average life expectancy (years)", gridcolor="#EFE6D6",
                   range=[xmin - 3, xmax + 4]),
        yaxis=dict(title="", gridcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        plot_bgcolor="rgba(255,248,241,0.5)", paper_bgcolor="rgba(0,0,0,0)",
    )

    higher = int((dfr["gap"] > 0).sum())
    alt = (f"A dumbbell chart comparing, within each of {len(dfr)} world regions, the average "
           f"life expectancy of countries that eat more {group_label.lower()} versus those "
           f"that eat less. In {higher} of {len(dfr)} regions the higher-{group_label.lower()} "
           "group lives longer; each row's label shows the gap in years.")
    return fig, alt
