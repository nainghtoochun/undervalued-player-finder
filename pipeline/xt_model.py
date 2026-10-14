"""Expected Threat (xT), following Karun Singh's grid approach.

The pitch is split into a 16 x 12 grid. xT of a zone is the chance that
possession in that zone leads to a goal within the next few actions.
A pass or carry is worth xT(end zone) - xT(start zone).
"""
import numpy as np
import pandas as pd

from pipeline.config import PITCH_X, PITCH_Y

NX, NY = 16, 12


def zone(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    xi = np.clip((np.asarray(x) / PITCH_X * NX).astype(int), 0, NX - 1)
    yi = np.clip((np.asarray(y) / PITCH_Y * NY).astype(int), 0, NY - 1)
    return yi * NX + xi


def fit_xt(events: pd.DataFrame, n_iter: int = 30) -> np.ndarray:
    n = NX * NY
    shots = events[events["type"] == "Shot"]
    passes = events[(events["type"] == "Pass") & events["pass_outcome"].isna()]
    carries = events[events["type"] == "Carry"]
    failed = events[(events["type"] == "Pass") & events["pass_outcome"].notna()]

    def start_zones(df):
        xy = np.vstack(df["location"].to_numpy())
        return zone(xy[:, 0], xy[:, 1])

    shot_z = start_zones(shots)
    goal = (shots["shot_outcome"] == "Goal").to_numpy()
    move_start = np.concatenate([start_zones(passes), start_zones(carries)])
    end_xy = np.vstack(list(passes["pass_end_location"]) + list(carries["carry_end_location"]))
    move_end = zone(end_xy[:, 0], end_xy[:, 1])
    fail_z = start_zones(failed)

    shot_count = np.bincount(shot_z, minlength=n)
    goal_count = np.bincount(shot_z[goal], minlength=n)
    move_count = np.bincount(move_start, minlength=n)
    fail_count = np.bincount(fail_z, minlength=n)
    total = shot_count + move_count + fail_count

    with np.errstate(divide="ignore", invalid="ignore"):
        p_shot = np.nan_to_num(shot_count / total)
        p_move = np.nan_to_num(move_count / total)
        p_goal = np.nan_to_num(goal_count / shot_count)

    T = np.zeros((n, n))
    np.add.at(T, (move_start, move_end), 1)
    row_sum = T.sum(axis=1, keepdims=True)
    T = np.divide(T, row_sum, out=np.zeros_like(T), where=row_sum > 0)

    xt = np.zeros(n)
    for _ in range(n_iter):
        xt = p_shot * p_goal + p_move * (T @ xt)
    return xt.reshape(NY, NX)


def action_xt(df: pd.DataFrame, end_col: str, grid: np.ndarray) -> pd.Series:
    """xT added by each successful pass or carry in df."""
    flat = grid.ravel()
    s = np.vstack(df["location"].to_numpy())
    e = np.vstack(df[end_col].to_numpy())
    return pd.Series(flat[zone(e[:, 0], e[:, 1])] - flat[zone(s[:, 0], s[:, 1])], index=df.index)
