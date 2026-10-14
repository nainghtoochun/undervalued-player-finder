"""Expected goals model trained on StatsBomb shots.

Goal: beat a distance-only baseline and land close to StatsBomb's own xG
on log loss and calibration.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from pipeline.config import GOAL_X, GOAL_Y, POST_HIGH_Y, POST_LOW_Y


def shot_features(shots: pd.DataFrame) -> pd.DataFrame:
    xy = np.vstack(shots["location"].to_numpy())
    x, y = xy[:, 0], xy[:, 1]
    dx, dy = GOAL_X - x, GOAL_Y - y
    distance = np.hypot(dx, dy)
    # angle the goal mouth covers from the shot location
    a1 = np.arctan2(POST_LOW_Y - y, GOAL_X - x)
    a2 = np.arctan2(POST_HIGH_Y - y, GOAL_X - x)
    angle = np.abs(a2 - a1)
    feats = pd.DataFrame({
        "distance": distance,
        "angle": angle,
        "is_header": (shots["shot_body_part"] == "Head").astype(int),
        "under_pressure": shots["under_pressure"].fillna(False).astype(int),
        "first_time": shots.get("shot_first_time", pd.Series(False, index=shots.index)).fillna(False).astype(int),
    }, index=shots.index)
    # TODO week 2: add freeze-frame features (defenders between ball and goal, keeper distance)
    return feats


def train(events: pd.DataFrame):
    shots = events[(events["type"] == "Shot") & (events["shot_type"] == "Open Play")].copy()
    X = shot_features(shots)
    y = (shots["shot_outcome"] == "Goal").astype(int)

    split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(split.split(X, y, groups=shots["match_id"]))
    model = LogisticRegression(max_iter=1000).fit(X.iloc[tr], y.iloc[tr])

    p = model.predict_proba(X.iloc[te])[:, 1]
    sb_xg = shots["shot_statsbomb_xg"].astype(float).iloc[te]
    baseline = LogisticRegression(max_iter=1000).fit(X.iloc[tr][["distance"]], y.iloc[tr])
    p_base = baseline.predict_proba(X.iloc[te][["distance"]])[:, 1]
    report = {
        "test_shots": len(te),
        "goal_rate": float(y.iloc[te].mean()),
        "distance_only_log_loss": log_loss(y.iloc[te], p_base),
        "ours_log_loss": log_loss(y.iloc[te], p),
        "statsbomb_log_loss": log_loss(y.iloc[te], sb_xg),
        "ours_brier": brier_score_loss(y.iloc[te], p),
        "statsbomb_brier": brier_score_loss(y.iloc[te], sb_xg),
        "ours_auc": roc_auc_score(y.iloc[te], p),
        "statsbomb_auc": roc_auc_score(y.iloc[te], sb_xg),
    }
    return model, report


if __name__ == "__main__":
    import joblib

    from pipeline.config import PROCESSED
    from pipeline.ingest_statsbomb import load_events

    events = load_events()
    print(f"loaded {len(events):,} events from {events['league'].nunique()} league(s)")
    model, report = train(events)
    print("\nxG model report (held-out matches, open-play shots)")
    for k, v in report.items():
        print(f"  {k:<24} {v:.4f}" if isinstance(v, float) else f"  {k:<24} {v}")
    print("\ncoefficients")
    for name, coef in zip(model.feature_names_in_, model.coef_[0]):
        print(f"  {name:<15} {coef:+.3f}")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, PROCESSED / "xg_model.joblib")
    print(f"\nsaved model to {PROCESSED / 'xg_model.joblib'}")
