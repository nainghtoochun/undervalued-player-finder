# Design decisions

Write one short entry each time you make a real choice. Interviewers love this file.

| Date | Decision | Why | Alternatives considered |
| --- | --- | --- | --- |
| 2026-10-13 | Use the 2015/16 Big 5 season | Only full-league season in StatsBomb open data, and it allows a 2-year backtest | Recent tournaments (too few matches per player) |
| 2026-10-13 | FastAPI instead of Express | The pipeline is Python, so one language for data and API | Express + Prisma |
| 2026-10-13 | Download with 4 threads and retries | GitHub rate limits (HTTP 429) broke faster downloads | Sequential download (about 3x slower) |
| 2026-10-13 | Store nested event columns (freeze frames, tactics) as JSON text in parquet | Parquet needs one type per column | Pickle files (not portable) |
| 2026-10-14 | Leave the Bundesliga out of the player table | StatsBomb open data has only Bayer Leverkusen's 34 Bundesliga matches for 2015/16 | Keep it (unfair to every other Bundesliga club) |
| 2026-10-14 | Still train xG and xT on all five leagues | More shots and passes make both models steadier | Four leagues only |
| 2026-10-14 | Gradient boosting for the final xG model | Best held-out log loss (0.2541 vs 0.2580 for logistic) | Logistic regression (easier to explain, kept for comparison) |
| 2026-10-14 | Minutes played worked out from events (lineups, subs, red cards, injuries) | Everything needed is already in the event data, no extra download | StatsBomb lineups endpoint (one extra request per match) |
| 2026-10-14 | xT counts only successful open play passes and carries | Corners and free kicks would credit set-piece takers for dead-ball positions | All passes |
| 2026-10-14 | Load only the columns and event types each step needs | All leagues with every column do not fit in laptop memory | Load everything (crashed the cloud download once) |
| 2026-10-14 | Match players inside each club, using nicknames from StatsBomb lineups | Event data has full legal names ("Jorge Resurrección Merodio") while Transfermarkt uses "Koke". Nicknames took the match rate from 94.7% to 99.9% | Matching on names alone |
| 2026-10-14 | Pair clubs by shared players, not just names | AC Milan and Inter Milan look the same once "AC" is removed, and names alone swapped them | Club names only |
| 2026-10-14 | Give each StatsBomb club one name by team id | StatsBomb spells Marseille and Caen two ways | Leave as is (split those squads in two) |
| 2026-10-14 | Club is not a value model feature, except relegation | A great season at a small club is the signal we want. Relegated players drop a division, which the market rightly prices in | Add club strength (would hide the bargains) |
| 2026-10-14 | Out-of-fold predictions for the value gap | A model that saw a player's price would just copy it | In-sample predictions |
| 2026-10-14 | Ridge regression for fair value | Higher cross-validated R2 than gradient boosting (0.62 vs 0.60) and easy to explain | Gradient boosting |
| 2026-10-14 | Judge the backtest after age, position, league and starting price | Young and cheap players rise anyway, so raw growth would flatter the model | Raw value growth only |
| 2026-10-14 | Leave goalkeepers out of the value model | xG, xA and xT say little about keepers | Keep them (noise) |
| 2026-10-19 | Publish the website as a static site on GitHub Pages, reading exported JSON | The data is one finished season, so a live database adds cost and a 30 to 60 second cold start on free hosts. A static site is free, instant and never sleeps | Render (API) + Neon (Postgres) + Vercel (web) |
| 2026-10-19 | Keep the FastAPI + Postgres backend, tested in CI against a real Postgres | Shows backend skills and serves the same fields as the site, for anyone running the full stack | Drop the API |
| 2026-10-19 | API tests use a separate `upf_test` database | Tests must never wipe the real data | Mock the database (would not test the SQL) |
| 2026-10-19 | HashRouter for page links | GitHub Pages cannot route deep links like /player/123 on its own | Custom 404 redirect trick |
