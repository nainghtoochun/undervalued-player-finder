"""Load the pipeline results into Postgres.

Run: python -m pipeline.load_db   (needs `docker compose up -d` first)

Every run empties the tables and reloads them, so it is safe to repeat.
The connection comes from DATABASE_URL (see .env.example).
"""
import json
import os

import pandas as pd
from sqlalchemy import create_engine, text

from pipeline.config import PROCESSED, RAW_SB, RAW_TM, ROOT

DEFAULT_URL = "postgresql+psycopg://upf:upf@localhost:5432/upf"
SEASON = "2015/16"


def database_url() -> str:
    url = os.getenv("DATABASE_URL", DEFAULT_URL)
    return url.replace("postgresql://", "postgresql+psycopg://", 1) if url.startswith("postgresql://") else url


def build_tables() -> dict[str, pd.DataFrame]:
    totals = pd.read_parquet(PROCESSED / "player_totals.parquet")
    metrics = pd.read_parquet(PROCESSED / "player_season_metrics.parquet")
    scores = pd.read_parquet(PROCESSED / "player_value_scores.parquet")
    matches = pd.read_csv(PROCESSED / "player_matches.csv").drop_duplicates("player_id")
    nick = pd.read_csv(RAW_SB / "player_nicknames.csv")[["player_id", "player_nickname"]]
    tm = pd.read_csv(RAW_TM / "players.csv.gz", usecols=["player_id", "date_of_birth"],
                     parse_dates=["date_of_birth"])

    players = (totals.sort_values("minutes", ascending=False).drop_duplicates("player_id")
               .merge(nick, on="player_id", how="left")
               .merge(matches[["player_id", "tm_player_id"]], on="player_id", how="left")
               .merge(tm.rename(columns={"player_id": "tm_player_id"}), on="tm_player_id", how="left"))
    players = pd.DataFrame({
        "player_id": players["player_id"], "name": players["player"], "nickname": players["player_nickname"],
        "team": players["team"], "league": players["league"], "position": players["position"],
        "position_group": players["position_group"], "tm_player_id": players["tm_player_id"].astype("Int64"),
        "birth_date": players["date_of_birth"].dt.date,
    })

    cols = ["player_id", "league", "team", "minutes", "npxg_p90", "xa_p90", "xt_pass_p90",
            "xt_carry_p90", "xt_p90", "np_goals_p90", "np_shots_p90"]
    season_metrics = metrics[cols].assign(season=SEASON)

    vals = pd.read_csv(RAW_TM / "player_valuations.csv.gz", usecols=["player_id", "date", "market_value_in_eur"])
    vals = vals[vals["player_id"].isin(players["tm_player_id"].dropna())]
    valuations = (vals.rename(columns={"player_id": "tm_player_id", "date": "valued_on",
                                       "market_value_in_eur": "market_value_eur"})
                  .drop_duplicates(["tm_player_id", "valued_on"]))
    valuations["valued_on"] = pd.to_datetime(valuations["valued_on"]).dt.date  # Postgres wants real dates

    value_scores = pd.DataFrame({
        "player_id": scores["player_id"], "season": SEASON, "age": scores["age"].round(1),
        "relegated": scores["relegated"].astype(bool), "value_2016_eur": scores["value_2016"].astype("int64"),
        "predicted_value_eur": scores["predicted_value_eur"].round().astype("int64"),
        "value_gap_pct": scores["value_gap_pct"],
        "gap_rank": scores["log_gap"].rank(ascending=False, method="first").astype(int),
        "value_2018_eur": scores["value_2018"].astype("Int64"),
    })
    report = json.loads((PROCESSED / "value_model_report.json").read_text())
    quintiles = pd.read_csv(PROCESSED / "backtest_by_quintile.csv").to_dict(orient="records")
    meta = pd.DataFrame({"key": ["value_model", "backtest", "backtest_by_quintile"],
                         "value": [json.dumps(report["model"]), json.dumps(report["backtest"]),
                                   json.dumps(quintiles)]})
    return {"players": players, "player_season_metrics": season_metrics,
            "valuations": valuations, "player_value_scores": value_scores, "app_meta": meta}


def load(engine, tables: dict[str, pd.DataFrame]) -> None:
    with engine.begin() as conn:  # one transaction: all tables load, or none do
        conn.execute(text((ROOT / "db" / "schema.sql").read_text()))
        conn.execute(text("TRUNCATE app_meta, player_value_scores, player_season_metrics, valuations, players"))
        for name in ["players", "player_season_metrics", "valuations", "player_value_scores"]:
            tables[name].to_sql(name, conn, if_exists="append", index=False, method="multi", chunksize=2000)
            print(f"  {name}: {len(tables[name]):,} rows")
        for row in tables["app_meta"].itertuples():
            conn.execute(text("INSERT INTO app_meta (key, value) VALUES (:k, CAST(:v AS JSONB))"),
                         {"k": row.key, "v": row.value})
        print(f"  app_meta: {len(tables['app_meta'])} rows")


if __name__ == "__main__":
    engine = create_engine(database_url())
    print(f"loading into {engine.url.render_as_string(hide_password=True)}")
    load(engine, build_tables())
    with engine.connect() as conn:
        top = conn.execute(text("""
            SELECT COALESCE(p.nickname, p.name) AS name, p.team, s.value_2016_eur, s.predicted_value_eur, s.value_2018_eur
            FROM player_value_scores s JOIN players p USING (player_id)
            WHERE s.age < 30 AND NOT s.relegated
            ORDER BY s.gap_rank LIMIT 5""")).fetchall()
    print("\ncheck query, top 5 bargains under 30 on clubs that stayed up:")
    for r in top:
        print(f"  {r.name:<35} {r.team:<22} 2016 EUR {r.value_2016_eur:>11,}  fair EUR {r.predicted_value_eur:>11,}"
              f"  2018 EUR {r.value_2018_eur or 0:>11,}")
