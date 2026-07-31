"""Festival timeline visualization (Req 9).

build_month_timeline returns (figure, alt_text): a 12-month bar strip showing how
many festivals fall in each month, with the selected month emphasized. Months are
always shown January-to-December in order (Req 9.1).
"""
from __future__ import annotations

import calendar

import plotly.graph_objects as go

from components import theme

MONTHS = [calendar.month_abbr[m] for m in range(1, 13)]


def build_month_timeline(counts_by_month: dict[int, int], selected: int) -> tuple[go.Figure, str]:
    counts = [counts_by_month.get(m, 0) for m in range(1, 13)]
    colors = [theme.PRIMARY if (m == selected) else "#D9C7A6" for m in range(1, 13)]

    fig = go.Figure(
        go.Bar(
            x=MONTHS, y=counts,
            marker=dict(color=colors),
            text=[str(c) if c else "" for c in counts],
            textposition="outside",
            hovertemplate="<b>%{x}</b>: %{y} festival(s)<extra></extra>",
        )
    )
    fig.update_layout(
        template=theme.plotly_template(),
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(title="Festivals", rangemode="tozero"),
        xaxis=dict(title="Month"),
        showlegend=False,
    )
    sel_name = calendar.month_name[selected]
    alt = (
        "A month-by-month timeline of food festivals from January to December; "
        f"{sel_name} is highlighted with {counts_by_month.get(selected, 0)} recorded festival(s)."
    )
    return fig, alt
