# Undervalued Player Finder
Hi, I am Naing Htoo Chun.
Finds soccer players whose on-ball contribution is worth more than their market value.

Built on StatsBomb open event data (2015/16 Premier League, La Liga, Serie A, Ligue 1, plus Leverkusen's Bundesliga matches) and Transfermarkt market values. It uses a custom expected goals (xG) model and an Expected Threat (xT) model, then checks its picks against what actually happened to those players' values in the next two years.

> Live demo, screenshots and findings will go here once deployed. See `BLUEPRINT.md` for the full plan.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
docker compose up -d            # starts Postgres
python -m pipeline.ingest_statsbomb   # all five leagues, about 15 to 20 minutes
python -m pipeline.run_all            # xG, xT and the player table
uvicorn api.main:app --reload
```

## Structure

| Folder | What lives there |
| --- | --- |
| `pipeline/` | Data download, xG model, xT model, player metrics, value model, DB loading |
| `api/` | FastAPI backend that serves players and bargains |
| `web/` | React + Vite + Tailwind frontend |
| `db/` | Postgres schema |
| `notebooks/` | Exploration only. Final logic always moves into `pipeline/` |
| `tests/` | Unit tests for the models and metrics |
| `docs/` | Design decisions and the findings write-up |
