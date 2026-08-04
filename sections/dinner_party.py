"""Dinner_Party — the 'Global Dinner Party' wow feature (Req 15, 17.2)."""
from __future__ import annotations

import streamlit as st

from components import cards, citation, lottie
from components.narrative import insight
from data import repository as repo

COURSE_ICON = {"starter": "🥣", "main": "🍛", "dessert": "🍰", "drink": "🥤"}


def _new_dinner(celebrate: bool = False) -> None:
    prev = st.session_state.get("dinner_prev_set", [])
    dinner = repo.assemble_dinner(exclude=prev)
    st.session_state["dinner"] = dinner
    if not dinner.get("error"):
        st.session_state["dinner_prev_set"] = dinner["countries"]
        if celebrate:
            st.balloons()


def render() -> None:
    cards.page_header("dinner_party")
    lottie.show("dinner", height=140)  # auto-appears when assets/lottie/dinner.json exists

    if "dinner" not in st.session_state:
        try:
            _new_dinner()
        except Exception:  # noqa: BLE001
            st.warning("The dinner table could not be set right now.")
            return

    label = "Set a new table  🎲" if st.session_state.get("dinner") else "Assemble the dinner"
    if st.button(label, type="primary"):
        _new_dinner(celebrate=True)
        st.rerun()

    dinner = st.session_state.get("dinner", {})

    # Fewer than five countries -> message, no table (Req 15.6).
    if dinner.get("error") == "fewer_than_five":
        st.info("There aren't enough countries with dishes to assemble a global dinner yet.")
        return


    # The five courses, each from a distinct country (Req 15.2).
    from components.flags import flag
    from components.images import get_food_image

    courses = dinner.get("courses", [])

    if courses:
        # CSS to constrain all dinner images to same height
        st.markdown("""
        <style>
        [data-testid="stImage"] img {
            height: 200px !important;
            object-fit: cover !important;
            border-radius: 12px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        # Render course cards using st.columns + st.image for reliable image display
        cols = st.columns(len(courses))
        for i, c in enumerate(courses):
            with cols[i]:
                icon = COURSE_ICON.get(c["course"], "🍽️")
                img = get_food_image(c["dish"])
                
                st.markdown(
                    f'<div style="text-align:center;font-size:0.72rem;text-transform:uppercase;'
                    f'letter-spacing:0.06em;color:#9A8C7A;font-weight:700;margin-bottom:4px;">'
                    f'{icon} {c["course"]}</div>',
                    unsafe_allow_html=True,
                )
                
                if img:
                    st.image(img[0], use_container_width=True)
                else:
                    st.markdown(
                        f'<div style="width:100%;height:120px;background:linear-gradient(135deg,#F4EADB,#FFF8F1);'
                        f'border-radius:12px;display:flex;align-items:center;justify-content:center;'
                        f'font-size:2.5rem;">{icon}</div>',
                        unsafe_allow_html=True,
                    )
                


    # Per-dish symbolism (Req 15.3) — interactive cards in a grid.

    # Build the complete HTML with inline styles (avoids CSS scoping issues)
    cards_html = ""
    for c in courses:
        icon = COURSE_ICON.get(c["course"], "🍽️")
        sym = c.get("symbolism") or "A dish with a story waiting to be told."
        ingredients = c.get("connecting_ingredients") or []
        routes = c.get("trade_routes") or []
        values = c.get("cultural_values") or []

        tags_html = ""
        for ing in ingredients[:3]:
            tags_html += (f'<span style="display:inline-block;background:#E8F5F0;'
                         f'border:1px solid #B8E0D4;border-radius:999px;padding:3px 10px;'
                         f'font-size:0.72rem;color:#1F6F5C;font-weight:500;margin:3px 4px 3px 0;">'
                         f'🌿 {ing}</span>')
        for rt in routes[:2]:
            tags_html += (f'<span style="display:inline-block;background:#EBF0FA;'
                         f'border:1px solid #B8C8E0;border-radius:999px;padding:3px 10px;'
                         f'font-size:0.72rem;color:#1F6F5C;font-weight:500;margin:3px 4px 3px 0;">'
                         f'🚢 {rt}</span>')
        for val in values[:2]:
            tags_html += (f'<span style="display:inline-block;background:#FFF0E0;'
                         f'border:1px solid #F5D6A8;border-radius:999px;padding:3px 10px;'
                         f'font-size:0.72rem;color:#C0392B;font-weight:500;margin:3px 4px 3px 0;">'
                         f'✦ {val}</span>')

        cards_html += (
            f'<div style="background:#FFFFFF;border:1px solid #EFE6D8;border-radius:18px;'
            f'padding:20px;overflow:hidden;box-shadow:0 4px 16px rgba(43,33,24,0.07);'
            f'transition:all 0.25s ease;border-top:4px solid #E8A317;">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<span style="font-size:1.8rem;flex-shrink:0;">{icon}</span>'
            f'<div>'
            f'<div style="font-family:Playfair Display,Georgia,serif;font-weight:800;'
            f'font-size:1.05rem;color:#2A2320;">{c["dish"]}</div>'
            f'<div style="font-size:0.78rem;color:#574B42;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.04em;">'
            f'{flag(c["iso3"])} {c["country"]}</div>'
            f'</div></div>'
            f'<div style="font-size:0.9rem;color:#4A3F35;line-height:1.5;margin:8px 0;'
            f'padding:10px 12px;background:#FFFBF5;border-radius:10px;'
            f'border-left:3px solid #E8A317;">{sym}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:10px;">'
            f'{tags_html}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));'
        f'gap:16px;margin:14px 0;">{cards_html}</div>',
        unsafe_allow_html=True,
    )

