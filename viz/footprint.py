"""Sustainability visuals: the healthy-and-sustainable quadrant and plate breakdown.

build_footprint_quadrant(df) plots each country's diet carbon intensity (x) against
life expectancy (y), split into four quadrants by the medians so the "eat well without
eating heavy" story is visible at a glance. build_plate_footprint(breakdown, name)
shows which food groups drive one country's plate footprint.

Both return (figure, alt_text) so callers can render an accessible description.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from components import theme


def build_footprint_quadrant(df: pd.DataFrame) -> tuple["object", str]:
    """Scatter of diet carbon footprint vs life expectancy, divided into quadrants."""
    d = df.dropna(subset=["co2", "life_expectancy", "population", "region"]).copy()

    med_co2 = float(d["co2"].median())
    med_life = float(d["life_expectancy"].median())

    fig = px.scatter(
        d, x="co2", y="life_expectancy", size="population", color="region",
        color_discrete_map=theme.REGION_COLORS, hover_name="name", size_max=54,
        labels={"co2": "Diet carbon intensity (kg CO₂e per kg of food)",
                "life_expectancy": "Life expectancy (years)", "region": "Region",
                "population": "Population"},
        custom_data=["region", "co2", "life_expectancy", "animal_share"],
    )
    fig.update_traces(
        marker=dict(opacity=0.82, line=dict(width=0.5, color="rgba(255,255,255,0.6)")),
        hovertemplate=(
            "<b>%{hovertext}</b><br>Region: %{customdata[0]}<br>"
            "Diet footprint: %{customdata[1]:.1f} kg CO₂e/kg<br>"
            "Life expectancy: %{customdata[2]:.0f} yrs<br>"
            "Animal foods on the plate: %{customdata[3]:.0f}%<extra></extra>"
        ),
    )

    # Median crosshairs split the field into four quadrants.
    fig.add_vline(x=med_co2, line=dict(color=theme.TEXT_SECONDARY, width=1, dash="dash"))
    fig.add_hline(y=med_life, line=dict(color=theme.TEXT_SECONDARY, width=1, dash="dash"))

    x_max = float(d["co2"].max())
    y_max = float(d["life_expectancy"].max())

    # Highlight the "healthy AND sustainable" quadrant (low footprint, long life).
    fig.add_shape(
        type="rect", x0=float(d["co2"].min()), x1=med_co2, y0=med_life, y1=y_max,
        fillcolor=theme.ACCENT, opacity=0.07, line_width=0, layer="below",
    )

    def _label(x, y, text, color):
        fig.add_annotation(x=x, y=y, text=text, showarrow=False,
                           font=dict(size=11, color=color, family=theme.FONT_STACK_UI),
                           opacity=0.9)

    _label((d["co2"].min() + med_co2) / 2, y_max,
           "🌱 Light & long-lived", theme.ACCENT)
    _label((med_co2 + x_max) / 2, y_max, "Heavy & long-lived", theme.TEXT_SECONDARY)

    fig.update_layout(
        template=theme.plotly_template(), height=560, legend_title_text="Region",
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(gridcolor="#EFE6D6"), xaxis=dict(gridcolor="#EFE6D6"),
    )

    alt = (
        f"A scatter plot of {len(d)} countries comparing the carbon intensity of the "
        "average national plate (horizontal axis, kilograms of CO₂-equivalent per kilogram "
        "of food) with life expectancy (vertical axis). Bubble size shows population and "
        "colour shows region. Dashed lines mark the medians; the shaded top-left quadrant "
        "holds countries that combine a low-carbon diet with long lives."
    )
    return fig, alt


def build_plate_footprint(breakdown: pd.DataFrame, country_name: str) -> tuple["object", str]:
    """Horizontal bar of each food group's contribution to a country's plate footprint."""
    d = breakdown.copy()
    d = d[d["co2_contribution"] > 0].sort_values("co2_contribution")

    fig = go.Figure(
        go.Bar(
            x=d["co2_contribution"], y=d["food_group"], orientation="h",
            marker=dict(color=d["co2_contribution"], colorscale="OrRd",
                        line=dict(width=0.5, color="rgba(255,255,255,0.6)")),
            customdata=d[["pct", "co2_per_kg"]].values,
            hovertemplate=("<b>%{y}</b><br>%{customdata[0]:.0f}% of the plate<br>"
                           "%{customdata[1]:.1f} kg CO₂e per kg<br>"
                           "Contributes %{x:.2f} kg CO₂e/kg<extra></extra>"),
        )
    )
    fig.update_layout(
        template=theme.plotly_template(), height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Contribution to plate footprint (kg CO₂e per kg)",
                   gridcolor="#EFE6D6"),
        yaxis=dict(title=""),
    )
    top = d.iloc[-1]["food_group"] if not d.empty else "food"
    alt = (
        f"A horizontal bar chart showing which food groups drive {country_name}'s plate "
        f"carbon footprint. {top} contributes the most. Each bar is the group's share of "
        "the plate multiplied by its carbon intensity."
    )
    return fig, alt
