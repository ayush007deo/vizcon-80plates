"""Journey navigation with active-section indication (Req 1.1, 1.2, 1.3, 17.1)."""
from __future__ import annotations

import config

# Human-readable labels in journey order (Req 17.1).
SECTION_LABELS: dict[str, str] = {
    "home": "Home",
    "explore_map": "Explore the World",
    "country_story": "A Country's Story",
    "journeys": "How Food Traveled",
    "traditions": "Traditions & Heritage",
    "travel": "Travel & Tourism",
    "bigpicture": "Food, Health & Flavor",
    "sustainability": "The Planet on Your Plate",
    "taste_passport": "Your Taste Passport",
    "dinner_party": "The Global Dinner Party",
    "sources": "Sources & Credits",
    # Sub-views (rendered inside chapters; kept for labels/citations):
    "plate": "What's on the Plate?",
    "similarity": "How Similar Is Your Plate?",
    "migration": "Food Migration",
    "spice_journey": "Journey of a Spice",
    "festivals": "Festivals Around the Table",
    "heritage": "Cultural Heritage",
    "health": "Can Food Predict Health?",
    "flavor_wheel": "The World's Flavor Wheel",
    "insights": "Global Insights",
    "dish_search": "Dish Search",
}


def label_for(section: str) -> str:
    return SECTION_LABELS.get(section, section.replace("_", " ").title())


def go_to(section: str) -> None:
    """Set the active section state. In single-page mode this just updates state
    so sections that check selected_country or similar state work correctly."""
    import streamlit as st

    st.session_state["active_section"] = section


def render_nav() -> None:
    """No-op in single-page flow mode. Kept for backward compatibility."""
    pass
