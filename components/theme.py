"""Design system: palette, typography, spacing, region colors (Req 20, 18.1).

The palette is chosen so body/label text meets a >= 4.5:1 contrast ratio against its
background (verified by tests via contrast_ratio). inject_theme() applies global CSS
and a shared Plotly template so every section looks consistent.
"""
from __future__ import annotations

# --- Palette tokens --------------------------------------------------------
BACKGROUND = "#FFF8F1"     # clean soft warm-white page background
SURFACE = "#FFFFFF"        # cards
TEXT_PRIMARY = "#2A2320"   # near-black (body)
TEXT_SECONDARY = "#574B42" # warm grey-brown (labels/captions)
PRIMARY = "#C0392B"        # warm paprika red (emphasis, buttons)
TEXT_ON_PRIMARY = "#FFFFFF"
ACCENT = "#1F6F5C"         # deep teal (secondary accent)
GOLD = "#E8A317"           # saffron/amber highlight
BAND_FROM = "#2E1C15"      # dark espresso (section band gradient start)
BAND_TO = "#8A3324"        # deep paprika (section band gradient end)

# Text/background pairs that MUST meet WCAG AA (4.5:1). Verified in tests.
CONTRAST_PAIRS = [
    (TEXT_PRIMARY, BACKGROUND),
    (TEXT_SECONDARY, BACKGROUND),
    (TEXT_PRIMARY, SURFACE),
    (TEXT_SECONDARY, SURFACE),
    (TEXT_ON_PRIMARY, PRIMARY),
    (TEXT_ON_PRIMARY, ACCENT),
]

# --- Region color mapping (Req 20.3) — consistent across all sections ------
REGION_COLORS = {
    "Africa": "#E9A03B",
    "Americas": "#2A9D8F",
    "Asia": "#E15C4A",
    "Europe": "#4A72B0",
    "Oceania": "#8E6BB0",
}
REGION_FALLBACK = "#9A8C7A"

# --- Typography / spacing --------------------------------------------------
# Modern editorial pairing (fonts are imported in inject_theme): an elegant display
# serif for headings, a clean geometric sans for UI/body.
FONT_STACK = "'Playfair Display', 'Georgia', serif"
FONT_STACK_UI = "'Inter', 'Helvetica Neue', 'Segoe UI', system-ui, sans-serif"
SPACE_UNIT = 8  # px base spacing unit

# Signature gradient accents (used for hero title, KPI numbers, accent bars).
GRAD_A = "#F0592B"   # warm coral-orange
GRAD_B = "#F2A93B"   # saffron
GRAD_C = "#12776A"   # teal (cool balance)

# National Geographic "explorer's journal" palette — used by the Journey of Food.
NAVY = "#0B1F33"     # deep navy ocean
NAVY_2 = "#16324B"   # lifted navy (land / panels)
AMBER = "#F59E0B"    # warm amber routes
AMBER_HI = "#FDBA3B"  # bright amber core
OLIVE = "#6B8E23"    # olive-green accent
CREAM = "#FFF8E7"    # cream cards


# --- Contrast helpers (pure; no Streamlit dependency) ----------------------
def _srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG contrast ratio between two hex colors (>= 4.5 is AA for body text)."""
    l1, l2 = _relative_luminance(fg), _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def region_color(region: str | None) -> str:
    return REGION_COLORS.get(region or "", REGION_FALLBACK)


# --- Streamlit / Plotly application ---------------------------------------
def inject_theme() -> None:
    """Apply global CSS once per run. Import Streamlit lazily so this module's
    pure helpers stay importable in tests without Streamlit."""
    import streamlit as st

    # Inject CSS via st.markdown
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,700;0,800;0,900;1,500;1,600&family=Inter:wght@400;500;600;700;800&display=swap');

                :root {{
            --primary: {PRIMARY}; --accent: {ACCENT};
            --text: {TEXT_PRIMARY}; --muted: {TEXT_SECONDARY};
            color-scheme: light only;
        }}

        /* Force light-background text to be dark (fixes Streamlit dark mode) */
        .stApp {{
            color: {TEXT_PRIMARY} !important;
        }}
        [data-testid="stAppViewContainer"] p,
        [data-testid="stAppViewContainer"] li,
        [data-testid="stAppViewContainer"] label,
        [data-testid="stAppViewContainer"] summary {{
            color: {TEXT_PRIMARY} !important;
        }}
        .stAlert p {{
            color: #31333F !important;
        }}

        /* Override back to white for text inside dark-background containers */
        .atw-band p, .atw-band h2 {{
            color: #FFFFFF !important;
        }}
        .atw-band .band-sub {{
            color: #F3C9A0 !important;
        }}
        .atw-herobanner-inner p, .atw-herobanner-inner h1 {{
            color: #FFFFFF !important;
        }}
        .atw-herobanner-inner .eyebrow {{
            color: #E8A317 !important;
        }}
        .dh-hero p {{
            color: #FFFFFF !important;
        }}
        .atw-dark-card p {{
            color: #FFFFFF !important;
        }}
        /* Clean modern base: soft warm white with subtle color-mesh accents. */
        .stApp {{
            background:
              radial-gradient(900px 520px at 92% -6%, rgba(242,169,59,0.12) 0%, rgba(242,169,59,0) 60%),
              radial-gradient(820px 520px at 4% 4%, rgba(18,119,106,0.08) 0%, rgba(18,119,106,0) 55%),
              linear-gradient(180deg, {BACKGROUND} 0%, #FFFDFB 100%);
            background-attachment: fixed;
            color: {TEXT_PRIMARY};
            font-family: {FONT_STACK_UI};
        }}

        /* Food vector pattern removed for readability */
        h1, h2, h3, h4 {{ font-family: 'Playfair Display', Georgia, serif !important; color: {TEXT_PRIMARY}; letter-spacing: -0.2px; font-weight: 800; }}
        h1 {{ font-weight: 800; }}
        p, span, div, li, label {{ font-family: {FONT_STACK_UI}; }}
        .block-container {{ padding-top: 0px; max-width: 1280px;
            position: relative; z-index: 1; }}

        /* Cloud overlay removed for readability */

                    50%  {{ transform: translateY(-10px) rotate(4deg); opacity: .95; }}
            100% {{ transform: translateY(6px) rotate(-4deg); opacity: .55; }}
        }}

        /* Sidebar: modern dark "rail" for strong contrast with the light content. */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(185deg, #2B1A12 0%, #40251A 100%);
            border-right: none; box-shadow: inset -1px 0 0 rgba(255,255,255,0.05);
        }}
        section[data-testid="stSidebar"] * {{ color: #F1E4D4; }}
        section[data-testid="stSidebar"] h3 {{ color:#fff !important; letter-spacing:0.02em; }}
        section[data-testid="stSidebar"] .stButton button {{
            font-family: {FONT_STACK_UI}; font-weight: 600; border-radius: 12px;
            background: rgba(255,255,255,0.04); color:#F1E4D4 !important;
            border: 1px solid rgba(255,255,255,0.10); text-align: left; transition: all .15s ease;
        }}
        section[data-testid="stSidebar"] .stButton button:hover {{
            transform: translateX(4px); border-color: {GOLD}; color: #FFFFFF;
            background: rgba(255,255,255,0.08);
        }}
        /* Active nav item (primary) keeps its warm gradient — pops on the dark rail. */
        section[data-testid="stSidebar"] .stButton button[kind="primary"] {{
            color:#FFFFFF !important; border:none; }}

        /* Buttons: gradient, rounded, lift on hover. */
        .stButton button[kind="primary"], .stButton button[data-testid="baseButton-primary"] {{
            background: linear-gradient(135deg, {PRIMARY} 0%, #D64B34 100%);
            border: none; border-radius: 999px; font-weight: 700;
            box-shadow: 0 6px 18px rgba(138,75,18,0.25); transition: all .18s ease;
        }}
        .stButton button[kind="primary"]:hover {{ transform: translateY(-2px);
            box-shadow: 0 10px 26px rgba(138,75,18,0.35); }}

        /* Narrative line. */
        .atw-narrative {{
            font-family: {FONT_STACK}; font-size: 1.35rem; font-style: italic;
            color: {TEXT_SECONDARY}; margin: 8px 0 16px 0; line-height: 1.5;
            opacity: 1 !important;
        }}

        /* Readable captions and labels */
        [data-testid="stCaptionContainer"] p {{
            color: #4a4a4a !important;
        }}

        

        /* Fix input labels and placeholders being invisible */
        [data-testid="stTextInput"] label,
        [data-testid="stSelectbox"] label,
        [data-testid="stMultiSelect"] label,
        .stTextInput label, .stSelectbox label, .stMultiSelect label {{
            color: {TEXT_PRIMARY} !important;
        }}
        [data-testid="stTextInput"] input::placeholder,
        .stTextInput input::placeholder {{
            color: #7a7a7a !important;
            opacity: 1 !important;
        }}
        [data-testid="stTextInput"] input,
        .stTextInput input {{
            color: {TEXT_PRIMARY} !important;
        }}
        /* Info/warning/error boxes text */
        [data-testid="stAlert"] p, [data-testid="stAlert"] span,
        .stAlert p, .stAlert span {{
            color: #31333F !important;
        }}

        /* Cards with hover lift and decorative food corner accent. */
        .atw-card {{
            background: {SURFACE}; border: 1px solid #EFE6D8; border-radius: 16px;
            padding: {SPACE_UNIT * 2}px {SPACE_UNIT * 2.5}px;
            margin-bottom: {SPACE_UNIT * 1.5}px;
            box-shadow: 0 2px 10px rgba(43,33,24,0.06);
            transition: transform .18s ease, box-shadow .18s ease;
            position: relative; overflow: hidden;
        }}
        
        .atw-card:hover {{ transform: translateY(-4px); box-shadow: 0 14px 30px rgba(43,33,24,0.14); }}
        .atw-card h4 {{ margin: 0 0 6px 0; color: {PRIMARY}; font-family: {FONT_STACK_UI};
            font-weight: 700; font-size: 1.05rem; }}
        .atw-unavailable {{ color: #A8998200; color: #9A8C7A; font-style: italic; }}

        /* Netflix-style recommendation posters (Taste Passport). */
        .tp-poster {{ position:relative; border-radius:18px; overflow:hidden; aspect-ratio:3/4;
            background-size:cover; background-position:center; background-color:#2B1A12;
            box-shadow:0 10px 26px rgba(43,33,24,0.20);
            transition: transform .25s ease, box-shadow .25s ease; }}
        .tp-poster:hover {{ transform: translateY(-6px) scale(1.03);
            box-shadow:0 24px 48px rgba(43,33,24,0.34); }}
        .tp-poster .tp-fallback {{ position:absolute; inset:0; display:flex; align-items:center;
            justify-content:center; font-size:3.4rem;
            background: linear-gradient(160deg, {BAND_FROM}, {BAND_TO}); }}
        .tp-poster .tp-overlay {{ position:absolute; inset:0; z-index:1;
            background: linear-gradient(0deg, rgba(15,9,6,0.92) 0%, rgba(15,9,6,0.35) 52%,
                        rgba(15,9,6,0.10) 100%); }}
        .tp-rank {{ position:absolute; top:10px; left:10px; z-index:2;
            background: linear-gradient(135deg, {GRAD_A}, {GRAD_B}); color:#fff !important;
            font-family:{FONT_STACK}; font-weight:900; font-size:1rem; line-height:1;
            width:34px; height:34px; border-radius:50%; display:flex; align-items:center;
            justify-content:center; box-shadow:0 4px 12px rgba(0,0,0,0.35); }}
        .tp-match {{ position:absolute; top:12px; right:12px; z-index:2; color:#FFE7C4 !important;
            font-family:{FONT_STACK_UI}; font-weight:700; font-size:0.74rem;
            background: rgba(0,0,0,0.45); border:1px solid rgba(255,255,255,0.25);
            padding:3px 9px; border-radius:999px;  }}
        .tp-body {{ position:absolute; left:0; right:0; bottom:0; z-index:2; padding:14px 15px;
            color:#fff !important; }}
        .tp-flag {{ font-size:1.6rem; line-height:1; }}
        .tp-name {{ font-family:{FONT_STACK}; font-weight:800; font-size:1.22rem; margin:2px 0 6px 0;
             }}
        .tp-chips {{ display:flex; flex-wrap:wrap; gap:5px; margin-bottom:7px; }}
        .tp-chip {{ background: rgba(255,255,255,0.18); border:1px solid rgba(255,255,255,0.28);
            color:#fff !important; border-radius:999px; padding:2px 9px; font-size:0.72rem; font-weight:600; }}
        .tp-why {{ font-size:0.82rem; color:#F0E7DB !important; line-height:1.35; }}
        .tp-why b {{ color:{GOLD}; }}

        /* Food–Culture–Longevity story (Health tab). */
        .dh-hero {{ display:flex; align-items:center; gap:20px; border-radius:18px;
            padding:20px 26px; margin:8px 0 10px 0; color:#fff !important;
            background:linear-gradient(120deg, {NAVY} 0%, #3a2a1b 60%, {PRIMARY} 140%);
            box-shadow:0 12px 30px rgba(11,31,51,0.25); }}
        .dh-hero .em {{ font-size:3.4rem; line-height:1; filter:drop-shadow(0 4px 10px rgba(0,0,0,.4)); }}
        .dh-hero .big {{ font-family:{FONT_STACK}; font-weight:900; font-size:2.4rem;
            color:{AMBER_HI} !important; line-height:1; }}
        .dh-hero .cap {{ font-family:{FONT_STACK_UI}; font-size:1.02rem; color:#F3E7D6 !important; margin-top:4px; }}
        .dh-list {{ background:{SURFACE}; border:1px solid #EFE6D8; border-radius:14px;
            padding:10px 14px; box-shadow:0 4px 14px rgba(43,33,24,0.06); }}
        .dh-list .h {{ font-family:{FONT_STACK_UI}; font-weight:700; font-size:0.85rem;
            text-transform:uppercase; letter-spacing:0.05em; color:{TEXT_SECONDARY};
            margin-bottom:6px; }}
        .dh-row {{ display:flex; justify-content:space-between; align-items:center;
            padding:5px 0; border-bottom:1px solid #F2E9DA; font-size:0.96rem; }}
        .dh-row:last-child {{ border-bottom:none; }}
        .dh-row .le {{ color:{PRIMARY}; font-weight:700; }}
        .dh-spot {{ background:{CREAM}; border-radius:16px; border-left:5px solid {OLIVE};
            padding:14px 18px; height:100%; box-shadow:0 6px 18px rgba(43,33,24,0.09); }}
        .dh-spot .n {{ font-family:{FONT_STACK}; font-weight:800; font-size:1.2rem; color:{NAVY}; }}
        .dh-spot .k {{ margin:6px 0; }}
        .dh-spot .k span {{ display:inline-block; background:#EFE7D6; border-radius:999px;
            padding:2px 9px; margin:2px 3px 0 0; font-size:0.8rem; color:{NAVY}; }}
        .dh-spot .why {{ color:#4A3F35; font-size:0.92rem; }}
        .dh-spot .why b {{ color:{PRIMARY}; }}

        /* Country Story — taste profile & "who shares my plate" cards. */
        .cs-taste {{ display:flex; flex-wrap:wrap; gap:10px 26px; margin:6px 0 2px 0; }}
        .cs-taste .row {{ display:flex; align-items:center; gap:8px; min-width:170px; }}
        .cs-taste .lab {{ color:{TEXT_PRIMARY}; font-weight:600; font-size:0.95rem; min-width:104px; }}
        .cs-taste .stars {{ color:{GOLD}; letter-spacing:2px; font-size:1rem; }}
        .cs-taste .stars .off {{ color:#E4D8C2; }}
        .cs-share {{ display:flex; flex-wrap:wrap; gap:12px; margin:6px 0; }}
        .cs-share .c {{ flex:1 1 210px; background:{SURFACE}; border:1px solid #EFE6D8;
            border-left:5px solid {ACCENT}; border-radius:14px; padding:12px 15px;
            box-shadow:0 4px 14px rgba(43,33,24,0.07); transition:transform .18s ease; }}
        .cs-share .c:hover {{ transform:translateY(-4px); box-shadow:0 14px 28px rgba(43,33,24,0.15); }}
        .cs-share .name {{ font-family:{FONT_STACK}; font-weight:800; font-size:1.1rem;
            color:{TEXT_PRIMARY}; }}
        .cs-share .pct {{ float:right; color:{ACCENT}; font-weight:800; }}
        .cs-share .shared {{ color:{TEXT_SECONDARY}; font-size:0.85rem; margin-top:4px; }}
        .cs-substat {{ color:{TEXT_SECONDARY}; font-size:0.82rem; text-align:center;
            margin:-6px 0 8px 0; }}

        /* Explore-map click preview card. */
        .xp-card {{ display:flex; gap:0; background:{CREAM}; border-radius:18px; overflow:hidden;
            border:1px solid #EFDFC4; box-shadow:0 14px 34px rgba(11,31,51,0.18);
            margin:12px 0 6px 0; }}
        .xp-photo {{ flex:0 0 40%; min-height:220px; background-size:cover; background-position:center;
            background-color:{NAVY_2}; }}
        .xp-info {{ flex:1 1 60%; padding:18px 22px; }}
        .xp-title {{ font-family:{FONT_STACK}; font-weight:800; font-size:1.7rem; color:{NAVY};
            display:flex; align-items:baseline; gap:10px; }}
        .xp-tag {{ color:{OLIVE}; font-weight:700; font-style:italic; font-size:1rem; }}
        .xp-pills {{ margin:8px 0; }}
        .xp-pill {{ display:inline-block; background:#F4E9D6; border:1px solid #E7D6B8;
            border-radius:999px; padding:2px 11px; margin:3px 3px 0 0; font-size:0.85rem;
            color:{NAVY}; }}
        .xp-stats {{ display:flex; gap:18px; flex-wrap:wrap; margin-top:10px; }}
        .xp-stat {{ text-align:center; }}
        .xp-stat .v {{ font-family:{FONT_STACK}; font-weight:800; font-size:1.25rem; color:{PRIMARY}; }}
        .xp-stat .l {{ font-size:0.72rem; text-transform:uppercase; letter-spacing:0.05em;
            color:{TEXT_SECONDARY}; }}

        /* Journey of Food — "explorer's journal" voyage cards & stats (NatGeo palette). */
        .vy-stats {{ display:flex; flex-wrap:wrap; gap:12px; margin:6px 0 14px 0; }}
        .vy-stat {{ flex:1 1 130px; background:{NAVY_2}; border:1px solid rgba(245,158,11,0.35);
            border-radius:14px; padding:14px 12px; text-align:center; color:{CREAM} !important;
            box-shadow:0 8px 22px rgba(11,31,51,0.28); }}
        .vy-stat .s-ico {{ font-size:1.5rem; }}
        .vy-stat .s-val {{ font-family:{FONT_STACK}; font-weight:800; font-size:1.35rem;
            color:{AMBER_HI} !important; margin:2px 0; }}
        .vy-stat .s-lab {{ font-size:0.72rem; text-transform:uppercase; letter-spacing:0.06em;
            color:#CBB89A !important; }}
        .vy-card {{ position:relative; background:{CREAM}; border-radius:16px;
            border-left:6px solid {AMBER}; padding:14px 18px 14px 20px; margin:10px 0;
            box-shadow:0 8px 22px rgba(43,33,24,0.12); }}
        .vy-card .vy-step {{ position:absolute; top:-12px; left:-12px; width:30px; height:30px;
            border-radius:50%; background:linear-gradient(135deg,{AMBER},{GRAD_A}); color:#fff !important;
            font-family:{FONT_STACK}; font-weight:800; display:flex; align-items:center;
            justify-content:center; box-shadow:0 4px 10px rgba(0,0,0,0.28); font-size:0.9rem; }}
        .vy-card .vy-place {{ font-family:{FONT_STACK}; font-weight:800; font-size:1.2rem;
            color:{NAVY}; }}
        .vy-card .vy-era {{ color:{OLIVE}; font-weight:700; font-size:0.82rem;
            text-transform:uppercase; letter-spacing:0.05em; margin-left:8px; }}
        .vy-card .vy-fact {{ color:#4A3F35; font-size:0.98rem; margin-top:5px; line-height:1.4; }}

        /* Visually hidden but available to screen readers & the document outline. */
        .atw-sronly {{ position:absolute !important; width:1px; height:1px; padding:0; margin:-1px;
            overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }}

        /* Pills. */
        .atw-pill {{ display:inline-block; background:#F4EADB; color:{TEXT_PRIMARY};
            border:1px solid #E7D6B8; border-radius:999px; padding:3px 12px; margin:3px;
            font-size:.9rem; transition: all .15s ease; }}
        .atw-pill:hover {{ background:{PRIMARY}; color:#fff !important; transform: scale(1.06); }}

        /* Hero for the landing page. */
        .atw-hero {{
            text-align:center; padding: 10px 0 4px 0;
        }}
        .atw-hero h1 {{ font-size: 3rem; margin-bottom: 2px;
            background: linear-gradient(90deg, {PRIMARY}, {GOLD}, {ACCENT});
            color: #C0392B; }}
        .atw-hero .tagline {{ font-family:{FONT_STACK}; font-style:italic; color:{TEXT_SECONDARY};
            font-size:1.15rem; }}

        /* Teaser cards (curiosity hooks). */
        .atw-teaser {{ background:{SURFACE}; border:1px solid #EFE6D8; border-radius:16px;
            padding:16px 18px; height:100%; box-shadow:0 2px 10px rgba(43,33,24,0.06);
            transition: transform .18s ease, box-shadow .18s ease; }}
        .atw-teaser:hover {{ transform: translateY(-5px); box-shadow:0 16px 32px rgba(43,33,24,0.16); }}
        .atw-teaser .emoji {{ font-size: 2rem; }}
        .atw-teaser .t-title {{ font-family:{FONT_STACK}; font-weight:700; font-size:1.1rem;
            margin:6px 0 2px 0; }}
        .atw-teaser .t-sub {{ color:{TEXT_SECONDARY}; font-size:.92rem; }}

        /* Discovery insight callout — with spice vector accent. */
        .atw-insight {{
            position: relative; overflow: hidden;
            background: linear-gradient(135deg, #FFF4DC 0%, #FCE9C4 100%);
            border-left: 6px solid {GOLD}; border-radius: 12px;
            padding: {SPACE_UNIT * 1.75}px {SPACE_UNIT * 2.25}px;
            margin: 16px 0; font-family: {FONT_STACK_UI};
            box-shadow: 0 4px 14px rgba(138,75,18,0.10);
        }}
        
        .atw-insight .atw-insight-label {{
            font-weight: 800; color: {PRIMARY}; text-transform: uppercase;
            letter-spacing: 0.08em; font-size: 0.78rem;
        }}
        .atw-insight div:last-child {{ font-size: 1.05rem; }}

        .atw-badge {{ display:inline-block;
            background: linear-gradient(135deg, {ACCENT}, #2E8C74); color:{TEXT_ON_PRIMARY};
            font-size:0.7rem; padding:2px 9px; border-radius:999px; margin-left:6px; font-weight:700; }}

        /* Full-bleed photographic hero banner — compact. */
        .atw-herobanner {{
            position: relative; border-radius: 24px; overflow: hidden;
            min-height: 300px; display: flex; align-items: flex-end; margin: 0 0 6px 0;
            box-shadow: 0 26px 60px rgba(43,33,24,0.30);
            isolation: isolate;
        }}
        /* Slow Ken Burns zoom/pan on the background photo — makes the hero feel alive. */
        .atw-hero-bg {{ position:absolute; inset:-6% ; background-size:cover;
            background-position:center; z-index:0; transform:scale(1.04);
            animation: atwKenBurns 26s ease-in-out infinite alternate; }}
        @keyframes atwKenBurns {{
            from {{ transform: scale(1.04) translate(0,0); }}
            to   {{ transform: scale(1.18) translate(-2%,-3%); }}
        }}
        /* Rich readable overlay + a moving warm glow. */
        .atw-hero-tint {{ position:absolute; inset:0; z-index:1;
            background: linear-gradient(105deg, rgba(20,12,8,0.82) 0%, rgba(20,12,8,0.45) 45%,
                        rgba(20,12,8,0.15) 100%),
                        linear-gradient(0deg, rgba(20,12,8,0.55) 0%, rgba(20,12,8,0) 55%); }}
        .atw-hero-glow {{ display:none; }}
            to {{ transform: translate(-30px,26px); opacity:1; }} }}
        .atw-herobanner-inner {{ position:relative; z-index:2; padding: 30px 36px; color: #fff;
            max-width: 860px; }}
        .atw-herobanner-inner .eyebrow {{ font-family:{FONT_STACK_UI}; font-weight:700;
            text-transform:uppercase; letter-spacing:0.24em; font-size:0.8rem;
            color:{GOLD}; margin-bottom:12px; }}
        .atw-herobanner-inner h1 {{ font-family:{FONT_STACK}; font-weight:900; color:#fff !important;
            font-size: 3rem; line-height:1.05; margin: 0; letter-spacing:-1px;
            background: linear-gradient(92deg, #FFFFFF 0%, #FFE7C4 40%, {GOLD} 62%, #FFFFFF 100%);
            background-size: 220% auto; -webkit-background-clip:text; background-clip:text;
            -webkit-text-fill-color: transparent;
            
            animation: atwShine 7s linear infinite; }} }}
        .atw-herobanner-inner p {{ font-family:{FONT_STACK}; font-style:italic; font-size:1.15rem;
            margin: 10px 0 0 0; max-width:660px; color:#2A2320;
             }}
        .atw-hero-scroll {{ display:flex; align-items:center; gap:10px; margin-top:26px;
            font-family:{FONT_STACK_UI}; font-size:0.82rem; letter-spacing:0.14em;
            text-transform:uppercase; color:rgba(255,255,255,0.85); }}
        .atw-hero-scroll span {{ width:22px; height:34px; border:2px solid rgba(255,255,255,0.7);
            border-radius:12px; position:relative; }}
        .atw-hero-scroll span::after {{ content:""; position:absolute; left:50%; top:6px;
            width:3px; height:7px; background:#fff; border-radius:2px; transform:translateX(-50%);
            animation: atwScroll 1.6s ease-in-out infinite; }} 40%{{opacity:1;}} 80%{{opacity:0;top:16px;}} 100%{{opacity:0;}} }}

        /* Surprising-fact cards — rounded with visible hover state. */
        .atw-fact {{ background: linear-gradient(135deg, #FFFFFF 0%, #FFF6E9 100%);
            border:1.5px solid #EFE0C8; border-radius:20px; padding:20px 22px; text-align:center;
            box-shadow:0 4px 16px rgba(43,33,24,0.08); height:100%;
            transition: all 0.22s ease; overflow:hidden; }}
        .atw-fact:hover {{ transform: translateY(-5px);
            box-shadow:0 16px 36px rgba(232,163,23,0.2);
            border-color:#E8A317; }}
        .atw-fact .f-emoji {{ font-size:2.2rem; }}
        .atw-fact .f-big {{ font-family:{FONT_STACK}; font-weight:800; font-size:1.15rem;
            color:{PRIMARY}; margin:6px 0 4px 0; line-height:1.25; }}
        .atw-fact .f-small {{ color:{TEXT_SECONDARY}; font-size:0.92rem; }}

        /* Bold hero-style metric card. */
        .atw-bigstat {{ text-align:center; padding:18px 16px; }}
        .atw-bigstat .bs-icon {{ font-size:2rem; }}
        .atw-bigstat .bs-label {{ color:{TEXT_SECONDARY}; font-size:0.9rem; font-weight:600;
            text-transform:uppercase; letter-spacing:0.04em; margin:4px 0 6px 0; }}
        .atw-bigstat .bs-value {{ font-family:{FONT_STACK}; font-weight:800; font-size:2rem;
            color:{PRIMARY}; }}

        /* Section header band for inner pages — with food vector art overlay. */
        .atw-band {{ position:relative; overflow:hidden;
            background: linear-gradient(120deg, {BAND_FROM} 0%, {BAND_TO} 100%);
            color:#FDECCF !important; border-radius:16px; padding:18px 24px; margin: 4px 0 16px 0;
            box-shadow:0 8px 24px rgba(58,30,61,0.28);
            border-bottom: 3px solid {GOLD}; }}
        
        .atw-band h2 {{ color:#FFF !important; margin:0; position:relative; }}
        .atw-band .band-sub {{ color:#F3C9A0 !important; font-family:{FONT_STACK}; font-style:italic; margin-top:2px; position:relative; }}

        /* Animated KPI counters (landing page) — glassy, gradient numbers, glow border. */
        .atw-kpis {{ display:flex; flex-wrap:wrap; gap:16px; justify-content:center;
            margin:24px 0 16px 0; }}
        .atw-kpi {{ position:relative; flex:1 1 150px; max-width:220px; text-align:center;
            background: rgba(255,255,255,0.72); 
            border:1px solid rgba(255,255,255,0.6); border-radius:20px; padding:22px 14px;
            box-shadow:0 10px 30px rgba(43,33,24,0.10);
            transition: transform .22s ease, box-shadow .22s ease; }}
        .atw-kpi::before {{ content:""; position:absolute; inset:0; border-radius:20px; padding:1.5px;
            background: linear-gradient(135deg, {GRAD_A}, {GRAD_B} 55%, {GRAD_C});
            -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
            -webkit-mask-composite: xor; mask-composite: exclude;
            opacity:0; transition: opacity .25s ease; }}
        .atw-kpi:hover {{ transform: translateY(-8px) scale(1.02);
            box-shadow:0 24px 46px rgba(43,33,24,0.20); }}
        .atw-kpi:hover::before {{ opacity:1; }}
        .atw-kpi .k-emoji {{ font-size:2.2rem; line-height:1;
            filter: drop-shadow(0 4px 8px rgba(43,33,24,0.18)); }}
        .atw-kpi .k-value {{ font-family:{FONT_STACK}; font-weight:900; font-size:2.35rem;
            margin:8px 0 4px 0; letter-spacing:0.3px;
            display:flex; align-items:baseline; justify-content:center; gap:1px;
            background: linear-gradient(120deg, {GRAD_A}, {GRAD_B});
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
        .atw-kpi .k-suffix, .atw-kpi .k-prefix {{ font-size:1.5rem; font-weight:900;
            background: linear-gradient(120deg, {GRAD_A}, {GRAD_B});
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
        .atw-kpi .k-label {{ color:{TEXT_SECONDARY}; font-size:0.82rem; font-weight:700;
            text-transform:uppercase; letter-spacing:0.06em; }}

        /* Click-to-reveal country fact card (Travel dashboard). */
        .tv-factcard {{ background: linear-gradient(135deg, #FFFFFF 0%, #FFF3E0 100%);
            border:1px solid #EFDFC4; border-left:6px solid {PRIMARY}; border-radius:16px;
            padding:16px 20px; margin:10px 0 4px 0; box-shadow:0 8px 26px rgba(43,33,24,0.12); }}
        .tv-facthead {{ font-family:{FONT_STACK}; font-weight:800; font-size:1.35rem;
            color:{BAND_FROM}; display:flex; align-items:baseline; gap:12px; }}
        .tv-facthead span {{ font-family:{FONT_STACK_UI}; font-weight:600; font-size:0.82rem;
            color:{TEXT_SECONDARY}; text-transform:uppercase; letter-spacing:0.06em; }}
        .tv-factrow {{ display:flex; flex-wrap:wrap; gap:14px; margin-top:12px; }}
        .tv-fact {{ flex:1 1 130px; background:#FFFBF3; border:1px solid #F0E4CF;
            border-radius:12px; padding:12px 14px; text-align:center; }}
        .tv-fact .tv-fe {{ font-size:1.5rem; }}
        .tv-fact .tv-fb {{ font-family:{FONT_STACK}; font-weight:800; font-size:1.25rem;
            color:{PRIMARY}; margin:4px 0 2px 0; }}
        .tv-fact .tv-fs {{ color:{TEXT_SECONDARY}; font-size:0.82rem; line-height:1.2; }} to {{ opacity:1; transform:none; }} }} to {{ opacity:1; transform:none; }} }}
        </style>
        """,
        unsafe_allow_html=True,

    )


def plotly_template() -> dict:
    """Shared Plotly layout template applying data visualization best practices.
    
    Principles applied:
    - Clean, minimal chrome (no gridlines unless needed)
    - Clear axis labels with readable font sizes
    - Consistent color palette across all charts
    - Adequate whitespace / margins for readability
    - No 3D effects or distortion
    """
    return {
        "layout": {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(255,248,241,0.5)",
            "font": {"color": TEXT_PRIMARY, "family": FONT_STACK_UI, "size": 13},
            "colorway": [PRIMARY, ACCENT, GOLD, "#4A72B0", "#8E6BB0", "#2A9D8F", "#E15C4A"],
            "title": {"font": {"family": FONT_STACK_UI, "size": 16, "color": TEXT_PRIMARY}},
            "xaxis": {
                "showgrid": False,
                "zeroline": False,
                "linecolor": "#EFE6D8",
                "tickfont": {"size": 11, "color": TEXT_SECONDARY},
                "title": {"font": {"size": 12, "color": TEXT_SECONDARY}},
            },
            "yaxis": {
                "showgrid": True,
                "gridcolor": "rgba(239,230,216,0.6)",
                "gridwidth": 1,
                "zeroline": False,
                "linecolor": "#EFE6D8",
                "tickfont": {"size": 11, "color": TEXT_SECONDARY},
                "title": {"font": {"size": 12, "color": TEXT_SECONDARY}},
            },
            "hoverlabel": {
                "bgcolor": "#FFFFFF",
                "bordercolor": "#EFE6D8",
                "font": {"size": 12, "color": TEXT_PRIMARY, "family": FONT_STACK_UI},
            },
            "margin": {"t": 40, "b": 40, "l": 50, "r": 20},
        }
    }
