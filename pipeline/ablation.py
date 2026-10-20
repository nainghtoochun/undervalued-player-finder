"""Do xG, xA and xT actually help find bargains? An honest check of the headline.

Run: python -m pipeline.ablation   (after python -m pipeline.value_model)

The value model uses advanced stats (xG, xA, xT) plus simple facts (minutes,
age, position, league, relegation). This script rebuilds the fair value with
fewer inputs and runs the same 2016 to 2018 backtest on each version:

1. full model                  advanced stats + simple facts
2. no advanced stats           minutes, age, position, league, relegation
3. no stats at all             age, position, league, relegation
4. placebo                     a random ranking

Then a fairer test of the stats themselves. Among players the simple model
rates the same, do the ones with better xG, xA and xT rise more?
"stats premium" = log(full fair value) - log(simple fair value), the part of a
player's fair value that comes only from his advanced stats.
"""
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from pipeline.config import PROCESSED
from pipeline.value_model import NUMERIC, backtest, build_dataset, expected_growth_residual, fit_value_model

VARIANTS = {
    "Full model (xG, xA, xT + minutes, age, position, league)": NUMERIC,
    "No xG, xA or xT (minutes, age, position, league)": ["minutes", "age", "age_sq", "relegated"],
    "No stats at all (age, position, league)": ["age", "age_sq", "relegated"],
}
TOP_NS = (25, 50, 100)


def _ratio(log_value: float) -> float:
    return float(np.exp(log_value) - 1)


def variant_table(data: pd.DataFrame, n_boot: int = 2000) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    rows, scored_by = [], {}
    for label, numeric in VARIANTS.items():
        scored, report = fit_value_model(data, numeric=numeric, models=("ridge",))
        scored_by[label] = scored
        row = {"inputs": label, "r2_log_value": report["ridge"]["r2_log_value"]}
        for n in TOP_NS:
            b, _ = backtest(scored, top_n=n, n_boot=n_boot)
            row[f"top{n}_extra"] = _ratio(b["extra_growth_log_top_minus_rest"])
            row[f"top{n}_low"], row[f"top{n}_high"] = (_ratio(x) for x in b["extra_growth_ci95"])
        rows.append(row)

    placebo = data.assign(log_gap=np.random.default_rng(1).normal(size=len(data)))
    row = {"inputs": "Random ranking (placebo)", "r2_log_value": np.nan}
    for n in TOP_NS:
        b, _ = backtest(placebo, top_n=n, n_boot=n_boot)
        row[f"top{n}_extra"] = _ratio(b["extra_growth_log_top_minus_rest"])
        row[f"top{n}_low"], row[f"top{n}_high"] = (_ratio(x) for x in b["extra_growth_ci95"])
    rows.append(row)
    return pd.DataFrame(rows), scored_by


def stats_premium_test(full: pd.DataFrame, simple: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> dict:
    """Does the part of fair value that comes from xG, xA and xT predict extra growth,
    once the simple model's gap is known?"""
    df = full[["player_id", "log_gap", "predicted_value_eur", "value_2016", "value_2018", "age", "age_sq",
               "position_group", "league"]].merge(
        simple[["player_id", "log_gap", "predicted_value_eur"]].rename(
            columns={"log_gap": "simple_gap", "predicted_value_eur": "simple_value"}), on="player_id")
    df = df[df["value_2018"].notna() & (df["value_2018"] > 0)].copy()
    df["stats_premium"] = np.log(df["predicted_value_eur"] / df["simple_value"])
    df["extra_growth"] = expected_growth_residual(df)

    X = df[["simple_gap", "stats_premium"]].to_numpy()
    y = df["extra_growth"].to_numpy()
    coef = LinearRegression().fit(X, y).coef_[1]
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n_boot):
        i = rng.integers(0, len(df), len(df))
        boot.append(LinearRegression().fit(X[i], y[i]).coef_[1])
    lo, hi = np.percentile(boot, [2.5, 97.5])

    # same idea without a regression: inside each fifth of the simple gap,
    # compare players with high vs low stats premium
    df["simple_fifth"] = pd.qcut(df["simple_gap"], 5, labels=False)
    df["high_premium"] = df.groupby("simple_fifth")["stats_premium"].transform(lambda s: s > s.median())
    by_half = df.groupby("high_premium")["extra_growth"].mean()

    return {
        "players": int(len(df)),
        # extra growth for a stats premium of +0.5 (fair value about 65% higher from the stats alone)
        "extra_growth_per_half_log_premium": _ratio(0.5 * coef),
        "ci95": [_ratio(0.5 * lo), _ratio(0.5 * hi)],
        "high_minus_low_premium_within_fifths": _ratio(by_half.get(True, 0) - by_half.get(False, 0)),
    }


if __name__ == "__main__":
    data = build_dataset()
    table, scored_by = variant_table(data)
    labels = list(VARIANTS)
    premium = stats_premium_test(scored_by[labels[0]], scored_by[labels[1]])

    pd.set_option("display.width", 160)
    show = table.copy()
    for c in show.columns[2:]:
        show[c] = show[c].map(lambda v: f"{v:+.0%}")
    print("Same backtest, fair value built from different inputs:\n")
    print(show[["inputs", "r2_log_value", "top25_extra", "top50_extra", "top50_low", "top50_high", "top100_extra"]]
          .round(2).to_string(index=False))
    lo, hi = premium["ci95"]
    print(f"\nStats premium test ({premium['players']} players): among players the simple model rates the same, "
          f"a +0.5 log stats premium goes with {premium['extra_growth_per_half_log_premium']:+.0%} extra growth "
          f"(95% range {lo:+.0%} to {hi:+.0%}).")
    print(f"High vs low stats premium inside each simple-gap fifth: "
          f"{premium['high_minus_low_premium_within_fifths']:+.0%} extra growth.")

    table.to_csv(PROCESSED / "ablation.csv", index=False)
    (PROCESSED / "ablation.json").write_text(json.dumps(
        {"variants": table.replace({np.nan: None}).to_dict(orient="records"), "stats_premium": premium}, indent=2))
