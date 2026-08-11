"""Card renderers, the unavailable placeholder, and the discovery-insight callout.

Used across sections (Req 4.1 cards not tables, 4.3 placeholders, 17.4 insight styling).
"""
from __future__ import annotations

import html
from typing import Iterable

UNAVAILABLE_TEXT = "Not available"


def _esc(value) -> str:
    return html.escape(str(value))


def unavailable_html() -> str:
    return f'<span class="atw-unavailable">{UNAVAILABLE_TEXT}</span>'


def render_narrative(section_key: str) -> None:
    """Render a section's opening narrative sentence (Req 1.4)."""
    import streamlit as st

    from components.narrative import narrative

    st.markdown(f'<p class="atw-narrative">{_esc(narrative(section_key))}</p>',
                unsafe_allow_html=True)


def card(title: str, body_html: str, icon: str = "") -> None:
    """Render one content card."""
    import streamlit as st

    heading = f"{icon} {_esc(title)}".strip()
    st.markdown(
        f'<div class="atw-card"><h4>{heading}</h4><div>{body_html}</div></div>',
        unsafe_allow_html=True,
    )


def value_card(title: str, value, icon: str = "", ai_derived: bool = False) -> None:
    """Card for a single scalar value; shows a placeholder when value is missing."""
    if value is None or (isinstance(value, float) and value != value):  # NaN check
        body = unavailable_html()
    else:
        body = f'<span style="font-size:1.6rem;font-weight:700">{_esc(value)}</span>'
    if ai_derived:
        body += '<span class="atw-badge">AI-assisted</span>'
    card(title, body, icon)


def list_card(title: str, items: Iterable[str] | None, icon: str = "") -> None:
    """Card for a list of items (e.g., dishes, festivals); placeholder if empty."""
    items = [i for i in (items or []) if i]
    if not items:
        body = unavailable_html()
    else:
        body = " ".join(f'<span class="atw-pill">{_esc(i)}</span>' for i in items)
    card(title, body, icon)


SECTION_EMOJI = {
    "explore_map": "🗺️", "plate": "🍽️", "similarity": "🤝", "migration": "🌍",
    "spice_journey": "🌶️", "festivals": "🎉", "heritage": "🏛", "health": "❤️",
    "flavor_wheel": "🎡", "taste_passport": "🛂", "dish_search": "🔎", "insights": "📊",
    "dinner_party": "🍽️", "sources": "📚", "country_story": "📖",
    "journeys": "🧭", "traditions": "🎎", "bigpicture": "📊", "travel": "✈️",
}


def page_header(section_key: str) -> None:
    """Render a section's dark band header with its narrative subtitle."""
    from components.navigation import label_for
    from components.narrative import narrative

    section_band(label_for(section_key), narrative(section_key),
                 emoji=SECTION_EMOJI.get(section_key, ""))


def section_band(title: str, subtitle: str = "", emoji: str = "") -> None:
    """A dark section-header band with an italic narrative subtitle."""
    import streamlit as st

    head = f"{emoji} {_esc(title)}".strip()
    sub = f'<div class="band-sub">{_esc(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div class="atw-band"><h2>{head}</h2>{sub}</div>',
        unsafe_allow_html=True,
    )


def big_stat(label: str, value, icon: str = "", ai_derived: bool = False) -> None:
    """A bold hero-style metric card; placeholder when the value is missing."""
    import streamlit as st

    if value is None or (isinstance(value, float) and value != value):
        val_html = unavailable_html()
    else:
        val_html = f'<span class="bs-value">{_esc(value)}</span>'
    badge = '<span class="atw-badge">AI-assisted</span>' if ai_derived else ""
    st.markdown(
        f'<div class="atw-card atw-bigstat"><div class="bs-icon">{icon}</div>'
        f'<div class="bs-label">{_esc(label)}{badge}</div>{val_html}</div>',
        unsafe_allow_html=True,
    )


def video_hero(video_data_uri: str, title: str, subtitle: str,
               mime: str = "video/mp4", height: int = 300) -> None:
    """A cinematic full-bleed video hero (muted autoplay loop) with the title overlaid.

    Rendered via components.html (an iframe) so browser autoplay is reliable and the
    HTML isn't sanitized. `video_data_uri` is a data: URI or a public URL.
    """
    import streamlit as st

    t, s = _esc(title), _esc(subtitle)
    st.html(
        f"""
        <!doctype html><html><head><meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@600;700&display=swap" rel="stylesheet">
        <style>
          html,body{{margin:0;padding:0;background:transparent;overflow:hidden;}}
          .hero{{position:relative;height:{height}px;border-radius:18px;overflow:hidden;
            width:calc(100% + 48px);margin-left:-24px;margin-right:-24px;
            box-shadow:0 26px 60px rgba(43,33,24,0.30);}}
          .hero video{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;}}
          .tint{{position:absolute;inset:0;z-index:1;
            background:linear-gradient(105deg,rgba(20,12,8,.82)0%,rgba(20,12,8,.42)46%,rgba(20,12,8,.12)100%),
                       linear-gradient(0deg,rgba(20,12,8,.6)0%,rgba(20,12,8,0)55%);}}
          .glow{{position:absolute;z-index:1;width:520px;height:520px;right:-120px;top:-160px;border-radius:50%;
            background:radial-gradient(closest-side,rgba(242,169,59,.5),rgba(242,169,59,0)70%);
            filter:blur(10px);animation:glow 9s ease-in-out infinite alternate;}}
          @keyframes glow{{from{{transform:translate(0,0);opacity:.7;}}to{{transform:translate(-30px,26px);opacity:1;}}}}
          .inner{{position:relative;z-index:2;height:100%;display:flex;flex-direction:column;
            justify-content:flex-end;padding:28px 36px;box-sizing:border-box;
            font-family:'Inter',system-ui,sans-serif;color:#fff;max-width:860px;}}
          .eyebrow{{font-weight:700;text-transform:uppercase;letter-spacing:.24em;font-size:.72rem;
            color:#E8A317;margin-bottom:8px;}}
          h1{{font-family:'Playfair Display',Georgia,serif;font-weight:900;font-size:2.8rem;line-height:1.05;
            margin:0;letter-spacing:-1px;background:linear-gradient(92deg,#FFF 0%,#FFE7C4 40%,#E8A317 62%,#FFF 100%);background-size:220% auto;-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;animation:shine 7s linear infinite;
            /* color set by gradient */
            
            
            }}
          @keyframes shine{{to{{background-position:220% center;}}}}
          p{{font-family:'Playfair Display',Georgia,serif;font-style:italic;font-size:1.1rem;
            margin:8px 0 0 0;max-width:660px;color:#E8A317;text-shadow:0 2px 14px rgba(0,0,0,.6);}}
          .scroll{{display:flex;align-items:center;gap:10px;margin-top:16px;font-size:.72rem;
            letter-spacing:.14em;text-transform:uppercase;color:rgba(255,255,255,.85);}}
          .scroll .m{{width:18px;height:28px;border:2px solid rgba(255,255,255,.7);border-radius:10px;position:relative;}}
          .scroll .m::after{{content:"";position:absolute;left:50%;top:5px;width:3px;height:6px;background:#fff;
            border-radius:2px;transform:translateX(-50%);animation:sc 1.6s ease-in-out infinite;}}
          @keyframes sc{{0%{{opacity:0;top:5px;}}40%{{opacity:1;}}80%{{opacity:0;top:14px;}}100%{{opacity:0;}}}}
        </style></head>
        <body><div class="hero">
          <video autoplay muted loop playsinline preload="auto">
            <source src="{video_data_uri}" type="{mime}">
          </video>
          <div class="tint"></div><div class="glow"></div>
          <div class="inner">
            <div class="eyebrow" style="color:#E8A317 !important">✦ A Data Journey · Culture Through Food</div>
            <h1>{t}</h1><p>{s}</p>
            <div class="scroll"><span class="m"></span>Scroll to begin</div>
          </div>
        </div></body></html>
        """
    )


def hero_banner(image_url: str | None, title: str, subtitle: str) -> None:
    """Full-bleed hero with the title overlaid on a photo (falls back to gradient)."""
    import streamlit as st

    t, s = _esc(title), _esc(subtitle)
    bg = f"background-image:url('{image_url}');" if image_url else ""
    st.html(
        f"""
        <div style="position:relative;border-radius:20px;overflow:hidden;min-height:280px;
            display:flex;align-items:flex-end;box-shadow:0 16px 40px rgba(43,33,24,0.25);">
            <div style="position:absolute;inset:0;{bg}background-size:cover;
                background-position:center;background-color:#2E1C15;"></div>
            <div style="position:absolute;inset:0;background:linear-gradient(105deg,
                rgba(20,12,8,0.85) 0%,rgba(20,12,8,0.4) 50%,rgba(20,12,8,0.15) 100%),
                linear-gradient(0deg,rgba(20,12,8,0.6) 0%,rgba(20,12,8,0) 55%);"></div>
            <div style="position:relative;padding:28px 32px;max-width:800px;
                font-family:Inter,system-ui,sans-serif;color:#FFFFFF;">
                <div style="font-weight:700;text-transform:uppercase;letter-spacing:0.2em;
                    font-size:0.72rem;color:#E8A317;margin-bottom:8px;">
                    ✦ A Data Journey · Culture Through Food</div>
                <h1 style="font-family:Playfair Display,Georgia,serif;font-weight:900;
                    font-size:2.8rem;line-height:1.05;margin:0;color:#FFFFFF;
                    letter-spacing:-1px;">{t}</h1>
                <div style="font-family:Playfair Display,Georgia,serif;font-style:italic;
                    font-size:1.1rem;margin:10px 0 0 0;color:#E8A317;">{s}</div>
            </div>
        </div>
        """
    )


def floaties(emojis: list[str]) -> None:
    """A row of gently floating emojis — a license-free animated accent."""
    import streamlit as st

    spans = "".join(f"<span>{e}</span>" for e in emojis[:6])
    st.markdown(f'<div class="atw-floaties" style="height:34px">{spans}</div>',
                unsafe_allow_html=True)


def fact_strip(facts: list[tuple[str, str, str]]) -> None:
    """A row of bold, surprising 'did you know' fact cards (emoji, big, small)."""
    import streamlit as st

    cols = st.columns(len(facts))
    for col, (emoji, big, small) in zip(cols, facts):
        with col:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#FFFFFF,#FFF6E9);'
                f'border:1.5px solid #EFE0C8;border-radius:20px;padding:20px 22px;'
                f'text-align:center;box-shadow:0 4px 16px rgba(43,33,24,0.08);height:100%;">'
                f'<div style="font-size:2.2rem;">{emoji}</div>'
                f'<div style="font-weight:800;font-size:1.1rem;color:#C0392B;'
                f'margin:6px 0 4px 0;line-height:1.25;">{_esc(big)}</div>'
                f'<div style="color:#574B42;font-size:0.9rem;">{_esc(small)}</div></div>',
                unsafe_allow_html=True,
            )


def kpi_counters(items: list[dict]) -> None:
    """A row of KPI cards whose numbers animate (count up) on load.

    Each item: {emoji, value:int, label, prefix?, suffix?}. The count-up uses a pure
    CSS @property/counter animation — no JavaScript — so it works inside Streamlit's
    sanitized markdown and degrades to the final value on older browsers.
    """
    import streamlit as st

    props, keyframes, cells = [], [], []
    for i, it in enumerate(items):
        target = int(it["value"])
        dur = 1.6 + 0.25 * i  # slight stagger so they don't all finish together
        props.append(
            f"@property --kpi{i}{{syntax:'<integer>';initial-value:0;inherits:false;}}"
        )
        keyframes.append(
            f"@keyframes kc{i}{{from{{--kpi{i}:0;}}to{{--kpi{i}:{target};}}}}"
            f".kn{i}{{animation:kc{i} {dur:.2f}s cubic-bezier(.2,.7,.2,1) forwards;"
            f"counter-reset:k var(--kpi{i});}}"
            f".kn{i}::after{{content:counter(k);}}"
        )
        pfx, sfx = it.get("prefix", ""), it.get("suffix", "")
        prefix = f'<span class="k-prefix">{_esc(pfx)}</span>' if pfx else ""
        suffix = f'<span class="k-suffix">{_esc(sfx)}</span>' if sfx else ""
        # Accessible value: screen readers get the real number+label (the animated
        # CSS counter is decorative and aria-hidden). Also a graceful fallback.
        aria = f'{pfx}{target:,}{sfx} {it["label"]}'
        cells.append(
            f'<div class="atw-kpi" role="group" aria-label="{_esc(aria)}">'
            f'<div class="k-emoji" aria-hidden="true">{it.get("emoji","")}</div>'
            f'<div class="k-value" aria-hidden="true">{prefix}<span class="kn{i}"></span>{suffix}</div>'
            f'<div class="k-label">{_esc(it["label"])}</div></div>'
        )
    style = "<style>" + "".join(props) + "".join(keyframes) + "</style>"
    st.markdown(style + f'<div class="atw-kpis">{"".join(cells)}</div>',
                unsafe_allow_html=True)


def teaser(emoji: str, title: str, subtitle: str) -> None:
    """A curiosity-hook card used on the landing page."""
    import streamlit as st

    st.markdown(
        f'<div class="atw-teaser"><div class="emoji">{emoji}</div>'
        f'<div class="t-title">{_esc(title)}</div>'
        f'<div class="t-sub">{_esc(subtitle)}</div></div>',
        unsafe_allow_html=True,
    )


def insight_callout(text: str | None) -> None:
    """Render a 'Did you know?' discovery insight, visually distinct (Req 17.4)."""
    if not text:
        return
    import streamlit as st

    st.markdown(
        f'<div class="atw-insight"><span class="atw-insight-label">Did you know?</span>'
        f'<div>{_esc(text)}</div></div>',
        unsafe_allow_html=True,
    )
