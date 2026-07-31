"""Around the World in 80 Plates — Single-page storytelling flow.

A continuous scrolling journey through world food cultures. No sidebar navigation —
the story flows top to bottom like a visual essay, with a sticky top nav for jumping
between chapters.
"""
from __future__ import annotations

import importlib

import streamlit as st

import config
from components import cards
from components.navigation import label_for
from components.theme import inject_theme


# Sections to render in the single-page flow (in narrative order).
_FLOW_SECTIONS = [
    "home",
    "explore_map",
    "journeys",
    "country_story",
    "traditions",
    "travel",
    "bigpicture",
    "taste_passport",
    "dinner_party",
]


def _init_state() -> None:
    defaults = {
        "active_section": "home",
        "selected_country": None,
        "compare_country": None,
        "dinner_prev_set": [],
        "taste_prefs": set(),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _inject_single_page_css() -> None:
    """Hide the sidebar entirely and add a premium sticky chapter navigation bar."""
    st.markdown(
        """
        <style>
        /* Hide sidebar completely */
        section[data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        button[kind="header"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }

        /* Give content full width */
        .block-container { max-width: 1400px !important; padding-top: 64px !important; padding-bottom: 48px !important; }

        /* Reduce Streamlit's default element spacing */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
            gap: 1rem !important;
        }
        [data-testid="stVerticalBlock"] {
            gap: 1rem !important;
        }
        

        /* Section dividers */
        .atw-section-divider {
            position: relative;
            margin: 64px 0 32px 0;
            text-align: center;
        }
        .atw-section-divider::before {
            content: "";
            position: absolute;
            top: 50%;
            left: 5%;
            right: 5%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(232,163,23,0.5), transparent);
        }
        .atw-section-divider .emoji {
            position: relative;
            background: #FFF8F1;
            padding: 0 24px;
            font-size: 2.2rem;
            filter: drop-shadow(0 2px 6px rgba(232,163,23,0.3));
        }

        /* ---- Premium sticky top nav ---- */
        .atw-topbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 9999;
            background: linear-gradient(180deg, rgba(46,28,21,0.97) 0%, rgba(46,28,21,0.94) 100%);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 4px 24px rgba(0,0,0,0.25);
            padding: 0;
        }
        .atw-topbar::before {
            content: ""; position: absolute; inset: 0; pointer-events: none; opacity: 0.04;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='56' viewBox='0 0 100 56'%3E%3Cpath d='M0 28 Q25 18 50 28 T100 28' fill='none' stroke='white' stroke-width='0.5'/%3E%3Ccircle cx='25' cy='14' r='2' fill='none' stroke='%23E8A317' stroke-width='0.5'/%3E%3Ccircle cx='75' cy='42' r='2' fill='none' stroke='%23E8A317' stroke-width='0.5'/%3E%3Cpath d='M48 10l2-4 2 4M47 10c-1 1-1 3 1 3M53 10c1 1 1 3-1 3' fill='none' stroke='white' stroke-width='0.4'/%3E%3C/svg%3E");
            background-size: 100px 56px;
        }
        .atw-topbar-inner {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            padding: 0 24px;
            height: 56px;
            gap: 0;
        }
        .atw-topbar-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
            margin-right: 24px;
        }
        .atw-topbar-brand .logo {
            font-size: 1.4rem;
            line-height: 1;
        }
        .atw-topbar-brand .title {
            font-family: 'Playfair Display', Georgia, serif;
            font-weight: 800;
            font-size: 1.05rem;
            color: #FFF8F1;
            letter-spacing: -0.3px;
            white-space: nowrap;
        }
        .atw-topbar-brand .title span {
            background: linear-gradient(90deg, #F2A93B, #E8A317);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* Nav links */
        .atw-topbar-nav {
            display: flex;
            align-items: center;
            gap: 4px;
            overflow-x: auto;
            scrollbar-width: none;
            -ms-overflow-style: none;
            flex: 1;
        }
        .atw-topbar-nav::-webkit-scrollbar { display: none; }
        .atw-topbar-nav a {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 8px 14px;
            border-radius: 10px;
            font-family: 'Inter', system-ui, sans-serif;
            font-size: 0.8rem;
            font-weight: 600;
            color: rgba(241,228,212,0.8);
            text-decoration: none;
            white-space: nowrap;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }
        .atw-topbar-nav a:hover {
            color: #FFFFFF;
            background: rgba(232,163,23,0.18);
            border-color: rgba(232,163,23,0.4);
            transform: translateY(-1px);
        }
        .atw-topbar-nav a .nav-emoji {
            font-size: 1rem;
        }

        /* Search shortcut in top bar — matches nav link style */
        .atw-topbar-search {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 8px 14px;
            border-radius: 10px;
            font-family: 'Inter', system-ui, sans-serif;
            font-size: 0.8rem;
            font-weight: 600;
            color: rgba(241,228,212,0.8);
            text-decoration: none;
            white-space: nowrap;
            transition: all 0.2s ease;
            border: 1px solid rgba(232,163,23,0.3);
            margin-left: 4px;
            flex-shrink: 0;
        }
        .atw-topbar-search:hover {
            color: #FFFFFF;
            background: rgba(232,163,23,0.18);
            border-color: rgba(232,163,23,0.5);
            transform: translateY(-1px);
        }
        /* VizCon badge */
        .atw-topbar-badge {
            flex-shrink: 0;
            margin-left: 16px;
            padding: 4px 12px;
            border-radius: 999px;
            background: linear-gradient(135deg, rgba(232,163,23,0.2), rgba(192,57,43,0.2));
            border: 1px solid rgba(232,163,23,0.4);
            font-family: 'Inter', system-ui, sans-serif;
            font-size: 0.68rem;
            font-weight: 700;
            color: #E8A317;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            white-space: nowrap;
        }

        /* Scroll-to anchors offset for sticky nav */
        .atw-anchor {
            display: block;
            position: relative;
            top: -70px;
            visibility: hidden;
            height: 0;
        }

        /* ---- Scroll-triggered storytelling animations ---- */
        .atw-story-section {
            opacity: 1;
            transform: translateY(0);
        }

        /* Cards and elements are always visible */

        /* Progress indicator on side */
        .atw-progress {
            position: fixed;
            right: 16px;
            top: 50%;
            transform: translateY(-50%);
            z-index: 100;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .atw-progress-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: rgba(192,57,43,0.2);
            border: 1px solid rgba(192,57,43,0.3);
            transition: all 0.3s ease;
        }
        .atw-progress-dot.active {
            background: #C0392B;
            transform: scale(1.4);
            box-shadow: 0 0 8px rgba(192,57,43,0.4);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_chapter_nav() -> None:
    """A premium fixed top bar with brand + chapter links."""
    _CHAPTER_EMOJI = {
        "home": "🏠", "explore_map": "🗺️", "journeys": "🧭",
        "country_story": "📖", "traditions": "🎎", "travel": "✈️",
        "bigpicture": "📊", "taste_passport": "🛂", "dinner_party": "🍽️",
    }
    # Short labels for the nav bar (fit without overflow)
    _NAV_LABELS = {
        "home": "Home",
        "explore_map": "Explore",
        "journeys": "Journeys",
        "country_story": "Stories",
        "traditions": "Traditions",
        "travel": "Travel",
        "bigpicture": "Health",
        "taste_passport": "Passport",
        "dinner_party": "Dinner Party",
    }
    links = []
    for section in _FLOW_SECTIONS:
        emoji = _CHAPTER_EMOJI.get(section, "")
        label = _NAV_LABELS.get(section, label_for(section))
        links.append(
            f'<a href="#{section}"><span class="nav-emoji">{emoji}</span>{label}</a>'
        )
    st.markdown(
        f"""
        <div class="atw-topbar">
            <div class="atw-topbar-inner">
                <div class="atw-topbar-brand">
                    <span class="logo">🌍</span>
                    <span class="title"><span>80</span> Plates</span>
                </div>
                <div class="atw-topbar-nav">
                    {"".join(links)}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section_divider(section: str) -> None:
    """A visual divider between sections with a food-culture vector flourish."""
    _DIVIDER_EMOJI = {
        "explore_map": "🌍", "journeys": "🧭", "country_story": "📖",
        "traditions": "🎎", "travel": "✈️", "bigpicture": "📊",
        "taste_passport": "🛂", "dinner_party": "🍽️",
    }
    emoji = _DIVIDER_EMOJI.get(section, "✦")
    # Inline SVG vine/spice decoration for the divider line
    st.markdown(
        f"""
        <span class="atw-anchor" id="{section}"></span>
        <div style="position:relative;margin:56px 0 28px 0;text-align:center;">
            <svg width="100%" height="24" viewBox="0 0 800 24" preserveAspectRatio="none"
                style="position:absolute;top:50%;left:0;transform:translateY(-50%);opacity:0.3;">
                <path d="M0 12 Q100 2 200 12 T400 12 T600 12 T800 12"
                    fill="none" stroke="#E8A317" stroke-width="1"/>
                <circle cx="200" cy="12" r="2.5" fill="#C0392B" opacity="0.6"/>
                <circle cx="400" cy="12" r="2" fill="#1F6F5C" opacity="0.6"/>
                <circle cx="600" cy="12" r="2.5" fill="#C0392B" opacity="0.6"/>
                <path d="M385 6 Q390 2 395 6 M392 6v6" fill="none" stroke="#1F6F5C"
                    stroke-width="0.8" opacity="0.5"/>
                <path d="M405 6 Q410 2 415 6 M410 6v6" fill="none" stroke="#1F6F5C"
                    stroke-width="0.8" opacity="0.5"/>
            </svg>
            <span style="position:relative;background:#FFF8F1;padding:0 24px;
                font-size:2.2rem;filter:drop-shadow(0 2px 6px rgba(232,163,23,0.3));">
                {emoji}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_section_safe(section: str) -> None:
    """Render a section, catching errors gracefully."""
    try:
        module = importlib.import_module(f"sections.{section}")
    except ModuleNotFoundError:
        module = None

    if module is not None and hasattr(module, "render"):
        module.render()
    else:
        st.header(label_for(section))
        cards.render_narrative(section)
        st.info("This section is coming soon.")


def main() -> None:
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _init_state()
    inject_theme()
    _inject_single_page_css()

    # Sticky chapter navigation
    _render_chapter_nav()

    # Render all sections sequentially as one continuous story
    for i, section in enumerate(_FLOW_SECTIONS):
        if i == 0:
            # Home section — no divider, starts immediately
            st.markdown(f'<span class="atw-anchor" id="{section}"></span>'
                        f'<div class="atw-story-section visible" data-section="{section}">',
                        unsafe_allow_html=True)
        else:
            _section_divider(section)
            st.markdown(f'<div class="atw-story-section" data-section="{section}">',
                        unsafe_allow_html=True)

        try:
            _render_section_safe(section)
        except Exception as exc:  # noqa: BLE001
            st.error(
                f"We couldn't load '{label_for(section)}' right now. "
                "The data store may be unavailable."
            )
            st.caption(f"Details: {type(exc).__name__}")

        st.markdown('</div>', unsafe_allow_html=True)

    # Footer — includes condensed sources & AI credits
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center;margin:12px 0 16px 0;">
            <div style="font-family:'Playfair Display',Georgia,serif; font-size:1.5rem;
                font-weight:800; color:#2A2320;">🌍 Around the World in 80 Plates</div>
            <div style="color:#574B42; font-size:0.9rem; margin-top:6px;font-style:italic;">
                Every meal tells a story. Every tradition leaves a footprint.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    fc1, fc2 = st.columns(2)
    with fc1:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #EFE6D8;border-radius:14px;
                padding:18px 20px;box-shadow:0 3px 12px rgba(43,33,24,0.06);">
                <div style="font-family:'Inter',sans-serif;font-weight:700;font-size:0.72rem;
                    text-transform:uppercase;letter-spacing:0.08em;color:#C0392B;
                    margin-bottom:10px;">📚 Data Sources</div>
                <div style="font-size:0.8rem;color:#574B42;line-height:2;">
                    <a href="https://www.fao.org/faostat/en/#data" target="_blank"
                        style="color:#574B42;text-decoration:none;border-bottom:1px dotted #9A8C7A;">
                        FAOSTAT Food Balance Sheets</a><br>
                    <a href="https://data.worldbank.org/indicator/ST.INT.ARVL" target="_blank"
                        style="color:#574B42;text-decoration:none;border-bottom:1px dotted #9A8C7A;">
                        World Bank Tourism Data</a><br>
                    <a href="https://ich.unesco.org/en/lists" target="_blank"
                        style="color:#574B42;text-decoration:none;border-bottom:1px dotted #9A8C7A;">
                        UNESCO Intangible Cultural Heritage</a><br>
                    <a href="https://www.kaggle.com/c/whats-cooking/data" target="_blank"
                        style="color:#574B42;text-decoration:none;border-bottom:1px dotted #9A8C7A;">
                        Kaggle What's Cooking</a><br>
                    <a href="https://www.kaggle.com/datasets/unsdsn/world-happiness" target="_blank"
                        style="color:#574B42;text-decoration:none;border-bottom:1px dotted #9A8C7A;">
                        World Happiness Report</a><br>
                    <span style="color:#9A8C7A;font-style:italic;">+ curated migration, spice &amp; festival data</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with fc2:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #EFE6D8;border-radius:14px;
                padding:18px 20px;box-shadow:0 3px 12px rgba(43,33,24,0.06);">
                <div style="font-family:'Inter',sans-serif;font-weight:700;font-size:0.72rem;
                    text-transform:uppercase;letter-spacing:0.08em;color:#1F6F5C;
                    margin-bottom:10px;">🤖 Built with AI</div>
                <div style="font-size:0.8rem;color:#574B42;line-height:2;">
                    🧹 Data cleaning &amp; ISO reconciliation<br>
                    📊 Plotly visualization code generation<br>
                    🧮 Similarity scoring &amp; clustering<br>
                    ✍️ Narrative copy &amp; insight generation<br>
                    <span style="color:#9A8C7A;font-style:italic;">All numbers trace to cited sources above</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div style="text-align:center;margin-top:20px;padding-top:14px;
            border-top:1px solid rgba(232,163,23,0.25);">
            <div style="color:#9A8C7A; font-size:0.72rem;">
                VizCon 2026 · Culture Through Food &amp; Traditions · All data open-licensed
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Scroll-reveal observer + side progress dots
    st.html(
        """
        <style>body{margin:0;padding:0;overflow:hidden;height:0;}</style>
        <script>
        (function() {
            // Wait for Streamlit to finish rendering
            setTimeout(function() {
                const doc = window.parent.document;
                const sections = doc.querySelectorAll('.atw-story-section');

                // IntersectionObserver to reveal sections on scroll
                const observer = new IntersectionObserver(function(entries) {
                    entries.forEach(function(entry) {
                        if (entry.isIntersecting) {
                            entry.target.classList.add('visible');
                        }
                    });
                }, { threshold: 0.08, rootMargin: '0px 0px -60px 0px' });

                sections.forEach(function(s) { observer.observe(s); });

                // Add progress dots on the right side
                let progressDiv = doc.querySelector('.atw-progress');
                if (!progressDiv) {
                    progressDiv = doc.createElement('div');
                    progressDiv.className = 'atw-progress';
                    for (let i = 0; i < sections.length; i++) {
                        const dot = doc.createElement('div');
                        dot.className = 'atw-progress-dot';
                        dot.title = sections[i].getAttribute('data-section') || '';
                        dot.onclick = function() {
                            const anchor = doc.getElementById(dot.title);
                            if (anchor) anchor.scrollIntoView({behavior:'smooth'});
                        };
                        dot.style.cursor = 'pointer';
                        progressDiv.appendChild(dot);
                    }
                    doc.body.appendChild(progressDiv);
                }

                // Update active dot on scroll
                const progressObserver = new IntersectionObserver(function(entries) {
                    entries.forEach(function(entry) {
                        if (entry.isIntersecting) {
                            const idx = Array.from(sections).indexOf(entry.target);
                            const dots = doc.querySelectorAll('.atw-progress-dot');
                            dots.forEach(function(d, i) {
                                d.classList.toggle('active', i === idx);
                            });
                        }
                    });
                }, { threshold: 0.3 });

                sections.forEach(function(s) { progressObserver.observe(s); });
            }, 1500);
        })();
        </script>
        """,
    )


if __name__ == "__main__":
    main()
