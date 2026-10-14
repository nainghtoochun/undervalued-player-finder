"""FastAPI backend. Endpoints are stubs until the pipeline loads data."""
import os

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Undervalued Player Finder API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("API_CORS_ORIGIN", "http://localhost:5173")],
    allow_methods=["GET"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/players")
def list_players(league: str | None = None, position: str | None = None,
                 max_value_eur: int | None = None, limit: int = Query(50, le=200)):
    # TODO week 4: query player_season_metrics joined with player_value_scores
    return []


@app.get("/players/{player_id}")
def get_player(player_id: int):
    # TODO week 4: metrics, value gap, and xT by pitch zone for the heatmap
    return {}


@app.get("/bargains")
def bargains(position: str | None = None, limit: int = Query(10, le=50)):
    # TODO week 4: top players by value_gap_pct
    return []
