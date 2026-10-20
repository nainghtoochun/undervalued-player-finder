"""Export the results as small JSON files for the website.

Run: python -m pipeline.export_web   (after python -m pipeline.value_model)

The live site reads these files directly, so it needs no server or database
and loads instantly. The same fields are served by the FastAPI backend
(api/main.py) for anyone running the full stack locally.

Writes web/public/data/{summary,players,history}.json
"""
import json

import numpy as np
import pandas as pd

from pipeline.config import PROCESSED, RAW_SB, RAW_TM, ROOT

OUT = ROOT / "web" / "public" / "data"
PERCENTILE_METRICS = ["npxg_p90", "xa_p90", "xt_p90", "xt_pass_p90", "xt_carry_p90", "np_shots_p90"]


def percent_rank(s: pd.Series) -> pd.Series:
    """Same as Postgres PERCENT_RANK(): 0 for the lowest, 100 for the highest."""
    n = len(s)
    return ((s.rank(method="min") - 1) / max(n - 1, 1) * 100).round(1)


def build_players() -> pd.DataFrame:
    metrics = pd.read_parquet(PROCESSED / "player_season_metrics.parquet")
    main = metrics.sort_values("minutes", ascending=False).drop_duplicates("player_id")  # main league spell
    scores = pd.read_parquet(PROCESSED / "player_value_scores.parquet")[
        ["player_id", "age", "relegated", "value_2016", "predicted_value_eur", "value_gap_pct", "log_gap",
         "value_2018"]]
    nick = pd.read_csv(RAW_SB / "player_nicknames.csv")[["player_id", "player_nickname"]]

    df = main.merge(scores, on="player_id", how="left").merge(nick, on="player_id", how="left")
    df["gap_rank"] = df["log_gap"].rank(ascending=False, method="first")
    for c in PERCENTILE_METRICS:
        df[f"pct_{c}"] = df.groupby("position_group")[c].transform(percent_rank)

    out = pd.DataFrame({
        "player_id": df["player_id"].astype(int),
        "name": df["player_nickname"].fillna(df["player"]),
        "full_name": df["player"],
        "team": df["team"], "league": df["league"],
        "position": df["position"], "position_group": df["position_group"],
        "age": df["age"].round(1),
        "minutes": df["minutes"].round(0),
        **{c: df[c].round(4) for c in ["npxg_p90", "xa_p90", "xt_p90", "xt_pass_p90", "xt_carry_p90",
                                       "np_goals_p90", "np_shots_p90"]},
        "value_2016_eur": df["value_2016"].astype("Int64"),
        "predicted_value_eur": df["predicted_value_eur"].round(-3).astype("Int64"),
        "value_gap_pct": df["value_gap_pct"].round(3),
        "gap_rank": df["gap_rank"].astype("Int64"),
        "value_2018_eur": df["value_2018"].astype("Int64"),
        "relegated": df["relegated"].map({1: True, 0: False}),
        "percentiles": df[[f"pct_{c}" for c in PERCENTILE_METRICS]].rename(
            columns=lambda c: c.removeprefix("pct_")).to_dict(orient="records"),
    })
    return out.sort_values(["gap_rank", "player_id"], na_position="last").reset_index(drop=True)


def build_history(players: pd.DataFrame) -> dict:
    matches = pd.read_csv(PROCESSED / "player_matches.csv").drop_duplicates("player_id")
    scored = players.loc[players["gap_rank"].notna(), ["player_id"]].merge(matches, on="player_id")
    vals = pd.read_csv(RAW_TM / "player_valuations.csv.gz", usecols=["player_id", "date", "market_value_in_eur"])
    vals = vals[(vals["date"] >= "2014-01-01") & (vals["date"] <= "2019-12-31")]
    vals = vals.merge(scored.rename(columns={"player_id": "sb_id", "tm_player_id": "player_id"}),
                      on="player_id").sort_values("date")
    return {str(k): g[["date", "market_value_in_eur"]].values.tolist() for k, g in vals.groupby("sb_id")}


def build_summary(players: pd.DataFrame) -> dict:
    report = json.loads((PROCESSED / "value_model_report.json").read_text())
    quintiles = pd.read_csv(PROCESSED / "backtest_by_quintile.csv")
    quintiles["extra_growth_pct"] = (np.exp(quintiles["extra_growth_log"]) - 1).round(4)
    return {
        "players": int(len(players)),
        "scored_players": int(players["gap_rank"].notna().sum()),
        "season": "2015/16",
        "valuation_date": "summer 2016",
        "backtest_date": "summer 2018",
        "backtest": report["backtest"],
        "backtest_by_quintile": quintiles.to_dict(orient="records"),
        "value_model": report["model"],
        "ablation": json.loads((PROCESSED / "ablation.json").read_text())
        if (PROCESSED / "ablation.json").exists() else None,
    }


def _clean(obj):
    """JSON cannot hold NaN or pandas NA, so turn them into null."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    if obj is pd.NA or (isinstance(obj, float) and np.isnan(obj)):
        return None
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    players = build_players()
    files = {
        "players.json": players.to_dict(orient="records"),
        "history.json": build_history(players),
        "summary.json": build_summary(players),
    }
    for name, data in files.items():
        path = OUT / name
        path.write_text(json.dumps(_clean(data), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1e3:.0f} KB)")
