"""Pre-generate narration audio with Amazon Polly (generative voice).

Uses the AWS credentials already configured on this machine (via the AWS CLI / env)
to synthesize warm, human narration for the prologue and the hand-written featured
country stories, saving MP3s into assets/audio/. The Streamlit app plays these files
when present and falls back to the browser Web Speech API otherwise.

Usage:
    python -m scripts.generate_narration              # generate missing files
    python -m scripts.generate_narration --force      # regenerate everything
    python -m scripts.generate_narration --voice Ruth # pick a different Polly voice
"""
from __future__ import annotations

import argparse
from pathlib import Path

import boto3

from sections.guided import (CHAPTERS, PROLOGUE_NARRATION, _FEATURED_STORIES,
                             _chapter_narration, _hub_narration)
from sections.journeys import JOURNEYS_INTRO
from data import repository as repo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"

DEFAULT_VOICE = "Amy"
DEFAULT_ENGINE = "generative"
DEFAULT_REGION = "us-east-1"

# One narrator per country, used for BOTH its intro and its chapters (cohesive voice).
# We favour Polly's "long-form" engine — purpose-built for expressive narration — for
# most, and keep a few accented "generative" voices (Amy/Brian/Kajal/Matthew) for
# variety.  Each entry is (VoiceId, Engine).
#   long-form en voices: Danielle, Gregory, Patrick, Ruth
#   generative accents:  Amy (GB), Brian (GB), Kajal (IN), Matthew (US) ...
VOICES: dict[str, tuple[str, str]] = {
    "prologue": ("Amy", "generative"),      # inviting British opener
    "hub_IND": ("Kajal", "generative"),     # Indian-English accent
    "hub_ITA": ("Gregory", "long-form"),
    "hub_JPN": ("Ruth", "long-form"),
    "hub_MEX": ("Danielle", "long-form"),
    "hub_FRA": ("Amy", "generative"),
    "hub_ESP": ("Danielle", "long-form"),    # distinct expressive voice (was clashing with Ethiopia's Ruth)
    "hub_CHN": ("Ruth", "long-form"),
    "hub_THA": ("Danielle", "long-form"),
    "hub_MAR": ("Brian", "generative"),      # British male
    "hub_BRA": ("Matthew", "generative"),
    "hub_KOR": ("Patrick", "long-form"),
    "hub_ETH": ("Ruth", "long-form"),
    "hub_GRC": ("Matthew", "generative"),    # replaced Gregory (flagged) — warm, liked on Brazil
    "journeys_intro": ("Amy", "generative"),  # documentary narrator for the food-travel story
    "hub_VNM": ("Danielle", "long-form"),
    "hub_TUR": ("Patrick", "long-form"),
    "hub_PER": ("Matthew", "generative"),
}

# Non-featured countries that also get a real narrator (their hub + chapter narration
# is generated from live data). Add ISO3 -> (voice, engine) here to fix "robotic"
# browser fallbacks one country at a time.
EXTRA_COUNTRIES: dict[str, tuple[str, str]] = {
    "COL": ("Matthew", "generative"),   # Colombia — warm voice (as on Brazil)
}


def _jobs() -> dict[str, tuple[str, str, str]]:
    """key -> (text, voice, engine) for the prologue, hub intros, and chapters."""
    jobs: dict[str, tuple[str, str, str]] = {}
    p_voice, p_engine = VOICES["prologue"]
    jobs["prologue"] = (PROLOGUE_NARRATION, p_voice, p_engine)

    jv, je = VOICES.get("journeys_intro", (DEFAULT_VOICE, DEFAULT_ENGINE))
    jobs["journeys_intro"] = (JOURNEYS_INTRO, jv, je)

    for iso3, story in _FEATURED_STORIES.items():
        voice, engine = VOICES.get(f"hub_{iso3}", (DEFAULT_VOICE, DEFAULT_ENGINE))
        jobs[f"hub_{iso3}"] = (story, voice, engine)

        profile = repo.get_country_profile(iso3) or {}
        name = profile.get("name", iso3)
        for cid, _emoji, _title, _teaser in CHAPTERS:
            text = _chapter_narration(cid, iso3, name, profile)
            # Same narrator voice for a country's chapters as its intro (cohesive).
            jobs[f"ch_{iso3}_{cid}"] = (text, voice, engine)

    # Extra (non-featured) countries: narrate their generated hub + chapter text.
    for iso3, (voice, engine) in EXTRA_COUNTRIES.items():
        if iso3 in _FEATURED_STORIES:
            continue
        profile = repo.get_country_profile(iso3) or {}
        name = profile.get("name", iso3)
        jobs[f"hub_{iso3}"] = (_hub_narration(iso3, name, profile), voice, engine)
        for cid, _emoji, _title, _teaser in CHAPTERS:
            jobs[f"ch_{iso3}_{cid}"] = (_chapter_narration(cid, iso3, name, profile),
                                        voice, engine)
    return jobs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--engine", default=DEFAULT_ENGINE)
    ap.add_argument("--region", default=DEFAULT_REGION)
    ap.add_argument("--force", action="store_true", help="regenerate existing files")
    args = ap.parse_args()

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    polly = boto3.client("polly", region_name=args.region)

    jobs = _jobs()
    made, skipped = 0, 0
    for key, (text, voice, engine) in jobs.items():
        out = AUDIO_DIR / f"{key}.mp3"
        if out.exists() and out.stat().st_size > 0 and not args.force:
            skipped += 1
            continue
        resp = polly.synthesize_speech(
            Text=text, VoiceId=voice, Engine=engine, OutputFormat="mp3",
        )
        audio = resp["AudioStream"].read()
        out.write_bytes(audio)
        made += 1
        print(f"  ✓ {out.name:<22} [{voice}/{engine}]  ({len(audio) // 1024} KB)")

    print(f"\nDone. Generated {made}, skipped {skipped}. -> {AUDIO_DIR}")


if __name__ == "__main__":
    main()
