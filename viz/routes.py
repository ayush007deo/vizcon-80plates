"""Dark 'explorer's journal' food-voyage map (Req 7, 8).

build_route_map returns (figure, alt_text). On a deep-navy world, a food icon glides
along glowing amber arcs; the travelled trail lights up behind it and origins pulse —
an animated voyage with a Play button. Country stops show their flag; (0,0) 'Global'
pseudo-stops are dropped by the caller.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from components import theme
from components.flags import flag
from pipeline.ingest import iso_reference

_GEO = dict(
    projection=dict(type="natural earth"),
    showland=True, landcolor=theme.NAVY_2,
    showocean=True, oceancolor=theme.NAVY,
    showcountries=True, countrycolor="rgba(255,248,231,0.32)",   # brighter borders
    showcoastlines=True, coastlinecolor="rgba(245,158,11,0.45)",
    showframe=False, bgcolor="rgba(0,0,0,0)", lakecolor=theme.NAVY,
)


def _stop_iso3(name: str) -> str | None:
    """Resolve a stop's country iso3, trying the parenthetical then the base name.

    Handles 'Andes (Peru)' -> Peru, 'Yunnan (China)' -> China, 'China (Sichuan)' -> China.
    """
    n2i = iso_reference.name_to_iso3()
    raw = str(name)
    candidates = []
    m = re.search(r"\(([^)]+)\)", raw)      # inside parentheses
    if m:
        candidates.append(m.group(1))
    candidates.append(re.sub(r"\(.*?\)", "", raw))  # outside parentheses
    candidates.append(raw)
    for c in candidates:
        iso = n2i.get(re.sub(r"[^a-z]", "", c.lower()))
        if iso:
            return iso
    return None


def _label(name: str) -> str:
    iso = _stop_iso3(name)
    return (flag(iso) + " " if iso else "") + str(name)


def _arc_points(lons, lats, per_leg=20, bulge=0.22):
    pts = []
    for i in range(len(lons) - 1):
        lon0, lat0, lon1, lat1 = lons[i], lats[i], lons[i + 1], lats[i + 1]
        mlon, mlat = (lon0 + lon1) / 2, (lat0 + lat1) / 2
        dlon, dlat = lon1 - lon0, lat1 - lat0
        clon, clat = mlon - dlat * bulge, mlat + dlon * bulge
        for t in np.linspace(0, 1, per_leg):
            lon = (1 - t) ** 2 * lon0 + 2 * (1 - t) * t * clon + t ** 2 * lon1
            lat = (1 - t) ** 2 * lat0 + 2 * (1 - t) * t * clat + t ** 2 * lat1
            pts.append((lon, lat))
    return pts


_PER_LEG = 18


def route_length(steps: pd.DataFrame) -> int:
    """Number of animation steps for a route (used by the auto-play loop)."""
    df = steps.sort_values("seq")
    return max(1, (len(df) - 1) * _PER_LEG)


def build_route_frame(steps: pd.DataFrame, subject: str, k: int,
                      icon: str = "🚢") -> tuple[go.Figure, int]:
    """A single static frame of the voyage with the ship at progress `k`.

    Used by the auto-animating fragment: each tick advances k and redraws, so the
    ship sails on its own without the user pressing play. Returns (figure, total_steps).
    """
    df = steps.sort_values("seq").reset_index(drop=True)
    lons, lats = df["lon"].tolist(), df["lat"].tolist()
    names = df["location_name"].tolist()
    arc = _arc_points(lons, lats, per_leg=_PER_LEG)
    total = max(1, len(arc))
    k = max(0, min(k, total - 1))
    alons = [p[0] for p in arc]
    alats = [p[1] for p in arc]
    cx, cy = alons[k], alats[k]
    reached = min(k // _PER_LEG, len(df) - 1)  # last stop the ship has reached

    route_iso = [i for i in (_stop_iso3(n) for n in names) if i]
    highlight = go.Choropleth(
        locations=route_iso, z=[1] * len(route_iso), locationmode="ISO-3",
        colorscale=[[0, "rgba(245,158,11,0.18)"], [1, "rgba(245,158,11,0.18)"]],
        showscale=False, marker=dict(line=dict(color=theme.AMBER_HI, width=1.6)),
        hoverinfo="skip",
    )
    faint = go.Scattergeo(lon=alons, lat=alats, mode="lines",
                          line=dict(width=2, color="rgba(245,158,11,0.18)"), hoverinfo="skip")
    tglow = go.Scattergeo(lon=alons[:k + 1], lat=alats[:k + 1], mode="lines",
                          line=dict(width=11, color="rgba(245,158,11,0.22)"), hoverinfo="skip")
    tmid = go.Scattergeo(lon=alons[:k + 1], lat=alats[:k + 1], mode="lines",
                         line=dict(width=5, color="rgba(245,158,11,0.55)"), hoverinfo="skip")
    tcore = go.Scattergeo(lon=alons[:k + 1], lat=alats[:k + 1], mode="lines",
                          line=dict(width=2.2, color=theme.AMBER_HI), hoverinfo="skip")
    # Stops: the reached one pulses larger.
    sizes = [22 if i == reached else 11 for i in range(len(df))]
    stops = go.Scattergeo(
        lon=lons, lat=lats, mode="markers+text",
        text=[_label(n) for n in names], textposition="top center",
        textfont=dict(size=12, color=theme.CREAM, family=theme.FONT_STACK_UI),
        marker=dict(size=sizes, color=theme.AMBER, line=dict(width=2, color=theme.CREAM)),
        hoverinfo="skip",
    )
    glow = go.Scattergeo(lon=[cx], lat=[cy], mode="markers",
                         marker=dict(size=38, color="rgba(253,186,59,0.32)"), hoverinfo="skip")
    ship = go.Scattergeo(lon=[cx], lat=[cy], mode="text",
                         text=[icon], textfont=dict(size=28), hoverinfo="skip")

    fig = go.Figure(data=[highlight, faint, tglow, tmid, tcore, stops, glow, ship])
    fig.update_layout(
        template=theme.plotly_template(), showlegend=False, paper_bgcolor=theme.NAVY,
        margin=dict(l=0, r=0, t=0, b=0), height=540, geo=_GEO, transition=dict(duration=0),
        dragmode=False,
    )
    return fig, total


def build_route_map(steps: pd.DataFrame, subject: str = "",
                    icon: str = "🍽️") -> tuple[go.Figure, str]:
    """steps: ordered DataFrame with seq, location_name, lat, lon, time_period."""
    df = steps.sort_values("seq").reset_index(drop=True)
    lons, lats = df["lon"].tolist(), df["lat"].tolist()
    names = df["location_name"].tolist()
    periods = [p if isinstance(p, str) else "" for p in df["time_period"].tolist()]
    stop_text = [f"{_label(n)}" for n in names]

    arc = _arc_points(lons, lats)
    alons = [p[0] for p in arc]
    alats = [p[1] for p in arc]

    def _glow_line(lo, la, width, color):
        return go.Scattergeo(lon=lo, lat=la, mode="lines",
                             line=dict(width=width, color=color), hoverinfo="skip")

    # Highlight the fill + borders of the countries the food passes through.
    # Always present (empty when no stop resolves to a country) so trace indices are stable.
    route_iso = [i for i in (_stop_iso3(n) for n in names) if i]
    highlight = go.Choropleth(
        locations=route_iso, z=[1] * len(route_iso), locationmode="ISO-3",
        colorscale=[[0, "rgba(245,158,11,0.18)"], [1, "rgba(245,158,11,0.18)"]],
        showscale=False, marker=dict(line=dict(color=theme.AMBER_HI, width=1.6)),
        hoverinfo="skip",
    )

    # Faint full path (so the whole voyage is hinted) + three-layer glowing trail.
    faint = _glow_line(alons, alats, 2, "rgba(245,158,11,0.18)")
    trail_glow = _glow_line([lons[0]], [lats[0]], 11, "rgba(245,158,11,0.22)")
    trail_mid = _glow_line([lons[0]], [lats[0]], 5, "rgba(245,158,11,0.55)")
    trail_core = _glow_line([lons[0]], [lats[0]], 2.2, theme.AMBER_HI)

    stops = go.Scattergeo(
        lon=lons, lat=lats, mode="markers+text",
        text=stop_text, textposition="top center",
        textfont=dict(size=12, color=theme.CREAM, family=theme.FONT_STACK_UI),
        marker=dict(size=11, color=theme.AMBER, line=dict(width=2, color=theme.CREAM),
                    symbol="circle"),
        customdata=periods,
        hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>",
    )
    glow = go.Scattergeo(lon=[lons[0]], lat=[lats[0]], mode="markers",
                         marker=dict(size=36, color="rgba(253,186,59,0.30)"), hoverinfo="skip")
    traveler = go.Scattergeo(lon=[lons[0]], lat=[lats[0]], mode="text",
                             text=[icon], textfont=dict(size=28), hoverinfo="skip")

    # trace order: 0 highlight, 1 faint, 2 trail_glow, 3 trail_mid, 4 trail_core,
    #              5 stops, 6 glow, 7 traveler
    fig = go.Figure(data=[highlight, faint, trail_glow, trail_mid, trail_core,
                          stops, glow, traveler])

    frames = []
    for k in range(len(arc)):
        lo = alons[:k + 1]
        la = alats[:k + 1]
        cx, cy = alons[k], alats[k]
        frames.append(go.Frame(
            name=str(k),
            data=[
                go.Scattergeo(lon=lo, lat=la, mode="lines",
                              line=dict(width=11, color="rgba(245,158,11,0.22)")),
                go.Scattergeo(lon=lo, lat=la, mode="lines",
                              line=dict(width=5, color="rgba(245,158,11,0.55)")),
                go.Scattergeo(lon=lo, lat=la, mode="lines",
                              line=dict(width=2.2, color=theme.AMBER_HI)),
                go.Scattergeo(lon=[cx], lat=[cy], mode="markers",
                              marker=dict(size=36, color="rgba(253,186,59,0.30)")),
                go.Scattergeo(lon=[cx], lat=[cy], mode="text",
                              text=[icon], textfont=dict(size=28)),
            ],
            traces=[2, 3, 4, 6, 7],
        ))
    fig.frames = frames

    def _play(label, dur):
        return dict(label=label, method="animate",
                    args=[None, dict(frame=dict(duration=dur, redraw=True),
                                     transition=dict(duration=0),
                                     fromcurrent=True, mode="immediate")])

    fig.update_layout(
        template=theme.plotly_template(), showlegend=False,
        paper_bgcolor=theme.NAVY, margin=dict(l=0, r=0, t=0, b=0), height=540, geo=_GEO,
        updatemenus=[dict(
            type="buttons", direction="right", showactive=False,
            x=0.5, y=0.02, xanchor="center", yanchor="bottom",
            bgcolor=theme.AMBER, bordercolor=theme.AMBER,
            font=dict(color=theme.NAVY, size=13, family=theme.FONT_STACK_UI),
            pad=dict(l=4, r=4, t=4, b=4),
            buttons=[
                _play(f"▶  Follow the {subject}".strip(), 55),
                _play("⏩  Fast", 20),
            ],
        )],
        dragmode=False,
    )

    route_desc = " → ".join(names)
    alt = (f"A dark world map: a {icon} icon sails glowing amber routes tracing "
           f"{subject or 'the journey'} across {len(df)} stops — {route_desc}.")
    return fig, alt
