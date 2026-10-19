"""Per 90 player metrics for the 2015/16 season.

Run: python -m pipeline.player_metrics   (after python -m pipeline.xg_model)

Steps
1. Fit the xT grid on every downloaded league (counted one league at a time).
2. For each full league (see PLAYER_LEAGUES in config), work out minutes played, then npxG, xA and xT for every player.
3. Combine, keep players with MIN_MINUTES or more, save to data/processed.
"""
import json

import numpy as np
import pandas as pd

from pipeline.config import MIN_MINUTES, PLAYER_LEAGUES
from pipeline.xg_model import SHOT_COLUMNS, non_penalty_shots, predict_xg
from pipeline.xt_model import XT_COLUMNS, XTCounts, action_xt, count_actions, solve_xt

RED_CARDS = {"Red Card", "Second Yellow"}
METRIC_TYPES = ["Starting XI", "Substitution", "Foul Committed", "Bad Behaviour", "Player Off",
                "Half End", "Shot", "Pass", "Carry"]

METRIC_COLUMNS = sorted(set(SHOT_COLUMNS + XT_COLUMNS + [
    "minute", "second", "period", "position", "pass_type", "tactics", "team_id",
    "substitution_replacement_id", "substitution_replacement",
    "foul_committed_card", "bad_behaviour_card", "player_off_permanent",
]))


# ---------- minutes played ----------

def _clock(events: pd.DataFrame) -> pd.Series:
    """Seconds since kick off. StatsBomb minutes keep counting in the second half (45, 46, ...)."""
    return events["minute"].astype(float) * 60 + events["second"].astype(float)


def minutes_played(events: pd.DataFrame) -> pd.DataFrame:
    """One row per player per match with minutes played.

    Starters come on at 0. Substitutes come on when they replace someone.
    A player goes off when substituted, sent off, or carried off for good;
    otherwise they play until the last event of the match.
    """
    rows = []
    for match_id, m in events.groupby("match_id", sort=False):
        t = _clock(m)
        end = t.max()
        on, off, team_of, name_of = {}, {}, {}, {}

        for _, ev in m[m["type"] == "Starting XI"].iterrows():
            lineup = json.loads(ev["tactics"])["lineup"] if isinstance(ev["tactics"], str) else []
            for p in lineup:
                pid = int(p["player"]["id"])
                on[pid], team_of[pid], name_of[pid] = 0.0, ev["team"], p["player"]["name"]

        for idx, ev in m[m["type"] == "Substitution"].iterrows():
            off[int(ev["player_id"])] = t[idx]
            new = ev["substitution_replacement_id"]
            if pd.notna(new):
                new = int(float(new))
                on[new], team_of[new] = t[idx], ev["team"]
                name_of[new] = ev["substitution_replacement"]

        cards = m["foul_committed_card"].isin(RED_CARDS) | m["bad_behaviour_card"].isin(RED_CARDS)
        perm = (m["type"] == "Player Off") & m["player_off_permanent"].fillna(False).astype(bool)
        for idx, ev in m[cards | perm].iterrows():
            if pd.notna(ev["player_id"]):
                pid = int(ev["player_id"])
                off[pid] = min(off.get(pid, end), t[idx])

        for pid, start in on.items():
            stop = off.get(pid, end)
            rows.append({"match_id": match_id, "player_id": pid, "player": name_of[pid],
                         "team": team_of[pid], "minutes": max(stop - start, 0.0) / 60})
    return pd.DataFrame(rows)


def one_name_per_team(events: pd.DataFrame) -> pd.Series:
    """StatsBomb sometimes spells a club two ways ("Marseille", "Olympique de Marseille").
    Use the team id to give every club its most common name."""
    names = events.loc[events["type"] == "Starting XI"].groupby("team_id")["team"].agg(
        lambda s: s.value_counts().index[0])
    return events["team_id"].map(names).fillna(events["team"])


# ---------- positions ----------

def position_group(name) -> str:
    if not isinstance(name, str):
        return "UNK"
    if name == "Goalkeeper":
        return "GK"
    if "Back" in name:  # check before "Wing" so Left Wing Back counts as a defender
        return "DEF"
    if "Midfield" in name:
        return "MID"
    if any(k in name for k in ("Wing", "Forward", "Striker")):
        return "FWD"
    return "UNK"


def main_position(events: pd.DataFrame) -> pd.DataFrame:
    on_ball = events[events["player_id"].notna() & events["position"].notna()]
    top = (on_ball.groupby(["player_id", "position"]).size().rename("n").reset_index()
           .sort_values("n", ascending=False).drop_duplicates("player_id"))
    top["player_id"] = top["player_id"].astype(int)
    top["position_group"] = top["position"].map(position_group)
    return top[["player_id", "position", "position_group"]]


# ---------- per player totals ----------

def player_totals(events: pd.DataFrame, xg_model, xg_cols, xt_grid) -> pd.DataFrame:
    """Season totals for one league (minutes, npxG, xA, xT, goals)."""
    events = events.assign(team=one_name_per_team(events))
    mins = minutes_played(events)

    shots = non_penalty_shots(events)
    shots["xg"] = predict_xg(shots, xg_model, xg_cols)
    shots["goal"] = (shots["shot_outcome"] == "Goal").astype(int)
    shots["player_id"] = shots["player_id"].astype(int)

    # xA: the passer of the key pass gets the xG of the shot it set up
    passer = events.loc[events["type"] == "Pass", ["id", "player_id"]].rename(
        columns={"id": "shot_key_pass_id", "player_id": "passer_id"})
    assisted = shots[shots["shot_key_pass_id"].notna()].merge(passer, on="shot_key_pass_id", how="inner")

    passes = events[(events["type"] == "Pass") & events["pass_outcome"].isna()
                    & events["pass_type"].isna()]  # successful open play passes only
    carries = events[events["type"] == "Carry"]
    passes = passes.assign(xt=action_xt(passes, "pass_end_location", xt_grid))
    carries = carries.assign(xt=action_xt(carries, "carry_end_location", xt_grid))

    def by_player(df, col, name, pid="player_id"):
        s = df.groupby(df[pid].astype(int))[col].sum().rename(name)
        s.index.name = "player_id"
        return s

    totals = pd.concat([
        mins.groupby("player_id")["minutes"].sum(),
        by_player(shots, "xg", "npxg"),
        by_player(shots, "goal", "np_goals"),
        shots.groupby("player_id").size().rename("np_shots"),
        by_player(assisted, "xg", "xa", pid="passer_id"),
        by_player(passes, "xt", "xt_pass"),
        by_player(carries, "xt", "xt_carry"),
    ], axis=1).fillna(0.0)
    totals.index.name = "player_id"

    # name and team: the team they played most minutes for (some players moved in January)
    main_team = (mins.groupby(["player_id", "player", "team"])["minutes"].sum().reset_index()
                 .sort_values("minutes", ascending=False).drop_duplicates("player_id")
                 .set_index("player_id")[["player", "team"]])
    out = totals.join(main_team, how="inner").reset_index()
    return out.merge(main_position(events), on="player_id", how="left")


def per90(totals: pd.DataFrame, min_minutes: float = MIN_MINUTES) -> pd.DataFrame:
    df = totals[totals["minutes"] >= min_minutes].copy()
    for col in ["npxg", "xa", "xt_pass", "xt_carry", "np_goals", "np_shots"]:
        df[f"{col}_p90"] = df[col] / df["minutes"] * 90
    df["xt_p90"] = df["xt_pass_p90"] + df["xt_carry_p90"]
    df["npxg_xa_p90"] = df["npxg_p90"] + df["xa_p90"]
    return df.sort_values("xt_p90", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    import joblib

    from pipeline.config import PROCESSED
    from pipeline.ingest_statsbomb import downloaded_leagues, load_events
    from pipeline.xt_model import plot_xt

    leagues = downloaded_leagues()
    saved = joblib.load(PROCESSED / "xg_model.joblib")
    print(f"leagues: {', '.join(leagues)}\nxG model: {saved['name']}")

    counts = XTCounts()
    for lg in leagues:
        counts = counts.add(count_actions(load_events([lg], columns=XT_COLUMNS, types=["Shot", "Pass", "Carry"])))
        print(f"  counted xT actions for {lg}")
    grid = solve_xt(counts)
    np.save(PROCESSED / "xt_grid.npy", grid)
    plot_xt(grid, PROCESSED / "xt_heatmap.png")
    print(f"xT grid saved, max zone value {grid.max():.3f}")

    frames = []
    for lg in [lg for lg in leagues if lg in PLAYER_LEAGUES]:
        ev = load_events([lg], columns=METRIC_COLUMNS, types=METRIC_TYPES)
        t = player_totals(ev, saved["model"], saved["columns"], grid)
        t["league"] = lg
        frames.append(t)
        print(f"  {lg}: {len(t)} players")
    totals = pd.concat(frames, ignore_index=True)
    table = per90(totals)
    totals.to_parquet(PROCESSED / "player_totals.parquet")
    table.to_parquet(PROCESSED / "player_season_metrics.parquet")
    table.to_csv(PROCESSED / "player_season_metrics.csv", index=False)

    show = ["player", "team", "position_group", "minutes", "npxg_p90", "xa_p90", "xt_p90"]
    print(f"\n{len(table)} players with {MIN_MINUTES}+ minutes. Top 10 by xT per 90:")
    print(table[show].head(10).round(3).to_string(index=False))
