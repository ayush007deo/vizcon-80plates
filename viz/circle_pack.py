"""Flavor-wheel circle-packing of cuisine clusters (Req 11).

build_flavor_wheel returns (figure, alt_text). Implemented as a Plotly icicle-style
packing is avoided in favor of a true nested-circle look: each cluster is a container
circle enclosing one leaf circle per member country. Hover/select shows the country
and its cluster (Req 11.5). Cluster names are shown as text (non-color channel).
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from components import theme

_PALETTE = list(theme.REGION_COLORS.values()) + ["#7A9E7E", "#C58B5B", "#6C8EBF"]


def build_flavor_wheel(clusters: pd.DataFrame) -> tuple[go.Figure, str]:
    """clusters: DataFrame with iso3, country, cluster_name.

    Lays out cluster container circles around a ring; inside each, member-country leaf
    circles are placed on an inner ring — a circle-packing arrangement.
    """
    names = sorted(clusters["cluster_name"].unique())
    n_clusters = max(1, len(names))
    fig = go.Figure()

    shapes = []
    ann = []
    R = 10  # radius of the ring on which clusters sit

    CAP = 14  # max leaf circles drawn per cluster to keep the wheel readable
    for ci, cname in enumerate(names):
        full = clusters[clusters["cluster_name"] == cname].reset_index(drop=True)
        total = len(full)
        members = full.head(CAP).reset_index(drop=True)
        m = len(members)
        extra = total - m
        # Container circle center.
        angle = 2 * math.pi * ci / n_clusters
        cx, cy = R * math.cos(angle), R * math.sin(angle)
        container_r = 1.6 + 0.5 * math.sqrt(max(1, m))
        color = _PALETTE[ci % len(_PALETTE)]

        shapes.append(dict(
            type="circle", xref="x", yref="y",
            x0=cx - container_r, y0=cy - container_r,
            x1=cx + container_r, y1=cy + container_r,
            line=dict(color=color, width=2), fillcolor=color, opacity=0.15,
        ))
        label = f"<b>{cname}</b>" + (f" (+{extra} more)" if extra > 0 else "")
        ann.append(dict(x=cx, y=cy + container_r + 0.4, text=label,
                        showarrow=False, font=dict(size=12, color=theme.TEXT_PRIMARY)))

        # Leaf circles for member countries, placed on an inner ring (or center).
        leaf_x, leaf_y, leaf_text = [], [], []
        for k in range(m):
            if m == 1:
                lx, ly = cx, cy
            else:
                a = 2 * math.pi * k / m
                rr = container_r * 0.5
                lx, ly = cx + rr * math.cos(a), cy + rr * math.sin(a)
            leaf_x.append(lx)
            leaf_y.append(ly)
            leaf_text.append(members.loc[k, "country"])

        fig.add_trace(go.Scatter(
            x=leaf_x, y=leaf_y, mode="markers+text",
            marker=dict(size=22, color=color, line=dict(color="#FFFFFF", width=1.5)),
            text=leaf_text, textposition="middle center",
            textfont=dict(size=9, color="#FFFFFF"),
            customdata=[cname] * m,
            hovertemplate="<b>%{text}</b><br>Cluster: %{customdata}<extra></extra>",
            name=cname,
        ))

    fig.update_layout(
        template=theme.plotly_template(),
        shapes=shapes, annotations=ann,
        height=620, showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(visible=False, range=[-R - 4, R + 4], scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False, range=[-R - 4, R + 4]),
    )

    alt = (
        f"A circle-packing flavor wheel grouping {len(clusters)} countries into "
        f"{n_clusters} cuisine clusters ({', '.join(names)}); each cluster circle "
        "encloses one labeled circle per member country."
    )
    return fig, alt
