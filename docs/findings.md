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

## Week 3 log

**Matching.** 1,353 of 1,355 regular players (99.9%) linked to Transfermarkt. Players who changed league in January matched to the same Transfermarkt id in both leagues, a good sign the matching is right.

**Fair value model.** 1,249 outfield players with a summer 2016 market value. Ridge regression, 5-fold out-of-fold predictions.

| Model | R2 on log value | Median price error |
| --- | --- | --- |
| Ridge (chosen) | 0.620 | 49% |
| Gradient boosting | 0.601 | 49% |

**Backtest, summer 2016 to summer 2018.** Top 50 by value gap against everyone else (1,180 players with a 2018 value; 4 of the top 50 had none).

| Group | Median value change | Share whose value rose |
| --- | --- | --- |
| Top 50 flagged | +21% | 54% |
| Everyone else | -17% | 35% |

After accounting for age, position, league and starting price, flagged players gained **+47% more** value (95% bootstrap range +19% to +81%). The effect gets stronger as the list gets shorter (top 25 +73%, top 100 +25%, top 200 +18%), and it rises steadily across the five value gap groups. See `data/processed/backtest.png`.

**Hits.** Luis Alberto (Deportivo, EUR 4m to EUR 35m), Roberto Inglese (Chievo, EUR 1m to EUR 10m), Cristiano Piccini (Betis, EUR 0.7m to EUR 7.5m).
**Misses.** Older players the model likes, like Massimo Gobbi (35), whose value kept falling.

**Limitations.**
- Market values are Transfermarkt estimates, not transfer fees.
- Part of the effect may be prices that were simply too low by chance moving back up. Controlling for starting price reduces but does not remove this.
- One season of stats, so a lucky season can look like a bargain.
- Spearman correlation between value gap and extra growth across all players is only 0.10. The signal is in the extreme tail, not everywhere.
