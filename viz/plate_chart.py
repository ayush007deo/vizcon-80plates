"""'What's on the Plate?' proportional visualization (Req 5).

build_plate returns (figure, alt_text). A donut pie reads like a plate: each food
group's arc is proportional to its percentage and labeled with that whole-percent
value (Req 5.1, 5.2). The pipeline guarantees the percentages sum to ~100 (Req 5.3).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from components import theme

# A warm, food-evocative palette keyed by common food groups (non-color labels also shown).
FOOD_COLORS = {
    "Cereals": "#E3B23C",
    "Vegetables": "#6FA85B",
    "Fruits": "#E8743B",
    "Meat": "#B5533C",
    "Seafood": "#4C86A8",
    "Dairy": "#EDE6D6",
    "Pulses": "#8A6D3B",
    "Sugar": "#D9A7C7",
    "Oils": "#C9B037",
}


def build_plate(food_groups: pd.DataFrame, country_name: str = "") -> tuple[go.Figure, str]:
    """food_groups: DataFrame with food_group, pct (ordered largest first)."""
    df = food_groups.copy()
    colors = [FOOD_COLORS.get(g, theme.REGION_FALLBACK) for g in df["food_group"]]

    fig = go.Figure(
        go.Pie(
            labels=df["food_group"],
            values=df["pct"],
            hole=0.42,
            sort=False,
            direction="clockwise",
            marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
            texttemplate="%{label}<br>%{value:.0f}%",
            hovertemplate="<b>%{label}</b>: %{value:.0f}% of food supply<extra></extra>",
        )
    )
    fig.update_layout(
        template=theme.plotly_template(),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
        margin=dict(l=10, r=10, t=10, b=10),
        height=480,
        annotations=[dict(text="🍽️", x=0.5, y=0.5, font=dict(size=40), showarrow=False)],
    )

    top = df.sort_values("pct", ascending=False).head(3)
    top_desc = ", ".join(f"{r['food_group']} {r['pct']:.0f}%" for _, r in top.iterrows())
    alt = (
        f"A plate breakdown for {country_name or 'the selected country'} where "
        f"the largest food groups are {top_desc}."
    )
    return fig, alt
