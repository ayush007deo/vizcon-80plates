# Around the World in 80 Plates

An interactive Streamlit journey through world food cultures, built for Viz Con 2026
(Theme 4: Culture Through Food & Traditions). Rather than a dashboard, it is a guided,
museum-like experience: spin a globe, click a country, fill its plate, compare cuisines,
follow ingredients and spices across centuries, and end at a surprise Global Dinner Party.

The spec lives in `.kiro/specs/around-the-world-in-80-plates/`
(`requirements.md`, `design.md`, `tasks.md`) and the source list in `data.txt`.

## Architecture

Two clearly separated parts that meet at PostgreSQL:

- **Offline data pipeline** (`pipeline/`) — ingests public + curated datasets, reconciles
  every country to an ISO 3166-1 alpha-3 key, derives plate proportions / similarity /
  clusters, and loads everything into PostgreSQL. Run ahead of time and re-runnable.
- **Runtime Streamlit app** (`app.py`, `sections/`, `components/`, `viz/`, `data/`) —
  a **read-only** consumer of PostgreSQL. It never writes to the store.

## Project layout

```
app.py            # Streamlit entry point + router + session state
config.py         # settings (DATABASE_URL from env), constants
data/             # cached data-access layer (db.py, repository.py)
sections/         # one module per storytelling section (render())
components/        # navigation, cards, narrative, theme, citation
viz/              # chart builders -> (figure, alt_text)
pipeline/         # ingest/ -> reconcile -> derive -> load
```

## Setup

Requires Python 3.11+ and a reachable PostgreSQL instance.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then edit DATABASE_URL
```

## Running

Populate the database first (pipeline), then launch the app:

```bash
# 1) Build the data store (schema + load). Added in tasks 2 and 4.
python -m pipeline.run_pipeline

# 2) Launch the read-only app.
streamlit run app.py
```

## Data sources

All datasets are public and cited in-app (Req 19) and recorded in the `source` table.
See `.kiro/specs/around-the-world-in-80-plates/data.txt` for the full list.

## Testing

```bash
pytest
```
