"""Travel Analytics visualizations (world tourism-economy time series, 1999-2020).

Each builder returns (figure, alt_text). Palette follows the spice-market design
system in components.theme; every chart has plain-language alt text (Req 18.2).
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from components import theme

_PRIMARY = theme.PRIMARY
_ACCENT = theme.ACCENT
_GOLD = theme.GOLD


def _fmt(n: float | None) -> str:
    if n is None or (isinstance(n, float) and n != n):
        return "—"
    n = float(n)
    if abs(n) >= 1e9:
        return f"{n / 1e9:.1f}B"
    if abs(n) >= 1e6:
        return f"{n / 1e6:.1f}M"
    if abs(n) >= 1e3:
        return f"{n / 1e3:.0f}K"
    return f"{n:,.0f}"


def build_global_trend(trend: pd.DataFrame, metric: str) -> tuple[go.Figure, str]:
    """Worldwide arrivals or receipts per year as a filled area — tells the COVID story."""
    col = "receipts" if metric == "receipts" else "arrivals"
    label = "International tourism receipts (US$)" if metric == "receipts" \
        else "International tourist arrivals"
    df = trend.dropna(subset=[col])
    fig = go.Figure(
        go.Scatter(
            x=df["year"], y=df[col], mode="lines+markers",
            line=dict(color=_PRIMARY, width=3, shape="spline"),
            fill="tozeroy", fillcolor="rgba(178,58,46,0.12)",
            marker=dict(size=6, color=_PRIMARY),
            hovertemplate="<b>%{x}</b><br>" + label + ": %{y:,.0f}<extra></extra>",
        )
    )
    # Annotate the pandemic collapse if the drop year is in range.
    if col == "arrivals" and {2019, 2020}.issubset(set(df["year"])):
        y2020 = float(df.loc[df["year"] == 2020, col].iloc[0])
        fig.add_annotation(
            x=2020, y=y2020, text="COVID-19", showarrow=True, arrowhead=2,
            arrowcolor=_PRIMARY, ax=-40, ay=-50,
            font=dict(color=_PRIMARY, size=12, family=theme.FONT_STACK_UI),
        )
    fig.update_layout(
        template=theme.plotly_template(), height=420,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title=label, xaxis_title=None,
        yaxis=dict(gridcolor="#EFE6D6"), xaxis=dict(dtick=2),
    )
    peak = df.loc[df[col].idxmax()]
    alt = (
        f"An area chart of worldwide {label.lower()} from {int(df['year'].min())} to "
        f"{int(df['year'].max())}, peaking around {int(peak['year'])}."
    )
    return fig, alt


def build_country_comparison(series: pd.DataFrame, metric: str) -> tuple[go.Figure, str]:
    """Multi-country line chart of arrivals or receipts over time."""
    col = "receipts" if metric == "receipts" else "arrivals"
    label = "Tourism receipts (US$)" if metric == "receipts" else "Tourist arrivals"
    df = series.dropna(subset=[col])
    fig = px.line(
        df, x="year", y=col, color="name", markers=True,
        labels={"year": "Year", col: label, "name": "Country"},
    )
    fig.update_traces(line=dict(width=2.5), marker=dict(size=5),
                      hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y:,.0f}<extra></extra>")
    fig.update_layout(
        template=theme.plotly_template(), height=440,
        margin=dict(l=10, r=10, t=20, b=10), legend_title_text="Country",
        yaxis_title=label, yaxis=dict(gridcolor="#EFE6D6"), xaxis=dict(dtick=2),
    )
    countries = ", ".join(sorted(df["name"].unique())[:6])
    alt = f"A line chart comparing {label.lower()} over time for {countries}."
    return fig, alt


# A warm spice-market gradient for the maps (cream -> saffron -> paprika -> plum).
_SCALE = [
    [0.0, "#FFF3D9"], [0.25, "#F6C453"], [0.5, "#E8892B"],
    [0.75, "#C0392B"], [1.0, "#7A1F3D"],
]

_GEO = dict(
    projection=dict(type="natural earth"),
    showocean=True, oceancolor="#EAF4F4",
    showland=True, landcolor="#F3ECDD",
    showcountries=True, countrycolor="#FFFFFF",
    showframe=False, coastlinecolor="#D8E6E6",
    bgcolor="rgba(0,0,0,0)",
)


def build_choropleth(points: pd.DataFrame, metric: str, year: int) -> tuple[go.Figure, str]:
    """World map shaded by arrivals or receipts for a chosen year (clickable)."""
    label = "Tourism receipts (US$)" if metric == "receipts" else "Tourist arrivals"
    df = points.copy()
    fig = go.Figure(
        go.Choropleth(
            locations=df["iso3"], z=df["value"], text=df["name"], locationmode="ISO-3",
            colorscale=_SCALE, colorbar=dict(title=None, thickness=12, len=0.7,
                                             outlinewidth=0, tickfont=dict(size=10)),
            marker=dict(line=dict(color="#FFFFFF", width=0.4)),
            hovertemplate="<b>%{text}</b><br>" + label + ": %{z:,.0f}"
                          "<br><i>click for facts</i><extra></extra>",
        )
    )
    fig.update_layout(
        template=theme.plotly_template(), height=470, margin=dict(l=0, r=0, t=0, b=0),
        geo=_GEO,
    )
    top = df.sort_values("value", ascending=False).head(3)
    top_desc = ", ".join(f"{r['name']} ({_fmt(r['value'])})" for _, r in top.iterrows())
    alt = (f"A world map shading countries by {label.lower()} in {year}; "
           f"the leaders are {top_desc}. Click any country for its story.")
    return fig, alt


def build_animated_choropleth(all_years: pd.DataFrame, metric: str) -> tuple[go.Figure, str]:
    """A play-button world map that sweeps year by year — watch travel rise and crash."""
    label = "Tourism receipts (US$)" if metric == "receipts" else "Tourist arrivals"
    df = all_years.sort_values("year").copy()
    zmax = df["value"].quantile(0.97) if not df.empty else None
    fig = px.choropleth(
        df, locations="iso3", color="value", locationmode="ISO-3",
        hover_name="name", animation_frame="year",
        color_continuous_scale=_SCALE, range_color=(0, zmax) if zmax else None,
        labels={"value": label},
    )
    fig.update_traces(marker=dict(line=dict(color="#FFFFFF", width=0.3)),
                      hovertemplate="<b>%{hovertext}</b><br>" + label + ": %{z:,.0f}<extra></extra>")
    fig.update_layout(
        template=theme.plotly_template(), height=480, margin=dict(l=0, r=0, t=0, b=0),
        geo=_GEO, coloraxis_colorbar=dict(title=None, thickness=12, len=0.7, outlinewidth=0),
    )
    # Snappier animation.
    if fig.layout.updatemenus:
        for btn in fig.layout.updatemenus[0].buttons:
            btn.args[1]["frame"]["duration"] = 500
            btn.args[1]["transition"]["duration"] = 300
    alt = (f"An animated world map sweeping through the years, shading each country by "
           f"{label.lower()}; press play to watch global travel grow and then collapse in 2020.")
    return fig, alt


def build_ranking_bar(df: pd.DataFrame, value_col: str, title: str,
                      value_label: str, is_currency: bool = False) -> tuple[go.Figure, str]:
    """Horizontal bar ranking colored by region."""
    d = df.copy().sort_values(value_col, ascending=True)
    colors = [theme.region_color(r) for r in d.get("region", [None] * len(d))]
    text = [("$" if is_currency else "") + _fmt(v) for v in d[value_col]]
    fig = go.Figure(
        go.Bar(
            x=d[value_col], y=d["name"], orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=text, textposition="auto",
            hovertemplate="<b>%{y}</b><br>" + value_label + ": %{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        template=theme.plotly_template(), height=max(320, 34 * len(d)),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=value_label, yaxis_title=None, xaxis=dict(gridcolor="#EFE6D6"),
    )
    lead = d.iloc[-1]
    alt = f"{title}: {lead['name']} leads with {('$' if is_currency else '')}{_fmt(lead[value_col])}."
    return fig, alt


def build_covid_bars(impact: dict) -> tuple[go.Figure, str]:
    """A lollipop before/after of global arrivals with the drop called out."""
    arr = impact.get("arrivals", {})
    peak, trough = impact.get("peak_year"), impact.get("trough_year")
    years = [str(peak), str(trough)]
    vals = [arr.get(peak), arr.get(trough)]
    colors = [_ACCENT, _PRIMARY]
    fig = go.Figure()
    # Stems + heads (lollipop) for a lighter, more modern look than solid bars.
    for x, v, c in zip(years, vals, colors):
        fig.add_trace(go.Scatter(
            x=[x, x], y=[0, v], mode="lines", line=dict(color=c, width=6),
            hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(
            x=[x], y=[v], mode="markers+text", marker=dict(size=26, color=c),
            text=[_fmt(v)], textposition="top center",
            textfont=dict(size=14, color=c, family=theme.FONT_STACK_UI),
            hovertemplate="<b>%{x}</b><br>Arrivals: %{y:,.0f}<extra></extra>",
            showlegend=False))
    crash = impact.get("crash_pct")
    if crash is not None:
        fig.add_annotation(
            x=0.5, xref="paper", y=max(v for v in vals if v) * 0.6,
            text=f"<b>{crash:.0f}%</b><br>in one year", showarrow=False,
            font=dict(size=22, color=_PRIMARY, family=theme.FONT_STACK_UI),
            align="center", bgcolor="rgba(255,255,255,0.7)", borderpad=6)
    fig.update_layout(
        template=theme.plotly_template(), height=340,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title="Global tourist arrivals", yaxis=dict(gridcolor="#EFE6D6"),
        xaxis=dict(showgrid=False), showlegend=False,
    )
    alt = (f"A before-and-after chart of global tourist arrivals in {peak} versus {trough}, "
           f"a fall of {abs(crash):.0f}%." if crash is not None else
           "A chart comparing global tourist arrivals before and during the pandemic.")
    return fig, alt
