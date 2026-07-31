# How We Used AI (AI Usage Record)

This document records where and how generative AI, LLMs, and NLP techniques were used
to build "Around the World in 80 Plates," so our process is transparent and reproducible
(Req 21.1, 21.4). It supports the Viz Con "Best Use of GenAI" award.

## Summary

AI was used as a **development and content-shaping assistant**, not as an unreviewed
source of facts. All country-level numbers come from cited public datasets (see
`.kiro/specs/around-the-world-in-80-plates/data.txt`). Curated storytelling data was
drafted with AI help and human-reviewed against public references.

## AI-assisted steps

| Step | How AI was used | Inputs | Tool | Human review |
|---|---|---|---|---|
| Spec authoring | Draft & refine requirements (EARS), design, and tasks | Contest brief, theme prompt | LLM assistant | Team edited/approved each doc |
| Code generation | Generate Streamlit sections, viz builders, pipeline modules, tests | Design doc + requirements | LLM assistant | Reviewed, run, and tested |
| Data discovery | Suggest candidate public datasets and reconciliation approach | Feature list | LLM assistant + web search | Links verified, licenses checked |
| Curated content drafting | Draft famous-dishes, migrations, spice routes, festivals, dinner symbolism | Public references (encyclopedic) | LLM assistant | Fact-checked against public sources |
| Taste-tag / NLP derivation (optional) | Derive `dish.taste_tags` from dish/ingredient text | Dish names + ingredients | Rule-based NLP (extensible to LLM) | Spot-checked |
| Narrative & insight copy | Draft section opening sentences and phrasing | Section intent | LLM assistant | Reviewed for tone & inclusivity |

## Reproducibility

- **Spec → code**: the `.kiro/specs/around-the-world-in-80-plates/` documents capture the
  requirements and design the code was generated from. Regenerating from the same design
  yields equivalent modules.
- **Data pipeline**: `python -m pipeline.run_pipeline` rebuilds the database
  deterministically from `pipeline/raw/` (public downloads) + `pipeline/curated/`.
- **Provenance in the data**: any content produced by an AI/NLP technique is flagged in
  the database via `dish.ai_derived` and `dish.ai_technique` (Req 21.2). The app shows an
  "AI-assisted" badge wherever such content is displayed (Req 21.3). In the current build,
  taste tags are curated (`ai_derived = false`); enabling the NLP step sets these flags.

## What AI did NOT do

- It did not invent country statistics; those are from FAOSTAT, World Bank, Kaggle, and
  UNdata as cited.
- It did not make final decisions on dataset selection, licensing, or claims — those were
  human-reviewed.

## How to enable/verify the NLP taste-tag step

The pipeline's `derive` stage can tag dishes from ingredient/category text. When used, it
sets `ai_derived = true` and records the `ai_technique`. To verify provenance in the DB:

```sql
SELECT name, taste_tags, ai_derived, ai_technique FROM dish WHERE ai_derived;
```
