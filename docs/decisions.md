# Design decisions

Write one short entry each time you make a real choice. Interviewers love this file.

| Date | Decision | Why | Alternatives considered |
| --- | --- | --- | --- |
| 2026-10-13 | Use the 2015/16 Big 5 season | Only full-league season in StatsBomb open data, and it allows a 2-year backtest | Recent tournaments (too few matches per player) |
| 2026-10-13 | FastAPI instead of Express | The pipeline is Python, so one language for data and API | Express + Prisma |
| 2026-10-13 | Download with 4 threads and retries | GitHub rate limits (HTTP 429) broke faster downloads | Sequential download (about 3x slower) |
| 2026-10-13 | Store nested event columns (freeze frames, tactics) as JSON text in parquet | Parquet needs one type per column | Pickle files (not portable) |
