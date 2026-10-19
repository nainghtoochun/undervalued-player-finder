"""Fair value model and the 2016 to 2018 backtest.

Idea. Predict what a player "should" cost from what he did on the pitch
(xG, xA, xT per 90, minutes), his age, position and league. If the market
price is far below that prediction, he may be undervalued.

Two rules keep this honest.
- Predictions are out of fold (5-fold cross validation). Each player's fair
  value comes from a model that never saw his own price.
- The club is NOT a feature. A great season at a small club is exactly the
  signal we are looking for, so we must not explain it away. The one club fact
  we do use is relegation: those players drop a division next season, and the
  market rightly prices that in.

The backtest then asks: two summers later, did the players we flagged
gain more value than similar players (same age, position, league, price)?

Run: python -m pipeline.value_model   (after python -m pipeline.match_players)
"""
import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from pipeline.config import (
    BACKTEST_DATE,
    BACKTEST_WINDOW_START,
    PROCESSED,
    RAW_TM,
    VALUATION_DATE,
    VALUATION_WINDOW_START,
)

PERFORMANCE = ["npxg_p90", "xa_p90", "xt_pass_p90", "xt_carry_p90", "np_shots_p90", "minutes"]
NUMERIC = PERFORMANCE + ["age", "age_sq", "relegated"]
CATEGORICAL = ["position_group", "league"]
TOP_N = 50


# ---------- data ----------

def value_at(valuations: pd.DataFrame, start: str, end: str, name: str) -> pd.Series:
    """Each player's latest market value between start and end (inclusive)."""
    v = valuations[(valuations["date"] >= start) & (valuations["date"] <= end)]
    latest = v.sort_values("date").groupby("player_id")["market_value_in_eur"].last()
    return latest.rename(name)


def relegated_teams() -> set[str]:
    """StatsBomb team names of the bottom three clubs in each league, from the results."""
    from pipeline.match_players import TM_LEAGUES, TM_SEASON

    g = pd.read_csv(RAW_TM / "games.csv.gz", usecols=[
        "competition_id", "season", "home_club_id", "away_club_id", "home_club_goals", "away_club_goals"])
    g = g[(g["season"] == TM_SEASON) & g["competition_id"].isin(TM_LEAGUES.values())]
    diff = g["home_club_goals"] - g["away_club_goals"]
    home = pd.DataFrame({"comp": g["competition_id"], "club": g["home_club_id"], "gd": diff,
                         "pts": np.select([diff > 0, diff == 0], [3, 1], 0)})
    away = pd.DataFrame({"comp": g["competition_id"], "club": g["away_club_id"], "gd": -diff,
                         "pts": np.select([diff < 0, diff == 0], [3, 1], 0)})
    table = pd.concat([home, away]).groupby(["comp", "club"])[["pts", "gd"]].sum().reset_index()
    bottom = table.sort_values(["pts", "gd"]).groupby("comp").head(3)["club"]
    clubs = pd.read_csv(PROCESSED / "club_matches.csv")
    return set(clubs.loc[clubs["tm_club_id"].isin(bottom), "team"])


def build_dataset() -> pd.DataFrame:
    metrics = pd.read_parquet(PROCESSED / "player_season_metrics.parquet")
    matches = pd.read_csv(PROCESSED / "player_matches.csv").drop_duplicates("player_id")
    players = pd.read_csv(RAW_TM / "players.csv.gz", usecols=["player_id", "date_of_birth"],
                          parse_dates=["date_of_birth"]).rename(columns={"player_id": "tm_player_id"})
    vals = pd.read_csv(RAW_TM / "player_valuations.csv.gz", usecols=["player_id", "date", "market_value_in_eur"])

    df = metrics[metrics["position_group"].isin(["DEF", "MID", "FWD"])]  # keepers need different stats
    # a player who changed league in January keeps his longer spell
    df = df.sort_values("minutes", ascending=False).drop_duplicates("player_id")
    df = df.merge(matches[["player_id", "tm_player_id"]], on="player_id", how="inner")
    df = df.merge(players, on="tm_player_id", how="left")
    df = df.merge(value_at(vals, VALUATION_WINDOW_START, VALUATION_DATE, "value_2016"),
                  left_on="tm_player_id", right_index=True, how="inner")
    df = df.merge(value_at(vals, BACKTEST_WINDOW_START, BACKTEST_DATE, "value_2018"),
                  left_on="tm_player_id", right_index=True, how="left")
    df = df[df["value_2016"] > 0]
    df["relegated"] = df["team"].isin(relegated_teams()).astype(int)

    season_end = pd.Timestamp("2016-07-01")
    df["age"] = (season_end - df["date_of_birth"]).dt.days / 365.25
    df["age"] = df["age"].fillna(df["age"].median())
    df["age_sq"] = df["age"] ** 2
    return df.reset_index(drop=True)


# ---------- model ----------

def _prep(scale: bool) -> ColumnTransformer:
    num = StandardScaler() if scale else "passthrough"
    return ColumnTransformer([("num", num, NUMERIC),
                              ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)])


def candidate_models() -> dict:
    return {
        "ridge": make_pipeline(_prep(scale=True), RidgeCV(alphas=np.logspace(-2, 3, 20))),
        "gradient boosting": make_pipeline(_prep(scale=False), HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=20,
            l2_regularization=1.0, random_state=0)),
    }


def fit_value_model(df: pd.DataFrame, seed: int = 0) -> tuple[pd.DataFrame, dict]:
    """Out-of-fold fair value for every player. Returns the scored table and a report."""
    X, y = df[NUMERIC + CATEGORICAL], np.log(df["value_2016"])
    folds = KFold(n_splits=5, shuffle=True, random_state=seed)
    report, preds = {}, {}
    for name, model in candidate_models().items():
        p = cross_val_predict(model, X, y, cv=folds)
        preds[name] = p
        report[name] = {"r2_log_value": r2_score(y, p), "mae_log_value": mean_absolute_error(y, p),
                        "median_abs_pct_error": float(np.median(np.abs(np.exp(p - y) - 1)))}
    best = max(report, key=lambda k: report[k]["r2_log_value"])
    report["chosen"] = best

    out = df.copy()
    out["predicted_value_eur"] = np.exp(preds[best])
    out["log_gap"] = preds[best] - y            # above 0 = cheaper than the model expects
    out["value_gap_pct"] = np.exp(out["log_gap"]) - 1
    return out.sort_values("log_gap", ascending=False).reset_index(drop=True), report


# ---------- backtest ----------

def expected_growth_residual(df: pd.DataFrame) -> pd.Series:
    """Value growth that age, position, league and starting price do NOT explain.

    Young, cheap players rise anyway, so comparing raw growth would flatter us.
    """
    X = pd.get_dummies(df[["age", "age_sq", "position_group", "league"]].assign(
        log_v16=np.log(df["value_2016"])), columns=["position_group", "league"], drop_first=True, dtype=float)
    growth = np.log(df["value_2018"] / df["value_2016"])
    return growth - LinearRegression().fit(X, growth).predict(X)


def backtest(scored: pd.DataFrame, top_n: int = TOP_N, n_boot: int = 2000, seed: int = 0) -> tuple[dict, pd.DataFrame]:
    has_2018 = scored["value_2018"].notna() & (scored["value_2018"] > 0)
    df = scored[has_2018].copy()
    df["growth"] = df["value_2018"] / df["value_2016"] - 1
    df["growth_log"] = np.log(df["value_2018"] / df["value_2016"])
    df["growth_resid"] = expected_growth_residual(df)
    df["flagged"] = df["log_gap"].rank(ascending=False) <= top_n

    top, rest = df[df["flagged"]], df[~df["flagged"]]
    rng = np.random.default_rng(seed)
    boot = [rng.choice(top["growth_resid"].to_numpy(), len(top)).mean()
            - rng.choice(rest["growth_resid"].to_numpy(), len(rest)).mean() for _ in range(n_boot)]
    lo, hi = np.percentile(boot, [2.5, 97.5])

    df["gap_quintile"] = pd.qcut(df["log_gap"], 5, labels=["1 most overpriced", "2", "3", "4", "5 most underpriced"])
    by_q = df.groupby("gap_quintile", observed=True).agg(
        players=("player_id", "size"), median_growth=("growth", "median"),
        share_rose=("growth", lambda g: (g > 0).mean()), extra_growth_log=("growth_resid", "mean"))

    flagged_all = scored["log_gap"].rank(ascending=False) <= top_n
    summary = {
        "players_scored": int(len(scored)),
        "players_with_2018_value": int(len(df)),
        "top_n": top_n,
        "top_missing_2018_value": int((flagged_all & ~has_2018).sum()),
        "top_median_growth": float(top["growth"].median()),
        "rest_median_growth": float(rest["growth"].median()),
        "top_share_rose": float((top["growth"] > 0).mean()),
        "rest_share_rose": float((rest["growth"] > 0).mean()),
        "extra_growth_log_top_minus_rest": float(top["growth_resid"].mean() - rest["growth_resid"].mean()),
        "extra_growth_ci95": [float(lo), float(hi)],
        "spearman_gap_vs_extra_growth": float(df["log_gap"].corr(df["growth_resid"], method="spearman")),
    }
    return summary, by_q


def plot_backtest(by_q: pd.DataFrame, path) -> None:
    """Bar per value gap quintile: extra value growth after age, position, league and price."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, muted, blue, surface = "#0b0b0b", "#52514e", "#2a78d6", "#fcfcfb"
    pct = (np.exp(by_q["extra_growth_log"]) - 1) * 100
    labels = ["Most\noverpriced", "2", "3", "4", "Most\nunderpriced"]
    fig, ax = plt.subplots(figsize=(8, 4.6), facecolor=surface)
    ax.set_facecolor(surface)
    bars = ax.bar(labels, pct, width=0.6, color=blue)
    ax.axhline(0, color=muted, linewidth=1)
    for b, v in zip(bars, pct):
        ax.annotate("0%" if round(v) == 0 else f"{v:+.0f}%", (b.get_x() + b.get_width() / 2, v),
                    xytext=(0, 4 if v >= 0 else -14), textcoords="offset points",
                    ha="center", fontsize=10, color=ink)
    ax.set_ylabel("Extra value change, 2016 to 2018", color=muted)
    ax.set_xlabel("Players grouped by value gap in summer 2016 (fifths)", color=muted)
    ax.set_title("The cheaper the model said a player was, the more his value rose",
                 loc="left", fontsize=12, color=ink, pad=24)
    ax.text(0, 1.03, "After accounting for age, position, league and starting price", transform=ax.transAxes,
            fontsize=9, color=muted, va="bottom")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(muted)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(colors=muted)
    ax.grid(axis="y", color="#e6e5e1", linewidth=0.8)
    ax.set_axisbelow(True)
    pad = (pct.max() - pct.min()) * 0.12
    ax.set_ylim(min(pct.min(), 0) - pad, max(pct.max(), 0) + pad)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:+.0f}%" if v else "0%"))
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=surface)
    plt.close(fig)


if __name__ == "__main__":
    data = build_dataset()
    print(f"{len(data)} outfield players with stats and a 2016 market value")
    scored, report = fit_value_model(data)
    for name in ("ridge", "gradient boosting"):
        r = report[name]
        print(f"  {name:<18} R2 {r['r2_log_value']:.3f}   median price error {r['median_abs_pct_error']:.0%}")
    print(f"  chosen: {report['chosen']}")

    summary, by_q = backtest(scored)
    print(f"\nBacktest, top {summary['top_n']} by value gap vs everyone else "
          f"({summary['players_with_2018_value']} players with a 2018 value)")
    print(f"  median value change 2016 to 2018: top {summary['top_median_growth']:+.0%}, "
          f"rest {summary['rest_median_growth']:+.0%}")
    print(f"  share whose value rose: top {summary['top_share_rose']:.0%}, rest {summary['rest_share_rose']:.0%}")
    lo, hi = summary["extra_growth_ci95"]
    print(f"  extra growth after age, position, league and price: "
          f"{np.exp(summary['extra_growth_log_top_minus_rest']) - 1:+.0%} "
          f"(95% range {np.exp(lo) - 1:+.0%} to {np.exp(hi) - 1:+.0%})")
    print("\nBy value gap quintile:")
    print(by_q.round(3).to_string())

    show = ["player", "team", "position_group", "age", "value_2016", "predicted_value_eur", "value_gap_pct", "value_2018"]
    print("\nTop 15 possible bargains (summer 2016):")
    print(scored[show].head(15).round({"age": 1, "value_gap_pct": 2}).to_string(index=False))

    scored.to_parquet(PROCESSED / "player_value_scores.parquet")
    scored.to_csv(PROCESSED / "player_value_scores.csv", index=False)
    by_q.to_csv(PROCESSED / "backtest_by_quintile.csv")
    plot_backtest(by_q, PROCESSED / "backtest.png")
    (PROCESSED / "value_model_report.json").write_text(json.dumps({"model": report, "backtest": summary}, indent=2))
