# Undervalued Player Finder Blueprint

Owner NaingHtooChun · Started Oct 13, 2026 · Target finish Nov 9, 2026 (polish by Jan 4, 2027)

## 1. The pitch

A web app that finds soccer players who create more attacking value than their market price suggests. It scores every player in the 2015/16 Big 5 European leagues with my own xG and Expected Threat models, compares that with their Transfermarkt value, and then checks whether the players it flagged really did rise in value two years later.

One line for the resume
> Built a soccer scouting app that scores 1,355 players across four top European leagues with custom xG and Expected Threat models and flags undervalued players, backtested against real market values two years later.

## 2. Why this stands out

- **It answers a real question.** Clubs pay scouts to find exactly this.
- **It has a backtest.** Most student projects never check whether their predictions were right. This one does, using 2018 values.
- **It covers the full stack.** Data pipeline, two models, a database, an API, a frontend, CI and deployment.
- **It's not a tutorial.** Nobody can copy it from YouTube.

## 3. Data

| Source | What I use | How to get it |
| --- | --- | --- |
| StatsBomb open data | Every event (passes, carries, shots) for 2015/16 Premier League, La Liga, Bundesliga, Serie A, Ligue 1 | `statsbombpy` Python library, free, no key needed |
| transfermarkt-datasets (dcaribou) | `players.csv` and `player_valuations.csv` with value history | GitHub or Kaggle ("player-scores"), free CSVs |

Why 2015/16? It is the only recent season with full league coverage in StatsBomb's free data, and it is old enough to check values two years later.

Correction (week 2). The Bundesliga 2015/16 in the free data only has Bayer Leverkusen's 34 matches. The player table uses the four full leagues (Premier League, La Liga, Serie A, Ligue 1). All five are still used to train xG and xT.

## 4. How it works

```
StatsBomb events ──► xG model ──────┐
        │                           ├──► Player metrics per 90 ──┐
        └─────────► xT model ───────┘                            │
                                                                 ├──► Value model ──► Value gap + backtest
Transfermarkt values ──► name matching ──────────────────────────┘                          │
                                                                                            ▼
                                                              Postgres ──► FastAPI ──► React app
```

### 4.1 xG model (expected goals)
- Input is every open-play shot. Features are distance, angle to goal, header or not, under pressure, first time.
- Start with logistic regression. Add freeze-frame features (defenders in the way, keeper position) in week 2.
- Success means my log loss is close to StatsBomb's own xG on a held-out set of matches.

### 4.2 xT model (Expected Threat)
- Split the pitch into a 16 x 12 grid. Each zone gets a value, the chance that having the ball there leads to a goal soon.
- Every successful pass or carry earns xT(end zone) minus xT(start zone).
- This rewards players who move the ball into dangerous areas, not just those who shoot.

### 4.3 Player metrics
- Minutes played from lineups and substitutions. Only players with 900+ minutes count.
- Per 90 minutes, non-penalty xG, expected assists (xA), xT from passes, xT from carries.
- Group by position (DEF, MID, FWD) so defenders are compared with defenders.

### 4.4 Value model and backtest
- Predict log(market value in July 2016) from performance, age, position and league.
- Value gap = (predicted value minus actual value) divided by actual value.
- Backtest. Take the top 50 players by value gap and compare their value change from 2016 to 2018 with similar players who were not flagged.

## 5. Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| Data and models | Python, pandas, NumPy, scikit-learn, mplsoccer | Standard for data science, and mplsoccer draws pitches |
| Database | Postgres 16 (Docker locally, Neon in production) | Real SQL, free hosted tier |
| API | FastAPI | Same language as the pipeline, automatic docs page |
| Frontend | React, Vite, TypeScript, Tailwind, Recharts | Fast to build, looks professional |
| Quality | pytest, ruff, GitHub Actions | Shows engineering habits |
| Hosting | Vercel (web), Render (API), Neon (DB) | Free tiers |

## 6. Folder map

```
undervalued-player-finder/
├── BLUEPRINT.md          this file
├── README.md             public face of the project
├── requirements.txt      Python packages
├── docker-compose.yml    local Postgres
├── .env.example          copy to .env
├── data/raw/             downloaded data (not committed)
├── data/processed/       cleaned tables (not committed)
├── notebooks/            exploration only
├── pipeline/             ingest, xG, xT, metrics, value model
├── api/                  FastAPI app
├── web/                  React app (created in week 4)
├── db/schema.sql         tables
├── tests/                unit tests
├── docs/decisions.md     why I chose what I chose
└── docs/findings.md      results write-up
```

## 7. Four-week plan

Plan on about 10 to 12 hours a week alongside classes.

### Week 1 (Oct 13 to Oct 19) Set up and explore
- [x] Install Python 3.12, Git, VS Code (Docker Desktop moved to week 3, when the database is needed)
- [x] `git init`, push to a public GitHub repo, confirm CI runs green
- [x] Create a virtual environment and install requirements
- [x] Run `python -m pipeline.ingest_statsbomb` (start with one league to test)
- [x] In a notebook, plot shots and passes on a pitch with mplsoccer
- [x] Train the first xG model and print its report
- Done when one league is downloaded and xG runs end to end

### Week 2 (Oct 20 to Oct 26) Models and metrics
- [x] Download all five leagues
- [x] Add freeze-frame features to xG and compare with StatsBomb
- [x] Fit the xT grid and draw it as a heatmap
- [x] Build `player_metrics.py` (minutes, npxG, xA, xT per 90)
- [x] Write tests for minutes played and per 90 maths
- Done when a table of every 900+ minute player with metrics exists

### Week 3 (Oct 27 to Nov 2) Market values and backtest
- [x] Download Transfermarkt CSVs
- [x] Match players by name and club with rapidfuzz, fix misses by hand, record the match rate
- [x] Fit the value model with cross validation
- [x] Run the backtest and write the result in `docs/findings.md`
- [x] Load everything into Postgres
- Done when the backtest number exists, whatever it says

### Week 4 (Nov 3 to Nov 9) Ship it
- [ ] Finish the API endpoints (`/players`, `/players/{id}`, `/bargains`)
- [ ] Build the three pages (Home, Explorer, Player)
- [ ] Deploy DB, API and web
- [ ] README with live link, demo GIF, diagram and key results
- Done when a stranger can open the link and use it

### Polish (Dec 20 to Jan 4)
- [ ] Write a short blog post from `docs/findings.md` and share it on LinkedIn
- [ ] Add the resume bullet with real numbers
- [ ] Ask two friends to use it and fix what confuses them

## 8. Risks and fixes

| Risk | Fix |
| --- | --- |
| Downloading all events is slow | Download one league first, save as parquet, never re-download |
| Names don't match between sources | Fuzzy match within the same club, keep a manual fix file |
| Market values are noisy | Use log value, compare within position groups, say it clearly in limitations |
| Backtest shows no edge | Still report it honestly. A clear negative result is still strong work |
| Running out of time | Cut freeze-frame features and the player heatmap first. Never cut deployment |

## 9. Interview talking points
- Why xT rewards different players than goals and assists do
- How I checked my xG model against a professional one
- How the backtest avoids looking into the future
- One thing that went wrong and how I fixed it (keep notes in `docs/decisions.md`)

## 10. Definition of done
- Live URL works on desktop and phone
- README explains the project in 30 seconds
- CI passes, with tests for the core maths
- Findings write-up with the backtest result
- Resume bullet with real numbers
