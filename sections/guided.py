"""Guided journey — a country-first, progressive-disclosure story flow.

Instead of showing everything at once, the visitor moves through stages:
    prologue  -> an invitation
    choose    -> pick a country on the world map
    country   -> that country's story unfolds chapter by chapter (each narratable)
    bigpicture-> zoom out to the global chapters

State lives in st.session_state["journey_stage"] and ["open_chapters"]. Existing
section modules are reused as chapter bodies so nothing is duplicated.
"""
from __future__ import annotations

import base64
import html as _html
from functools import lru_cache
from pathlib import Path

import streamlit as st

import config
from components import cards
from components.flags import flag
from components.voice import narrate
from data import repository as repo


# ---------------------------------------------------------------------------
# Imagery helpers — embed the dataset's food photos as data URIs so they render
# inside HTML/CSS (browsers can't load local file paths directly).
# ---------------------------------------------------------------------------
def _data_uri(path: str) -> str | None:
    try:
        raw = Path(path).read_bytes()
        # Detect the real image format from magic bytes (extensions can be wrong,
        # e.g. a WebP saved as .jpg), so the browser always renders it.
        if raw[:8].startswith(b"\x89PNG"):
            mime = "image/png"
        elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            mime = "image/webp"
        elif raw[:3] == b"\xff\xd8\xff":
            mime = "image/jpeg"
        elif raw[4:8] == b"ftyp" and b"avif" in raw[8:20]:
            mime = "image/avif"
        else:
            ext = Path(path).suffix.lower()
            mime = {".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
        return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
    except Exception:  # noqa: BLE001
        return None


@lru_cache(maxsize=64)
def _scenery_src(iso3: str) -> str | None:
    """A scenery/heritage hero image for the country (assets/country/<iso3>.<ext>).

    If several files share the ISO3 name (e.g. an old .jpg and a new .webp), the most
    recently modified one wins — so a freshly added image always takes precedence.
    """
    base = Path(__file__).resolve().parents[1] / "assets" / "country"
    candidates = [
        p for ext in (".jpg", ".jpeg", ".png", ".webp")
        for p in [base / f"{iso3}{ext}"]
        if p.exists() and p.stat().st_size > 0
    ]
    if not candidates:
        return None
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    return _data_uri(str(newest))


@lru_cache(maxsize=64)
def _country_media(iso3: str) -> tuple[str | None, tuple[str, ...]]:
    """(hero_src, gallery_srcs) built from the country's own dish photos.

    Returns browser-ready data URIs for whatever local dish images exist. The first
    image doubles as the hero banner; the rest feed the chapter-card backgrounds.
    """
    from components.images import _local_image

    try:
        dishes = repo.get_dishes(iso3)["name"].tolist()
    except Exception:  # noqa: BLE001
        dishes = (repo.get_country_profile(iso3) or {}).get("dishes") or []

    srcs: list[str] = []
    for dish in dishes:
        local = _local_image(dish)
        if not local:
            continue
        uri = _data_uri(local)
        if uri and uri not in srcs:
            srcs.append(uri)
    hero = srcs[0] if srcs else None
    return hero, tuple(srcs)

# Per-country chapters: (id, emoji, title, teaser question).
CHAPTERS = [
    ("story", "📖", "The Story", "Who gathers at this table?"),
    ("plate", "🍽️", "The Plate", "What fills a plate here?"),
    ("planet", "🌱", "The Planet Cost", "What does this plate cost the Earth?"),
    ("kindred", "🤝", "Kindred Kitchens", "Which distant nations cook alike?"),
    ("celebrations", "🎉", "Celebrations", "How does this culture feast?"),
]
_CHAPTER_TITLES = {c[0]: (c[1], c[2]) for c in CHAPTERS}

# Shared source of truth for the prologue narration (also used to pre-generate audio).
PROLOGUE_NARRATION = (
    "Every morning, eight billion of us wake to the same simple need... and answer it in a "
    "thousand different ways. A bowl of rice. A loaf still warm. Spices ground before dawn. "
    "Every plate is a small story about how a people live, and love, and remember. Choose a "
    "country, and let its food begin to tell you its story."
)

# Directory of pre-generated Amazon Polly narration (see scripts/generate_narration.py).
_AUDIO_DIR = "assets/audio"


def _audio_file(key: str) -> str:
    """Path (relative to project root) of a pre-generated narration MP3 for `key`."""
    return f"{_AUDIO_DIR}/{key}.mp3"


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------
def _goto(stage: str, **extra) -> None:
    st.session_state["journey_stage"] = stage
    for k, v in extra.items():
        st.session_state[k] = v
    st.rerun()


def _open_chapters(iso3: str) -> list[str]:
    store = st.session_state.setdefault("open_chapters", {})
    return store.setdefault(iso3, [])


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        .gj-eyebrow { text-align:center; font-family:'Inter',sans-serif; font-weight:700;
            text-transform:uppercase; letter-spacing:0.22em; font-size:0.74rem;
            color:#C0392B; margin:4px 0 2px 0; }
        .gj-chapters-intro { text-align:center; color:#574B42; font-size:1.02rem;
            margin:6px 0 2px 0; }
        /* Country hero — full-bleed cover banner, edge to edge, no gaps */
        .gj-hero { position:relative; width:100vw; margin-left:calc(50% - 50vw);
            height:58vh; min-height:420px; overflow:hidden; display:flex;
            align-items:flex-end; margin-top:8px; margin-bottom:18px;
            background-size:cover; background-position:center;
            box-shadow:0 18px 40px rgba(43,33,24,0.28); }
        .gj-hero--grad { background:linear-gradient(120deg,#2E1C15 0%,#8A3324 100%); }
        .gj-hero-shade { position:absolute; inset:0; z-index:1; pointer-events:none;
            background:linear-gradient(0deg, rgba(20,12,8,0.85) 0%,
                rgba(20,12,8,0.30) 40%, rgba(20,12,8,0) 72%); }
        .gj-hero-inner { position:relative; z-index:2; width:100%;
            padding:0 60px 34px 60px; }
        /* Choose-stage preview card — full image on top, info below (no crop) */
        .gj-prev { background:#FFFFFF; border:1px solid #EFE6D8; border-radius:20px;
            overflow:hidden; box-shadow:0 12px 30px rgba(43,33,24,0.12);
            margin:14px auto 8px auto; max-width:1000px; }
        .gj-prev-img { display:block; width:100%; height:auto; }
        .gj-prev-body { padding:18px 24px 20px 24px; }
        .gj-prev-title { font-family:'Playfair Display',Georgia,serif; font-weight:800;
            font-size:1.7rem; color:#2A2320; display:flex; align-items:baseline; gap:10px;
            flex-wrap:wrap; }
        .gj-prev-tag { color:#1F6F5C; font-weight:700; font-style:italic; font-size:1rem; }
        .gj-prev-eyebrow { font-size:0.72rem; color:#574B42; text-transform:uppercase;
            letter-spacing:0.06em; font-weight:600; margin-top:2px; }
        .gj-prev-pills { margin:10px 0 2px 0; }
        .gj-prev-pill { display:inline-block; background:#F4E9D6; border:1px solid #E7D6B8;
            border-radius:999px; padding:3px 11px; margin:3px 3px 0 0; font-size:0.84rem;
            color:#2A2320; }
        .gj-prev-stats { display:flex; gap:22px; flex-wrap:wrap; margin-top:12px; }
        .gj-prev-stat { text-align:center; }
        .gj-prev-stat .v { font-family:'Playfair Display',Georgia,serif; font-weight:800;
            font-size:1.25rem; color:#C0392B; }
        .gj-prev-stat .l { font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em;
            color:#574B42; }
        .gj-hero-inner-legacy { position:relative; z-index:2; padding:30px 38px; max-width:820px; }
        .gj-hero-eyebrow { font-family:'Inter',sans-serif; font-weight:700;
            text-transform:uppercase; letter-spacing:0.22em; font-size:0.78rem;
            color:#F2A93B; margin-bottom:8px; }
        .gj-hero-title { font-family:'Playfair Display',Georgia,serif; font-weight:900;
            font-size:3rem; line-height:1.03; margin:0; color:#FFF8F1 !important;
            letter-spacing:-0.5px; text-shadow:0 2px 18px rgba(0,0,0,0.45); }
        .gj-hero-tagline { font-family:'Playfair Display',Georgia,serif; font-style:italic;
            font-size:1.25rem; color:#FFE7C4; margin-top:10px; text-shadow:0 2px 12px rgba(0,0,0,0.5); }
        /* Photo-backed chapter cards */
        .gj-card.photo { color:#fff; border:none; background-size:cover;
            background-position:center; min-height:168px; display:flex;
            flex-direction:column; justify-content:flex-end; text-align:left;
            box-shadow:0 8px 22px rgba(43,33,24,0.22); }
        .gj-card.photo:hover { border:none; box-shadow:0 20px 40px rgba(43,33,24,0.34); }
        .gj-card.photo .gj-emoji { font-size:1.9rem; filter:drop-shadow(0 3px 8px rgba(0,0,0,0.5)); }
        .gj-card.photo .gj-title { color:#FFF8F1; }
        .gj-card.photo .gj-teaser { color:rgba(255,248,241,0.9); }
        .gj-card.photo .gj-check { color:#7CF0C0; }
        /* Chapter selection cards */
        .gj-card { position:relative; background:#FFFFFF; border:1.5px solid #EFE6D8;
            border-radius:18px; padding:20px 16px; text-align:center; height:100%;
            box-shadow:0 3px 12px rgba(43,33,24,0.06); transition:all .22s ease; }
        .gj-card:hover { transform:translateY(-5px); box-shadow:0 16px 32px rgba(43,33,24,0.14);
            border-color:#E8A317; }
        .gj-card.done { border-color:#1F6F5C; background:linear-gradient(135deg,#FFFFFF,#F1FAF6); }
        .gj-card .gj-emoji { font-size:2.3rem; line-height:1;
            filter:drop-shadow(0 3px 6px rgba(0,0,0,0.12)); }
        .gj-card .gj-title { font-family:'Playfair Display',Georgia,serif; font-weight:800;
            font-size:1.12rem; color:#2A2320; margin:8px 0 3px 0; }
        .gj-card .gj-teaser { font-size:0.8rem; color:#574B42; line-height:1.35; }
        .gj-card .gj-check { position:absolute; top:10px; right:12px; color:#1F6F5C;
            font-weight:800; font-size:0.9rem; }
        .gj-chapter-open { background:linear-gradient(135deg,#FFF8F1,#FFF3E5);
            border:1px solid #EFDFC4; border-left:5px solid #C0392B; border-radius:18px;
            padding:6px 22px 18px 22px; margin:6px 0 22px 0;
            box-shadow:0 10px 30px rgba(43,33,24,0.10); animation:gjRise .45s ease both; }
        @keyframes gjRise { from{opacity:0;transform:translateY(14px);} to{opacity:1;transform:none;} }
        .gj-chapter-head { font-family:'Playfair Display',Georgia,serif; font-weight:800;
            font-size:1.5rem; color:#2A2320; margin:14px 0 4px 0; }
        .gj-progress { text-align:center; color:#8A3324; font-weight:700; font-size:0.86rem;
            letter-spacing:0.04em; margin:10px 0; }
        /* Prominent "next step" banner to the Big Picture */
        .gj-nextcta { display:flex; align-items:center; gap:18px; margin:26px 0 12px 0;
            padding:22px 28px; border-radius:20px;
            background:linear-gradient(120deg,#2E1C15 0%,#5A2A1E 60%,#8A3324 140%);
            box-shadow:0 16px 40px rgba(46,28,21,0.30); }
        .gj-nextcta-emoji { font-size:2.6rem; line-height:1;
            filter:drop-shadow(0 3px 8px rgba(0,0,0,0.4)); }
        .gj-nextcta-title { font-family:'Playfair Display',Georgia,serif; font-weight:800;
            font-size:1.5rem; color:#FFF8F1; }
        .gj-nextcta-sub { color:#F3C9A0; font-size:0.98rem; margin-top:2px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Contextual top bar (replaces the old fixed nav)
# ---------------------------------------------------------------------------
def _bar(center_html: str, *, actions=None, right=None) -> None:
    """A slim contextual bar: left action buttons, a centered title, one right action.

    actions : list of (label, key, stage) rendered on the left (e.g. Home, Countries).
    right   : optional (label, key, stage) rendered on the far right.
    """
    actions = actions or []
    spec = [1] * len(actions) + [3.2] + ([1.4] if right else [])
    cols = st.columns(spec)
    for i, (label, key, stage) in enumerate(actions):
        with cols[i]:
            if st.button(label, key=key, use_container_width=True):
                _goto(stage)
    with cols[len(actions)]:
        st.markdown(
            f"<div style='text-align:center;font-family:Playfair Display,serif;"
            f"font-weight:800;font-size:1.05rem;color:#2A2320;padding-top:6px;'>"
            f"{center_html}</div>", unsafe_allow_html=True)
    if right:
        with cols[-1]:
            if st.button(right[0], key=right[1], use_container_width=True, type="primary"):
                _goto(right[2])


# ---------------------------------------------------------------------------
# Stage: prologue
# ---------------------------------------------------------------------------
def _prologue() -> None:
    import base64
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    static_video = root / "static" / "hero.mp4"
    if static_video.exists():
        st.markdown(f"<h1 class='atw-sronly'>{config.APP_TITLE}</h1>", unsafe_allow_html=True)
        cards.video_hero("app/static/hero.mp4?v=2", config.APP_TITLE, config.APP_TAGLINE)
    else:
        hero = root / "assets" / "food" / "_hero.jpg"
        src = None
        if hero.exists():
            src = "data:image/jpeg;base64," + base64.b64encode(hero.read_bytes()).decode("ascii")
        cards.hero_banner(src, config.APP_TITLE, config.APP_TAGLINE)

    st.markdown(
        "<div class='atw-narrative' style='text-align:center;margin-top:14px'>"
        "Every country wakes up and eats differently. Pick one, and let its food tell you "
        "how it lives, celebrates, and connects to the rest of the world.</div>",
        unsafe_allow_html=True,
    )

    narrate(PROLOGUE_NARRATION, label="Hear the invitation",
            audio_file=_audio_file("prologue"), rate=1.0, pitch=1.05, height=70)

    try:
        k = repo.landing_kpis()
        cards.kpi_counters([
            {"emoji": "🌍", "value": k["countries"], "label": "Countries"},
            {"emoji": "🍛", "value": k["dishes"], "label": "Signature dishes"},
            {"emoji": "🏛", "value": k["heritage_sites"], "label": "Heritage sites"},
            {"emoji": "🎉", "value": k["festivals"] + k["culinary"], "label": "Traditions"},
        ])
    except Exception:  # noqa: BLE001
        pass

    left, mid, right = st.columns([1, 1.2, 1])
    with mid:
        if st.button("Begin the journey  →", type="primary", use_container_width=True):
            _goto("choose")
        if st.button("🎲  Surprise me with a country", use_container_width=True):
            _surprise()


def _surprise() -> None:
    import random
    try:
        options = repo.dish_countries()
    except Exception:  # noqa: BLE001
        options = []
    if options:
        _goto("country", selected_country=random.choice(options))


# ---------------------------------------------------------------------------
# Stage: choose a country
# ---------------------------------------------------------------------------
def _choose() -> None:
    from viz.choropleth import build_explore_map
    from sections.explore_map import _selected_iso3

    _bar("Choose a country to explore",
         actions=[("🏠  Home", "gj_choose_home", "prologue")])

    st.markdown("<div class='gj-eyebrow'>Chapter One · The Map</div>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;color:#2A2320;font-size:1.06rem;margin:2px 0 10px 0'>"
        "The world map is your table of contents. <b>Click any glowing country</b> to open "
        "its story.</p>", unsafe_allow_html=True)

    try:
        countries = repo.countries_for_map()
        stats = repo.map_hover_stats()
    except Exception:  # noqa: BLE001
        st.warning("The map is unavailable right now.")
        return
    if countries.empty:
        st.info("No countries are available to explore yet.")
        return

    story = countries[countries["has_story"].astype(bool)]
    selected = st.session_state.get("explore_selected")
    fig, alt = build_explore_map(countries, selected=selected, hover_stats=stats)
    # Give the world map enough height and a centered, non-full-bleed width so the
    # whole map shows instead of being clipped top-and-bottom.
    fig.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0))
    _mleft, _mmid, _mright = st.columns([0.1, 0.8, 0.1])
    with _mmid:
        event = st.plotly_chart(
            fig, width="stretch", on_select="rerun", selection_mode="points",
            key="gj_map_select", config={"displayModeBar": False, "scrollZoom": False},
        )

    iso3 = _selected_iso3(event)
    if iso3 and iso3 != selected:
        if bool(story["iso3"].eq(iso3).any()):
            st.session_state["explore_selected"] = iso3
            st.session_state["selected_country"] = iso3
            st.rerun()
        else:
            row = countries[countries["iso3"] == iso3]
            nm = row.iloc[0]["name"] if not row.empty else iso3
            st.info(f"No food story for {nm} yet — try a glowing country.")

    if selected:
        _choose_preview(selected)
    else:
        st.markdown(f"<p style='color:#574B42;font-size:0.9rem;'>{alt}</p>",
                    unsafe_allow_html=True)


def _choose_preview(iso3: str) -> None:
    """A teaser card for the highlighted country + the single button that enters it."""
    from sections.country_story import _tagline

    profile = repo.get_country_profile(iso3) or {}
    name = profile.get("name", iso3)
    region = profile.get("region") or ""
    tagline = _tagline(iso3, profile)

    dishes = [d for d in (profile.get("dishes") or [])][:4]
    fests = [f for f in (profile.get("festivals") or [])][:2]
    pills = "".join(f'<span class="gj-prev-pill">🍽 {_html.escape(d)}</span>' for d in dishes)
    pills += "".join(f'<span class="gj-prev-pill">🎉 {_html.escape(f)}</span>' for f in fests)

    def _stat(v, label, suffix=""):
        if v is None or (isinstance(v, float) and v != v):
            return ""
        val = f"{int(v):,}" if isinstance(v, (int, float)) else str(v)
        return (f'<div class="gj-prev-stat"><div class="v">{val}{suffix}</div>'
                f'<div class="l">{label}</div></div>')

    life = profile.get("life_expectancy")
    stats = "".join([
        _stat(int(life) if life is not None else None, "Life exp", " yrs"),
        _stat(profile.get("unesco_heritage_count"), "Heritage sites"),
        _stat(profile.get("annual_tourists"), "Tourists/yr"),
    ])

    # No image here — the full scenery photo renders on the next page's hero. This
    # keeps the picker a clean, compact info card and avoids a half-rendered thumbnail.
    st.markdown(
        f"""
        <div class="gj-prev">
            <div class="gj-prev-body">
                <div class="gj-prev-title">{flag(iso3)} {_html.escape(name)}
                    <span class="gj-prev-tag">{_html.escape(tagline)}</span></div>
                <div class="gj-prev-eyebrow">{_html.escape(region)}</div>
                <div class="gj-prev-pills">{pills}</div>
                <div class="gj-prev-stats">{stats}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, mid, right = st.columns([1, 1.4, 1])
    with mid:
        if st.button(f"Begin {name}'s story  →", type="primary",
                     key=f"gj_enter_{iso3}", use_container_width=True):
            _goto("country", selected_country=iso3)


# ---------------------------------------------------------------------------
# Stage: a country's story unfolds
# ---------------------------------------------------------------------------
def _country_hub() -> None:
    iso3 = st.session_state.get("selected_country")
    if not iso3:
        _goto("choose")
        return
    try:
        profile = repo.get_country_profile(iso3)
    except Exception:  # noqa: BLE001
        profile = None
    if not profile:
        st.warning("This country's story could not be loaded.")
        if st.button("← Choose another country"):
            _goto("choose")
        return

    name = profile.get("name", iso3)
    # Navigation is handled by the clickable header stepper; the bar just sets context.
    _bar(f"{flag(iso3)} {name}")

    _country_hero(iso3, name, profile)

    intro = _hub_narration(iso3, name, profile)
    st.markdown(f"<p class='gj-chapters-intro'>{_html.escape(intro)}</p>",
                unsafe_allow_html=True)
    # Featured countries have a pre-generated Polly narration; others fall back to voice.
    narrate(intro, label=f"Hear {name}'s story",
            audio_file=_audio_file(f"hub_{iso3}"), height=70)

    opened = _open_chapters(iso3)
    st.markdown("<div class='gj-eyebrow'>Uncover the chapters</div>", unsafe_allow_html=True)

    _, gallery = _country_media(iso3)

    # Chapter selection cards as a responsive row of buttons, each fronted by one of
    # the country's own dish photos so the grid is vivid rather than blank.
    cols = st.columns(len(CHAPTERS))
    for i, (col, (cid, emoji, title, teaser)) in enumerate(zip(cols, CHAPTERS)):
        done = cid in opened
        photo = gallery[i % len(gallery)] if gallery else None
        with col:
            if photo:
                overlay = ("linear-gradient(180deg, rgba(31,111,92,0.35) 0%, "
                           "rgba(13,46,31,0.88) 100%)" if done else
                           "linear-gradient(180deg, rgba(20,12,8,0.15) 0%, "
                           "rgba(20,12,8,0.85) 100%)")
                st.markdown(
                    f"<div class='gj-card photo {'done' if done else ''}' "
                    f"style=\"background-image:{overlay}, url('{photo}');\">"
                    f"{'<span class=gj-check>✓ read</span>' if done else ''}"
                    f"<div class='gj-emoji'>{emoji}</div>"
                    f"<div class='gj-title'>{title}</div>"
                    f"<div class='gj-teaser'>{_html.escape(teaser)}</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='gj-card {'done' if done else ''}'>"
                    f"{'<span class=gj-check>✓ read</span>' if done else ''}"
                    f"<div class='gj-emoji'>{emoji}</div>"
                    f"<div class='gj-title'>{title}</div>"
                    f"<div class='gj-teaser'>{_html.escape(teaser)}</div></div>",
                    unsafe_allow_html=True,
                )
            btn = "Re-read" if done else "Reveal"
            if st.button(btn, key=f"gj_open_{iso3}_{cid}", use_container_width=True):
                if cid in opened:
                    opened.remove(cid)
                else:
                    opened.append(cid)
                st.rerun()

    # Progress nudge.
    st.markdown(f"<div class='gj-progress'>You've uncovered {len(opened)} of "
                f"{len(CHAPTERS)} chapters</div>", unsafe_allow_html=True)

    # Render opened chapters in the order they were opened.
    for cid in opened:
        _render_chapter(cid, iso3, name, profile)

    # A prominent, always-visible invitation to zoom out — the natural next step, so
    # the Big Picture is easy to find without hunting for a small top-corner button.
    all_read = len(opened) >= len(CHAPTERS)
    headline = ("You've explored all of " + name + " — now see how it fits the whole world."
                if all_read else
                "Zoom out from " + name + " to how the whole world eats.")
    st.markdown(
        f"""
        <div class="gj-nextcta">
            <div class="gj-nextcta-emoji">🌍</div>
            <div class="gj-nextcta-text">
                <div class="gj-nextcta-title">The Big Picture</div>
                <div class="gj-nextcta-sub">{_html.escape(headline)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    l, m, r = st.columns([1, 1.6, 1])
    with m:
        if st.button("Explore the big picture  →", type="primary",
                     key="gj_cta_big", use_container_width=True):
            _goto("bigpicture")
        if st.button("🗺️  Or explore another country", key="gj_cta_another",
                     use_container_width=True):
            _goto("choose")


def _country_hero(iso3: str, name: str, profile: dict) -> None:
    from sections.country_story import _tagline

    region = profile.get("region") or ""
    tagline = _tagline(iso3, profile)
    # Prefer a scenery/heritage photo of the country (always on-context); fall back to
    # one of its dish photos, then to a warm gradient.
    dish_hero, _gallery = _country_media(iso3)
    hero_src = _scenery_src(iso3) or dish_hero

    inner = (
        f'<div class="gj-hero-inner">'
        f'<div class="gj-hero-eyebrow">{_html.escape(region)}</div>'
        f'<h1 class="gj-hero-title">{flag(iso3)} {_html.escape(name)}</h1>'
        f'<div class="gj-hero-tagline">&ldquo;{_html.escape(tagline)}&rdquo;</div></div>'
    )
    if hero_src:
        # Full-bleed cover banner — fills the screen edge-to-edge with no gaps.
        style = f"background-image:url('{hero_src}');"
        html = (f'<div class="gj-hero" style="{style}">'
                f'<div class="gj-hero-shade"></div>{inner}</div>')
    else:
        html = f'<div class="gj-hero gj-hero--grad">{inner}</div>'
    st.markdown(html, unsafe_allow_html=True)


def _render_chapter(cid: str, iso3: str, name: str, profile: dict) -> None:
    emoji, title = _CHAPTER_TITLES.get(cid, ("", cid.title()))
    st.session_state["selected_country"] = iso3  # chapters reuse this state
    with st.container(border=True):
        st.markdown(f"<div class='gj-chapter-head'>{emoji} {title}</div>",
                    unsafe_allow_html=True)
        narrate(_chapter_narration(cid, iso3, name, profile), label="Listen",
                audio_file=_audio_file(f"ch_{iso3}_{cid}"), height=66)
        try:
            if cid == "story":
                _ch_story(iso3, name, profile)
            elif cid == "plate":
                from sections import plate as plate_section
                plate_section.body()
            elif cid == "planet":
                _ch_planet(iso3, name)
            elif cid == "kindred":
                _ch_kindred(iso3, name)
            elif cid == "celebrations":
                _ch_celebrations(iso3, name, profile)
        except Exception as exc:  # noqa: BLE001
            st.info("This chapter couldn't be loaded right now.")
            st.caption(f"({type(exc).__name__})")


# ---- individual country chapters ------------------------------------------
def _ch_story(iso3: str, name: str, profile: dict) -> None:
    from sections import country_story as cs

    facts = cs._facts(profile, iso3)
    if facts:
        cards.insight_callout(facts[0])

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        cards.big_stat("🏛 Heritage sites", profile.get("unesco_heritage_count"), icon="")
    with d2:
        life = profile.get("life_expectancy")
        cards.big_stat("❤️ Life expectancy",
                       f"{float(life):.0f} yrs" if life is not None else None, icon="")
    with d3:
        nutri = profile.get("nutrition_score")
        cards.big_stat("🥗 Nutrition score",
                       f"{float(nutri):.0f}/100" if nutri is not None else None, icon="")
    with d4:
        tour = profile.get("annual_tourists")
        cards.big_stat("✈️ Visitors / yr",
                       f"{int(tour):,}" if tour is not None else None, icon="")

    try:
        culinary = repo.get_country_culinary(iso3)
        if culinary is not None and not culinary.empty:
            pills = " ".join(f'<span class="atw-pill">{r["element"]}</span>'
                             for _, r in culinary.iterrows())
            cards.card("UNESCO Food Traditions", pills, icon="🍲")
    except Exception:  # noqa: BLE001
        pass

    cs._taste_profile(iso3)


def _ch_planet(iso3: str, name: str) -> None:
    from data import footprint_data as fp
    from viz.footprint import build_plate_footprint

    df = fp.country_footprints()
    row = df[df["iso3"] == iso3]
    if row.empty:
        st.info(f"No plate-footprint data for {name} yet.")
        return
    r = row.iloc[0]
    c1, c2, c3 = st.columns(3)
    with c1:
        cards.big_stat("Carbon intensity", f"{r['co2']:.1f} kg CO₂e/kg", icon="🌍")
    with c2:
        cards.big_stat("Animal foods", f"{r['animal_share']:.0f}% of plate", icon="🥩")
    with c3:
        cards.big_stat("Planet score", f"{r['planet_score']:.0f}/100", icon="🌿")
    breakdown = fp.country_breakdown(iso3)
    if not breakdown.empty:
        fig, alt = build_plate_footprint(breakdown, name)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption(alt)
    st.caption("Footprints: Our World in Data (Poore & Nemecek, 2018); diet from FAOSTAT.")


def _ch_kindred(iso3: str, name: str) -> None:
    from sections import country_story as cs
    from sections import similarity as similarity_section

    cs._who_shares_my_plate(iso3, name)
    st.markdown("##### Compare with any country")
    similarity_section.body()


def _ch_celebrations(iso3: str, name: str, profile: dict) -> None:
    fests = profile.get("festivals") or []
    if fests:
        cards.list_card("Festivals", fests, icon="🎉")
    else:
        st.caption(f"No festival records for {name} yet.")
    try:
        culinary = repo.get_country_culinary(iso3)
        if culinary is not None and not culinary.empty:
            pills = " ".join(
                f'<span class="atw-pill">{r["element"]}'
                + (f' · {int(r["year"])}' if r["year"] and str(r["year"]).strip() else "")
                + "</span>"
                for _, r in culinary.iterrows()
            )
            cards.card("Living food heritage (UNESCO)", pills, icon="🍲")
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Stage: the big picture (global chapters)
# ---------------------------------------------------------------------------
_BIGPICTURE_TABS = [
    ("journeys", "🧭 Journeys"),
    ("dinner_party", "🍽️ Dinner Party"),
    ("sustainability", "🌱 Planet"),
    ("bigpicture", "❤️ Health & Taste"),
    ("taste_passport", "🛂 Passport"),
]


def _bigpicture() -> None:
    # Navigation is handled by the clickable header stepper.
    _bar("🌍 The Big Picture")

    st.markdown(
        "<p style='text-align:center;color:#2A2320;font-size:1.06rem;margin:2px 0 14px 0'>"
        "Step back from a single plate, and the world's food reveals patterns no one meal "
        "could — health, taste, and one shared table.</p>", unsafe_allow_html=True)

    # Tabs, not a long scroll — jump straight to any chapter of the big picture.
    import importlib
    tabs = st.tabs([label for _, label in _BIGPICTURE_TABS])
    for tab, (section, _label) in zip(tabs, _BIGPICTURE_TABS):
        with tab:
            try:
                module = importlib.import_module(f"sections.{section}")
                module.render()
            except Exception as exc:  # noqa: BLE001
                st.info(f"This chapter couldn't be loaded right now. ({type(exc).__name__})")


# ---------------------------------------------------------------------------
# Narration text builders (data-derived, graceful fallback)
# ---------------------------------------------------------------------------
def _top_group(iso3: str) -> str | None:
    try:
        groups = repo.get_food_groups(iso3)
        if not groups.empty:
            return str(groups.sort_values("pct", ascending=False).iloc[0]["food_group"]).lower()
    except Exception:  # noqa: BLE001
        pass
    return None


# Hand-written, genuinely distinct openings for the well-known cuisines.
_FEATURED_STORIES: dict[str, str] = {
    "IND": ("Somewhere in India, before the sun is fully up, a pan of oil is already "
            "blooming with cumin and mustard seed. This is a land of a thousand kitchens, "
            "where the same spice box tells a different story in every home — a meal can be "
            "fire, comfort, and prayer, all at once. Come; the chai is almost ready."),
    "ITA": ("In Italy, the whole day is measured in meals. Somewhere a grandmother is "
            "rolling pasta by hand, the way she was taught, while a pot of sauce whispers on "
            "the stove. Here, simplicity is the highest art: a few good things, treated with "
            "love. Pull up a chair — lunch is sacred."),
    "JPN": ("In Japan, a bowl of rice is set down with quiet care. This is the home of "
            "umami, that deep, savory fifth taste, where a single perfect ingredient matters "
            "more than a crowded plate, and the sea is never far from the table. Sit, and let "
            "the meal unfold, course by delicate course."),
    "MEX": ("In Mexico, the morning smells of corn — masa pressed and warmed on the griddle, "
            "just as it has been for three thousand years. This is the birthplace of "
            "chocolate and chili, of feasts loud with color and family. Come hungry; there is "
            "always room for one more."),
    "FRA": ("In France, the table is a kind of theatre. Somewhere a baker pulls warm bread "
            "from the oven while cheese softens and wine begins to breathe. Here, eating "
            "slowly is not indulgence but wisdom. Sit down — we are in no hurry at all."),
    "ESP": ("In Spain, dinner waits for the stars. Small plates arrive one after another, "
            "hands reach across the table, and no one ever eats alone. This is the land of "
            "paella and long, laughing nights. Come late — and stay later."),
    "CHN": ("In China, the wok roars to life and centuries answer. From dumplings folded "
            "like little promises to broths simmered all day long, this is a table as vast as "
            "the country itself, where balance and abundance sit side by side. Take your "
            "chopsticks; the feast is meant to be shared."),
    "THA": ("In Thailand, a single bite can be sweet, sour, salty, and fiery all at once. "
            "Somewhere a street cart sizzles, lime and chili sharp in the air, the whole "
            "cuisine balanced on a knife's edge of flavor. Pull up a plastic stool — the best "
            "food here never had a menu."),
    "MAR": ("In Morocco, a tagine has been simmering since morning, sweet with apricot and "
            "warm with cumin. This is where the spice routes once met, East and West folded "
            "into one fragrant pot. Come; the tea is poured from high above the glass, and no "
            "guest ever leaves hungry."),
    "BRA": ("In Brazil, the day begins with strong coffee and ends with something worth "
            "dancing to. From slow-cooked feijoada to the drums of Carnival, this is a table "
            "as warm and generous as the country itself. Sit — the pot is always big enough."),
    "KOR": ("In Korea, the meal arrives all at once: a dozen little dishes crowded around a "
            "bowl of rice, and kimchi that has been fermenting quietly for months. This is "
            "food built on patience and sharing. Pull up close — every dish belongs to the "
            "whole table."),
    "ETH": ("In Ethiopia, coffee is not a drink but a ceremony — beans roasted and poured "
            "while the room fills with smoke and conversation. Here, a shared platter of "
            "injera erases the line between your plate and mine. Come, tear a piece of bread; "
            "we eat with our hands, together."),
    "GRC": ("In Greece, lunch spills onto a sunlit terrace, olive oil glistening and the sea "
            "somewhere close. This is a table of simple, ancient things: bread, olives, fish, "
            "and time. Sit — here, a long, slow meal is a life well lived."),
    "VNM": ("In Vietnam, breakfast is a steaming bowl of pho on a busy corner, fresh herbs "
            "torn over the top. This is the street-food capital of the world, where the "
            "finest cooking happens on a low stool by the roadside. Lean in — the broth has "
            "been simmering since before dawn."),
    "TUR": ("In Turkey, the table bridges two continents. Somewhere a mezze spread unfurls — "
            "a dozen small dishes, warm bread, and tea in tulip glasses that never runs dry. "
            "Here, hospitality is a sacred duty. Sit down; you are family now."),
    "PER": ("In Peru, the humble potato is a national treasure — thousands of varieties, "
            "born high in the Andes. From ceviche bright with lime to feasts cooked in the "
            "earth itself, this is a cuisine of astonishing range. Come; here the Pacific and "
            "the mountains meet on a single plate."),
}

# Region-specific sensory imagery for the generated (non-featured) stories.
_REGION_IMAGE = {
    "Africa": ["the air is warm with woodsmoke and a stew that has cooked all day",
               "a pot bubbles over an open flame, and neighbors drift toward the smell"],
    "Americas": ["a table is being laid for far more people than were invited",
                 "something slow-cooked and generous is lifted from the fire"],
    "Asia": ["rice is steaming and spices are toasting in a hot, bright pan",
             "a broth simmers while hands work quickly over a sizzling wok"],
    "Europe": ["bread is baking and a pot murmurs quietly on the stove",
               "the market's morning haul is being turned into the day's meal"],
    "Oceania": ["the ocean breeze carries the smell of the fresh catch to the table",
                "fire and fresh fish meet the way they have for generations"],
}
_CLOSERS = [
    "Pull up a chair — this is where the story begins.",
    "Come closer; every dish here has something to tell.",
    "Sit, and let its food do the talking.",
    "Stay a while — the table has stories to share.",
]


def _generic_narration(iso3: str, name: str, profile: dict) -> str:
    """A varied, region-flavored opening for countries without a hand-written one."""
    seed = sum(ord(c) for c in iso3)
    region = profile.get("region") or ""
    images = _REGION_IMAGE.get(region, ["a kitchen is just coming to life"])
    image = images[seed % len(images)]

    dishes = profile.get("dishes") or []
    dish = dishes[0] if dishes else None
    staples = profile.get("staple_foods") or []
    top = _top_group(iso3)

    # Opening: vary the sentence shape by country.
    openers = [
        f"Arrive in {name} just as a meal begins, and {image}.",
        f"In {name}, {image}.",
        f"Somewhere in {name}, {image}.",
    ]
    parts = [openers[seed % len(openers)]]

    # A food-culture line — lead with a real dish, a staple, or the dominant group,
    # and phrase it differently for different countries.
    if dish:
        dish_lines = [
            f" The kitchens here are proud of {dish} — a taste that simply means home.",
            f" Ask anyone what to eat, and they will point you first to {dish}.",
            f" {dish} is the dish that gathers this family to the table.",
        ]
        parts.append(dish_lines[seed % len(dish_lines)])
    elif staples:
        parts.append(f" The everyday plate leans on {staples[0].lower()} and what the land "
                     "gives freely.")
    elif top:
        parts.append(f" The everyday plate is built, above all, on {top}.")

    # An optional second texture: a food tradition or a staple pairing.
    used_staple = dish is None and bool(staples)  # a staple was already named above
    try:
        culinary = repo.get_country_culinary(iso3)
        elem = (culinary.iloc[0]["element"]
                if culinary is not None and not culinary.empty else None)
    except Exception:  # noqa: BLE001
        elem = None
    # Only weave in a UNESCO tradition when its name is short enough to read as story.
    if elem and len(str(elem)) <= 42:
        parts.append(f" Its food traditions run so deep the world has named {elem} a "
                     "living heritage.")
    elif not used_staple and len(staples) >= 2:
        parts.append(f" Around it gather {staples[0].lower()}, {staples[1].lower()}, and "
                     "the flavors passed down through generations.")

    parts.append(" " + _CLOSERS[seed % len(_CLOSERS)])
    return "".join(parts)


def _hub_narration(iso3: str, name: str, profile: dict) -> str:
    """A warm, cinematic invitation — bespoke for known cuisines, varied for the rest."""
    if iso3 in _FEATURED_STORIES:
        return _FEATURED_STORIES[iso3]
    return _generic_narration(iso3, name, profile)


def _chapter_narration(cid: str, iso3: str, name: str, profile: dict) -> str:
    """Each chapter as a spoken story beat, not a statistic read aloud."""
    try:
        if cid == "story":
            h = profile.get("unesco_heritage_count")
            line = (f"To really know {name}, you have to start at its table. ")
            if h:
                line += (f"This is a land that has guarded {int(h)} places the world calls "
                         "treasures, and its food carries that same long memory — ")
            else:
                line += "Its food carries a long memory — "
            line += "every dish a small inheritance, passed hand to hand, meal after meal."
            return line

        if cid == "plate":
            top = _top_group(iso3)
            if top:
                return (f"Lift the lid on an ordinary day in {name}. The plate leans, as it "
                        f"always has, on {top} — and around that centre gathers everything "
                        "that makes a meal taste like home.")
            return (f"Lift the lid on an ordinary day in {name}, and see the quiet balance "
                    "of a meal built over generations.")

        if cid == "planet":
            from data import footprint_data as fp
            df = fp.country_footprints()
            row = df[df["iso3"] == iso3]
            if not row.empty:
                co2 = float(row.iloc[0]["co2"])
                weight = ("a remarkably gentle footprint" if co2 < 3.5
                          else "a fairly light footprint" if co2 < 5
                          else "a heavier footprint" if co2 < 6.5
                          else "one of the heaviest footprints on Earth")
                return (f"Every meal leaves a mark you cannot see. The everyday plate in "
                        f"{name} leaves {weight} on the planet. The way a country chooses to "
                        "eat is, in the end, a quiet promise it makes to the Earth.")
            return (f"Every meal leaves a mark you cannot see — and {name}'s plate is part "
                    "of that story too.")

        if cid == "kindred":
            sim = repo.most_similar(iso3, 1)
            if sim is not None and not sim.empty:
                r = sim.iloc[0]
                return (f"Food has never really believed in borders. Thousands of miles from "
                        f"{name}, someone is stirring a pot that would taste like home — "
                        f"{r['name']} shares almost the very same plate. Distant kitchens, "
                        "one shared language of flavor.")
            return (f"Food has never really believed in borders — somewhere out there, a "
                    f"kitchen cooks just like {name}'s.")

        if cid == "celebrations":
            fests = profile.get("festivals") or []
            if fests:
                return (f"And when the calendar turns to celebration, the table becomes the "
                        f"beating heart of it all. In {name}, days like {fests[0]} are "
                        "measured not in hours, but in the dishes shared around them.")
            return (f"And when {name} celebrates, the table becomes the heart of it all — "
                    "joy measured in the dishes shared around it.")
    except Exception:  # noqa: BLE001
        pass
    return f"The story of {name} continues."


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
_PROGRESS_STEPS = [
    ("prologue", "Welcome"),
    ("choose", "Choose"),
    ("country", "The Story"),
    ("bigpicture", "Big Picture"),
]


def _header(stage: str) -> None:
    """A persistent brand bar + a clickable journey stepper (jump between stages)."""
    order = [s for s, _ in _PROGRESS_STEPS]
    cur = order.index(stage) if stage in order else 0
    have_country = bool(st.session_state.get("selected_country"))
    icons = {"prologue": "🏠", "choose": "🗺️", "country": "📖", "bigpicture": "🌍"}

    st.markdown(
        """
        <style>
        .gjnav-brand { display:flex; align-items:center; gap:8px; padding-top:8px;
            font-family:'Playfair Display',Georgia,serif; font-weight:800;
            font-size:1.15rem; color:#2A2320; white-space:nowrap; }
        .gjnav-brand b { background:linear-gradient(90deg,#F2A93B,#E8A317);
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
        .gjnav-badge { text-align:right; padding-top:12px; }
        .gjnav-badge span { padding:4px 12px; border-radius:999px;
            background:linear-gradient(135deg,rgba(232,163,23,0.20),rgba(192,57,43,0.20));
            border:1px solid rgba(232,163,23,0.4); font-family:'Inter',sans-serif;
            font-size:0.66rem; font-weight:700; color:#B26B12; letter-spacing:0.06em;
            text-transform:uppercase; white-space:nowrap; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns([1.7, 1, 1, 1, 1.2, 1.0])
    with cols[0]:
        st.markdown("<div class='gjnav-brand'>🌍&nbsp;<span><b>80</b> Plates</span></div>",
                    unsafe_allow_html=True)
    for i, (stg, label) in enumerate(_PROGRESS_STEPS):
        with cols[i + 1]:
            active = (i == cur)
            done = (i < cur)
            disabled = (stg == "country" and not have_country)
            prefix = "✓ " if done and not active else f"{icons.get(stg, '')} "
            if st.button(prefix + label, key=f"gjnav_{stg}",
                         type="primary" if active else "secondary",
                         use_container_width=True, disabled=disabled):
                if not active:
                    _goto(stg)
    with cols[5]:
        st.markdown("<div class='gjnav-badge'><span>VizCon 2026</span></div>",
                    unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)


def render() -> None:
    _inject_css()
    stage = st.session_state.get("journey_stage", "prologue")

    _header(stage)
    if stage == "choose":
        _choose()
    elif stage == "country":
        _country_hub()
    elif stage == "bigpicture":
        _bigpicture()
    else:
        _prologue()
