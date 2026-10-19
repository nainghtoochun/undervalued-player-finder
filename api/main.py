"""FastAPI backend for the Undervalued Player Finder.

Run locally:  docker compose up -d && python -m pipeline.load_db
              uvicorn api.main:app --reload
Docs:         http://localhost:8000/docs
"""
import os
from datetime import date
from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

DEFAULT_URL = "postgresql+psycopg://upf:upf@localhost:5432/upf"
League = Literal["Premier League", "La Liga", "Serie A", "Ligue 1"]
Position = Literal["DEF", "MID", "FWD"]
SortKey = Literal["value_gap_pct", "xt_p90", "npxg_p90", "xa_p90", "value_2016_eur", "minutes"]


# ---------- database ----------

def database_url() -> str:
    url = os.getenv("DATABASE_URL", DEFAULT_URL)
    return url.replace("postgresql://", "postgresql+psycopg://", 1) if url.startswith("postgresql://") else url


@lru_cache
def get_engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True)


def get_conn():
    with get_engine().connect() as conn:
        yield conn


# ---------- response models ----------

class PlayerRow(BaseModel):
    player_id: int
    name: str
    team: str
    league: str
    position_group: str
    age: float | None
    minutes: float
    npxg_p90: float
    xa_p90: float
    xt_p90: float
    value_2016_eur: int | None
    predicted_value_eur: int | None
    value_gap_pct: float | None
    gap_rank: int | None
    value_2018_eur: int | None
    relegated: bool | None


class ValuePoint(BaseModel):
    date: date
    value_eur: int


class PlayerDetail(PlayerRow):
    full_name: str
    position: str | None
    xt_pass_p90: float
    xt_carry_p90: float
    np_goals_p90: float
    np_shots_p90: float
    percentiles: dict[str, float]   # 0 to 100, against the same position group
    value_history: list[ValuePoint]


class Summary(BaseModel):
    players: int
    scored_players: int
    backtest: dict
    backtest_by_quintile: list[dict]
    value_model: dict


# ---------- queries ----------

BASE_SELECT = """
    SELECT p.player_id, COALESCE(p.nickname, p.name) AS name, p.name AS full_name, p.team, m.league,
           p.position, p.position_group, s.age, m.minutes, m.npxg_p90, m.xa_p90, m.xt_p90,
           m.xt_pass_p90, m.xt_carry_p90, m.np_goals_p90, m.np_shots_p90,
           s.value_2016_eur, s.predicted_value_eur, s.value_gap_pct, s.gap_rank, s.value_2018_eur, s.relegated
    FROM player_main_season m
    JOIN players p USING (player_id)
    LEFT JOIN player_value_scores s USING (player_id)
"""
PERCENTILE_METRICS = ["npxg_p90", "xa_p90", "xt_p90", "xt_pass_p90", "xt_carry_p90", "np_shots_p90"]

app = FastAPI(
    title="Undervalued Player Finder API",
    description="Soccer players whose 2015/16 performance was worth more than their market price.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("API_CORS_ORIGIN", "http://localhost:5173").split(","),
    allow_methods=["GET"],
)


@app.get("/health")
def health(conn: Connection = Depends(get_conn)):
    conn.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/summary", response_model=Summary)
def summary(conn: Connection = Depends(get_conn)):
    meta = dict(conn.execute(text("SELECT key, value FROM app_meta")).all())
    counts = conn.execute(text(
        "SELECT (SELECT COUNT(*) FROM player_main_season), (SELECT COUNT(*) FROM player_value_scores)")).one()
    return Summary(players=counts[0], scored_players=counts[1], backtest=meta.get("backtest", {}),
                   backtest_by_quintile=meta.get("backtest_by_quintile", []),
                   value_model=meta.get("value_model", {}))


@app.get("/players", response_model=list[PlayerRow])
def list_players(
    league: League | None = None,
    position: Position | None = None,
    max_value_eur: int | None = Query(None, ge=0),
    max_age: float | None = Query(None, ge=15, le=45),
    search: str | None = Query(None, min_length=2, max_length=50),
    sort: SortKey = "value_gap_pct",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn: Connection = Depends(get_conn),
):
    where, params = ["TRUE"], {"limit": limit, "offset": offset}
    if league:
        where.append("m.league = :league")
        params["league"] = league
    if position:
        where.append("p.position_group = :position")
        params["position"] = position
    if max_value_eur is not None:
        where.append("s.value_2016_eur <= :max_value")
        params["max_value"] = max_value_eur
    if max_age is not None:
        where.append("s.age <= :max_age")
        params["max_age"] = max_age
    if search:
        where.append("(p.name ILIKE :q OR p.nickname ILIKE :q OR p.team ILIKE :q)")
        params["q"] = f"%{search}%"
    # sort is checked against a fixed list (SortKey), so it is safe to place in the SQL
    sql = (f"{BASE_SELECT} WHERE {' AND '.join(where)} "
           f"ORDER BY {sort} DESC NULLS LAST, player_id LIMIT :limit OFFSET :offset")
    return [dict(r._mapping) for r in conn.execute(text(sql), params)]


@app.get("/bargains", response_model=list[PlayerRow])
def bargains(
    position: Position | None = None,
    max_age: float = Query(30, ge=15, le=45),
    include_relegated: bool = False,
    limit: int = Query(10, ge=1, le=50),
    conn: Connection = Depends(get_conn),
):
    where, params = ["s.gap_rank IS NOT NULL", "s.age <= :max_age"], {"max_age": max_age, "limit": limit}
    if position:
        where.append("p.position_group = :position")
        params["position"] = position
    if not include_relegated:
        where.append("NOT s.relegated")
    sql = f"{BASE_SELECT} WHERE {' AND '.join(where)} ORDER BY s.gap_rank LIMIT :limit"
    return [dict(r._mapping) for r in conn.execute(text(sql), params)]


@app.get("/players/{player_id}", response_model=PlayerDetail)
def get_player(player_id: int, conn: Connection = Depends(get_conn)):
    row = conn.execute(text(f"{BASE_SELECT} WHERE p.player_id = :id"), {"id": player_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="player not found")

    pct_cols = ", ".join(f"PERCENT_RANK() OVER (ORDER BY m.{c}) AS {c}" for c in PERCENTILE_METRICS)
    pct = conn.execute(text(f"""
        SELECT * FROM (
            SELECT m.player_id, {pct_cols}
            FROM player_main_season m JOIN players p USING (player_id)
            WHERE p.position_group = :pg
        ) ranked WHERE player_id = :id"""), {"pg": row["position_group"], "id": player_id}).mappings().first()

    history = conn.execute(text("""
        SELECT v.valued_on AS date, v.market_value_eur AS value_eur
        FROM valuations v JOIN players p ON p.tm_player_id = v.tm_player_id
        WHERE p.player_id = :id AND v.valued_on BETWEEN '2014-01-01' AND '2019-12-31'
        ORDER BY v.valued_on"""), {"id": player_id}).mappings().all()

    percentiles = {c: round(float(pct[c]) * 100, 1) for c in PERCENTILE_METRICS} if pct else {}
    return PlayerDetail(**row, percentiles=percentiles, value_history=[dict(h) for h in history])
