"""Expected Threat (xT), following Karun Singh's grid approach.

The pitch is split into a 16 x 12 grid. xT of a zone is the chance that
having the ball there leads to a goal within the next few actions.
A pass or carry is worth xT(end zone) - xT(start zone).

Counting is split from solving so we can count one league at a time
(less memory) and solve once on the combined counts.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from pipeline.config import PITCH_X, PITCH_Y

NX, NY = 16, 12
N = NX * NY
XT_COLUMNS = ["type", "location", "pass_end_location", "carry_end_location", "pass_outcome",
              "shot_type", "shot_outcome"]


def zone(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    xi = np.clip((np.asarray(x) / PITCH_X * NX).astype(int), 0, NX - 1)
    yi = np.clip((np.asarray(y) / PITCH_Y * NY).astype(int), 0, NY - 1)
    return yi * NX + xi


def _zones(col: pd.Series) -> np.ndarray:
    if len(col) == 0:
        return np.zeros(0, dtype=int)
    xy = np.vstack(col.to_numpy())
    return zone(xy[:, 0], xy[:, 1])


@dataclass
class XTCounts:
    shots: np.ndarray = field(default_factory=lambda: np.zeros(N))
    goals: np.ndarray = field(default_factory=lambda: np.zeros(N))
    moves: np.ndarray = field(default_factory=lambda: np.zeros(N))
    fails: np.ndarray = field(default_factory=lambda: np.zeros(N))
    transitions: np.ndarray = field(default_factory=lambda: np.zeros((N, N)))

    def add(self, other: "XTCounts") -> "XTCounts":
        return XTCounts(self.shots + other.shots, self.goals + other.goals, self.moves + other.moves,
                        self.fails + other.fails, self.transitions + other.transitions)


def count_actions(events: pd.DataFrame) -> XTCounts:
    shots = events[(events["type"] == "Shot") & (events["shot_type"] != "Penalty")]
    passes = events[(events["type"] == "Pass") & events["pass_outcome"].isna()]
    carries = events[events["type"] == "Carry"]
    failed = events[(events["type"] == "Pass") & events["pass_outcome"].notna()]

    shot_z = _zones(shots["location"])
    goal = (shots["shot_outcome"] == "Goal").to_numpy()
    move_start = np.concatenate([_zones(passes["location"]), _zones(carries["location"])])
    move_end = np.concatenate([_zones(passes["pass_end_location"]), _zones(carries["carry_end_location"])])

    c = XTCounts()
    c.shots = np.bincount(shot_z, minlength=N).astype(float)
    c.goals = np.bincount(shot_z[goal], minlength=N).astype(float)
    c.moves = np.bincount(move_start, minlength=N).astype(float)
    c.fails = np.bincount(_zones(failed["location"]), minlength=N).astype(float)
    np.add.at(c.transitions, (move_start, move_end), 1)
    return c


def solve_xt(c: XTCounts, n_iter: int = 50) -> np.ndarray:
    total = c.shots + c.moves + c.fails
    with np.errstate(divide="ignore", invalid="ignore"):
        p_shot = np.nan_to_num(c.shots / total)
        p_move = np.nan_to_num(c.moves / total)
        p_goal = np.nan_to_num(c.goals / c.shots)
    row_sum = c.transitions.sum(axis=1, keepdims=True)
    T = np.divide(c.transitions, row_sum, out=np.zeros_like(c.transitions), where=row_sum > 0)

    xt = np.zeros(N)
    for _ in range(n_iter):
        xt = p_shot * p_goal + p_move * (T @ xt)
    return xt.reshape(NY, NX)


def fit_xt(events: pd.DataFrame, n_iter: int = 50) -> np.ndarray:
    return solve_xt(count_actions(events), n_iter)


def action_xt(df: pd.DataFrame, end_col: str, grid: np.ndarray) -> pd.Series:
    """xT added by each pass or carry in df (end zone value minus start zone value)."""
    if len(df) == 0:
        return pd.Series(dtype=float)
    flat = grid.ravel()
    return pd.Series(flat[_zones(df[end_col])] - flat[_zones(df["location"])], index=df.index)


def plot_xt(grid: np.ndarray, path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mplsoccer import Pitch

    pitch = Pitch(pitch_type="statsbomb", line_color="#222", line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 6.8))
    bins = pitch.bin_statistic(np.array([0.0]), np.array([0.0]), bins=(NX, NY))
    bins["statistic"] = grid
    hm = pitch.heatmap(bins, ax=ax, cmap="Blues", edgecolors="white")
    pitch.label_heatmap(bins, ax=ax, str_format="{:.2f}", fontsize=7, color="#222",
                        ha="center", va="center", exclude_zeros=False)
    fig.colorbar(hm, ax=ax, fraction=0.03, pad=0.02, label="xT (chance of a goal soon)")
    ax.set_title("Expected Threat by zone, attacking left to right", fontsize=13)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
