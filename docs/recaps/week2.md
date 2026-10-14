# Week 2 Recap: Models and metrics

**Dates** Oct 14, 2026 (planned for Oct 20 to Oct 26, done early)
**Status** Done. 15 tests pass.

## Week 2 in plain words
Week 1 built a kitchen and cooked one dish. Week 2 turned it into a full menu.

- **More ingredients.** We now have all five leagues, about 5.4 million events.
- **A smarter xG model.** Week 1 only knew *where* a shot was taken. Now it also sees a snapshot of every player at the moment of the shot (a "freeze frame"). So it knows if three defenders were in the way or the keeper was out of position. That made it almost as good as StatsBomb's professional model.
- **A map of danger (xT).** We split the pitch into 192 boxes and worked out how likely a goal is to come soon from each box. Right in front of goal is worth 0.29. Your own box is worth almost nothing. Now every pass or dribble gets a score for how much it moved the ball into danger.
- **A stat sheet for every player.** For each player we worked out minutes played, then per 90 minutes their xG (chances they got), xA (chances they created) and xT (how much they moved the ball into danger).
- **Tests.** 13 new automatic checks make sure the maths stays right when the code changes.

## What I finished
- [x] Downloaded all five leagues
- [x] Added freeze-frame features to xG and compared four models
- [x] Fitted the xT grid and drew it as a heatmap
- [x] Built per 90 player stats (minutes, npxG, xA, xT)
- [x] Wrote tests for minutes played, per 90 maths, positions and freeze frames

## Results
| xG model | Log loss (lower is better) | AUC (higher is better) |
| --- | --- | --- |
| Distance only | 0.2806 | 0.757 |
| Week 1 logistic | 0.2678 | 0.788 |
| Week 2 logistic + freeze frame | 0.2580 | 0.812 |
| Week 2 gradient boosting + freeze frame | **0.2541** | 0.820 |
| StatsBomb xG (professional) | 0.2513 | 0.824 |

Freeze frames closed about **83%** of the gap to the professional model.

**Player table.** 1,355 players with 900+ minutes. Top three by xT per 90 are Neymar (0.42), Di María (0.41) and Messi (0.41).

**Sanity checks.** Messi has 26 La Liga goals in the data (19 open play, 4 free kicks, 3 penalties), matching his real season. Two teams' minutes add up to about 2,047 per match, which is 22 players for about 93 minutes.

## What went wrong and how we fixed it
| # | Problem | What happened | Fix | Lesson |
| --- | --- | --- | --- | --- |
| 1 | Premier League data lost three columns | When shrinking the file for the laptop, already-converted text got treated as missing and wiped (freeze frames, lineups, related events) | Code now keeps text that is already JSON. Re-downloaded the Premier League | Check the data after every transformation, not just the first time |
| 2 | Bundesliga was not a full season | The free data only has Bayer Leverkusen's 34 matches | Use it to train xG and xT, but leave it out of the player table | Count what you actually downloaded before trusting the plan |
| 3 | Downloads were slow and one crashed | GitHub rate limits, plus two downloads at once ran out of memory | Ran them one at a time, with retries | Big jobs one at a time, and watch memory |
| 4 | All the data would not fit in memory | 5 leagues x 120 columns is far too big for a laptop | Each step loads only the columns and event types it needs | Load less, not more |
| 5 | The Week 1 notebook broke | The xG code changed shape | Updated the notebook and re-ran it | When you change shared code, re-run everything that uses it |

## Things I learned
- How freeze frames turn a simple model into a strong one
- What Expected Threat is and why it rewards passers and dribblers, not just scorers
- How to work out minutes played from raw events (subs, red cards, injuries)
- Why you compare several models on held-out matches before picking one

## Interview story from this week
"I found that the free Bundesliga data only covered one club, so I kept it for training the models but left it out of the player rankings. That way I didn't compare one team's players against nobody. I wrote the decision down with the reason."

## Next up (Week 3, Oct 27 to Nov 2)
- [ ] Download Transfermarkt market values
- [ ] Match players between StatsBomb and Transfermarkt
- [ ] Build the value model and find the biggest gaps
- [ ] Run the backtest: did the flagged players' values rise by 2018?
- [ ] Install Docker and load everything into Postgres
