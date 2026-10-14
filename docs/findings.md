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

## Week 2 log

**xG with freeze frames.** Five leagues, 38,728 shots, 20% of matches held out (7,554 non-penalty shots).

| Model | Log loss | Brier | AUC |
| --- | --- | --- | --- |
| Distance only | 0.2806 | 0.0803 | 0.757 |
| Week 1 logistic | 0.2678 | 0.0763 | 0.788 |
| Week 2 logistic + freeze frame | 0.2580 | 0.0742 | 0.812 |
| Week 2 gradient boosting + freeze frame | **0.2541** | 0.0730 | 0.820 |
| StatsBomb xG (professional) | 0.2513 | 0.0717 | 0.824 |

Freeze frames closed about 83% of the gap to StatsBomb (0.0165 down to 0.0028 log loss).

**xT grid.** The most valuable zone is right in front of goal (0.29). Value climbs slowly through midfield and jumps inside the box. See `data/processed/xt_heatmap.png`.

**Player table.** 1,355 players with 900+ minutes in the four full leagues. Top three by xT per 90 are Neymar (0.42), Di María (0.41) and Messi (0.41).

**Sanity checks.** Two teams' minutes add up to about 2,047 per match (2 x 11 players x about 93 minutes). Messi had 23 non-penalty La Liga goals, which matches his real 26 minus 3 penalties.
