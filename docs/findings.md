# Findings

Fill this in during week 4. This becomes the blog post and the README highlight.

1. How good is our xG model compared with StatsBomb's?
2. What does the xT grid look like, and which zones matter most?
3. Top 10 undervalued players by position.
4. Backtest result. Did the flagged players gain more value two years later?
5. Limitations.

## Week 1 log

First xG model (logistic regression on distance, angle, header, under pressure, first time), Premier League 2015/16, open-play shots, 20% of matches held out (1,931 shots).

| Model | Log loss (lower is better) | Brier | AUC |
| --- | --- | --- | --- |
| Distance only | 0.2962 | | |
| Ours, week 1 | 0.2859 | 0.0811 | 0.742 |
| StatsBomb xG | 0.2669 | 0.0755 | 0.792 |

Sanity check. Jamie Vardy had 17.6 non-penalty xG and 19 non-penalty goals, matching his real 24 goals minus 5 penalties.
Next step. Freeze-frame features to close the gap with StatsBomb.
