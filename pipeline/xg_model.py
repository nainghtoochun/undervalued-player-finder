"""Expected goals (xG) model trained on StatsBomb shots.

Week 1 used only where the shot was taken from.
Week 2 adds freeze frames, the positions of every player at the moment of the shot,
so the model knows how many defenders were in the way and where the keeper stood.

Run: python -m pipeline.xg_model
"""
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from pipeline.config import GOAL_X, GOAL_Y, POST_HIGH_Y, POST_LOW_Y

SHOT_COLUMNS = [
    "id", "match_id", "type", "location", "shot_type", "shot_body_part", "shot_outcome",
    "under_pressure", "shot_first_time", "shot_statsbomb_xg", "shot_freeze_frame",
    "shot_key_pass_id", "player_id", "player", "team", "play_pattern",
]

BASIC_FEATURES = ["distance", "angle", "is_header", "under_pressure", "first_time"]
FREEZE_FEATURES = [
    "is_free_kick", "from_counter", "defenders_in_cone", "keeper_in_cone",
    "keeper_dist_to_goal", "nearest_defender", "has_freeze_frame",
]
ALL_FEATURES = BASIC_FEATURES + FREEZE_FEATURES


def _flag(series: pd.Series) -> np.ndarray:
    return series.fillna(False).astype(bool).astype(int).to_numpy()


def _in_triangle(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """True for each point in p (n x 2) that lies inside triangle abc."""
    def cross(o, u, v):
        return (u[0] - o[0]) * (v[:, 1] - o[1]) - (u[1] - o[1]) * (v[:, 0] - o[0])
    d1, d2, d3 = cross(a, b, p), cross(b, c, p), cross(c, a, p)
    has_neg = (d1 < 0) | (d2 < 0) | (d3 < 0)
    has_pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
    return ~(has_neg & has_pos)


def freeze_frame_features(location, frame_json) -> dict:
    """Features from one shot's freeze frame (positions of visible players)."""
    out = {"defenders_in_cone": 0, "keeper_in_cone": 0, "keeper_dist_to_goal": np.nan,
           "nearest_defender": np.nan, "has_freeze_frame": 0}
    if not isinstance(frame_json, str):
        return out
    frame = json.loads(frame_json)
    shot = np.asarray(location, dtype=float)
    post_a, post_b = np.array([GOAL_X, POST_LOW_Y]), np.array([GOAL_X, POST_HIGH_Y])
    opp = [p for p in frame if not p.get("teammate")]
    keeper = [p for p in opp if p.get("position", {}).get("name") == "Goalkeeper"]
    outfield = np.array([p["location"] for p in opp if p not in keeper], dtype=float).reshape(-1, 2)

    out["has_freeze_frame"] = 1
    if len(outfield):
        out["defenders_in_cone"] = int(_in_triangle(outfield, shot, post_a, post_b).sum())
        out["nearest_defender"] = float(np.min(np.hypot(*(outfield - shot).T)))
    if keeper:
        k = np.array(keeper[0]["location"], dtype=float).reshape(1, 2)
        out["keeper_in_cone"] = int(_in_triangle(k, shot, post_a, post_b)[0])
        out["keeper_dist_to_goal"] = float(np.hypot(GOAL_X - k[0, 0], GOAL_Y - k[0, 1]))
    return out


def shot_features(shots: pd.DataFrame, freeze: bool = True) -> pd.DataFrame:
    xy = np.vstack(shots["location"].to_numpy())
    x, y = xy[:, 0], xy[:, 1]
    a1 = np.arctan2(POST_LOW_Y - y, GOAL_X - x)
    a2 = np.arctan2(POST_HIGH_Y - y, GOAL_X - x)
    feats = pd.DataFrame({
        "distance": np.hypot(GOAL_X - x, GOAL_Y - y),
        "angle": np.abs(a2 - a1),  # how wide the goal mouth looks from the shot
        "is_header": (shots["shot_body_part"] == "Head").astype(int).to_numpy(),
        "under_pressure": _flag(shots["under_pressure"]),
        "first_time": _flag(shots["shot_first_time"]),
    }, index=shots.index)
    if not freeze:
        return feats

    feats["is_free_kick"] = (shots["shot_type"] == "Free Kick").astype(int).to_numpy()
    feats["from_counter"] = (shots["play_pattern"] == "From Counter").astype(int).to_numpy()
    ff = pd.DataFrame(
        [freeze_frame_features(loc, fj) for loc, fj in zip(shots["location"], shots["shot_freeze_frame"])],
        index=shots.index,
    )
    # missing keeper or defender: fill with typical values so the model can still score the shot
    ff["keeper_dist_to_goal"] = ff["keeper_dist_to_goal"].fillna(2.0)
    ff["nearest_defender"] = ff["nearest_defender"].fillna(ff["nearest_defender"].median()).fillna(5.0)
    return pd.concat([feats, ff], axis=1)


def non_penalty_shots(events: pd.DataFrame) -> pd.DataFrame:
    return events[(events["type"] == "Shot") & (events["shot_type"] != "Penalty")].copy()


def _scores(y, p) -> dict:
    return {"log_loss": log_loss(y, p), "brier": brier_score_loss(y, p), "auc": roc_auc_score(y, p)}


def evaluate(events: pd.DataFrame, seed: int = 42) -> tuple[pd.DataFrame, dict]:
    """Compare four models on held-out matches. Returns a table and the fitted models."""
    shots = non_penalty_shots(events)
    X = shot_features(shots)
    y = (shots["shot_outcome"] == "Goal").astype(int)
    split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    tr, te = next(split.split(X, y, groups=shots["match_id"]))

    candidates = {
        "distance only": (LogisticRegression(max_iter=1000), ["distance"]),
        "week 1 logistic": (LogisticRegression(max_iter=1000), BASIC_FEATURES),
        "week 2 logistic + freeze frame": (
            make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)), ALL_FEATURES),
        "week 2 gradient boosting + freeze frame": (
            HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                           l2_regularization=1.0, random_state=seed), ALL_FEATURES),
    }
    rows, fitted = [], {}
    for name, (model, cols) in candidates.items():
        model.fit(X.iloc[tr][cols], y.iloc[tr])
        p = model.predict_proba(X.iloc[te][cols])[:, 1]
        rows.append({"model": name, **_scores(y.iloc[te], p)})
        fitted[name] = (model, cols)
    sb = shots["shot_statsbomb_xg"].astype(float).iloc[te]
    rows.append({"model": "StatsBomb xG (professional)", **_scores(y.iloc[te], sb)})
    table = pd.DataFrame(rows).set_index("model")
    table.attrs["test_shots"] = len(te)
    return table, fitted


def train_final(events: pd.DataFrame, fitted: dict, model_name: str) -> tuple:
    """Refit the chosen model on every shot so player metrics use all the data."""
    shots = non_penalty_shots(events)
    X = shot_features(shots)
    y = (shots["shot_outcome"] == "Goal").astype(int)
    model, cols = fitted[model_name]
    model.fit(X[cols], y)
    return model, cols


def predict_xg(shots: pd.DataFrame, model, cols: list[str]) -> pd.Series:
    return pd.Series(model.predict_proba(shot_features(shots)[cols])[:, 1], index=shots.index)


if __name__ == "__main__":
    import joblib

    from pipeline.config import PROCESSED
    from pipeline.ingest_statsbomb import downloaded_leagues, load_events

    leagues = downloaded_leagues()
    events = load_events(leagues, columns=SHOT_COLUMNS, types=["Shot"])
    print(f"loaded {len(events):,} shots from {', '.join(leagues)}")

    table, fitted = evaluate(events)
    print(f"\nxG models on held-out matches ({table.attrs['test_shots']:,} non-penalty shots)")
    print(table.round(4).to_string())

    best = table.drop(index="StatsBomb xG (professional)")["log_loss"].idxmin()
    print(f"\nbest model: {best}")
    model, cols = train_final(events, fitted, best)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "columns": cols, "name": best}, PROCESSED / "xg_model.joblib")
    table.round(4).to_csv(PROCESSED / "xg_model_report.csv")
    print(f"saved model to {PROCESSED / 'xg_model.joblib'}")
