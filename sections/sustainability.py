"""Sustainability chapter — "The Weight of a Plate".

The content lives in data.sustainability (curated emissions + the plant-vs-longevity
story). This section is a thin adapter so the guided flow and any importer that expects
sections.sustainability.render()/body() keeps working.
"""
from __future__ import annotations

from data import sustainability as _sustainability


def render() -> None:
    _sustainability.render()


def body() -> None:
    _sustainability.render()
