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
