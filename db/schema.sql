-- Undervalued Player Finder schema (Postgres 16)
-- Safe to run many times. pipeline/load_db.py runs it, then reloads every table.

CREATE TABLE IF NOT EXISTS players (
    player_id        INTEGER PRIMARY KEY,   -- StatsBomb player id
    name             TEXT NOT NULL,         -- full name from StatsBomb
    nickname         TEXT,                  -- the name fans use ("Koke")
    team             TEXT NOT NULL,         -- club with the most minutes in 2015/16
    league           TEXT NOT NULL,
    position         TEXT,
    position_group   TEXT,                  -- GK, DEF, MID, FWD
    tm_player_id     INTEGER UNIQUE,        -- Transfermarkt id, NULL if not matched
    birth_date       DATE
);

CREATE TABLE IF NOT EXISTS player_season_metrics (
    player_id        INTEGER NOT NULL REFERENCES players(player_id),
    league           TEXT NOT NULL,         -- a January transfer gives a player two rows
    season           TEXT NOT NULL,
    team             TEXT NOT NULL,
    minutes          REAL NOT NULL,
    npxg_p90         REAL,
    xa_p90           REAL,
    xt_pass_p90      REAL,
    xt_carry_p90     REAL,
    xt_p90           REAL,
    np_goals_p90     REAL,
    np_shots_p90     REAL,
    PRIMARY KEY (player_id, league, season)
);

CREATE TABLE IF NOT EXISTS valuations (
    tm_player_id     INTEGER NOT NULL,
    valued_on        DATE NOT NULL,
    market_value_eur BIGINT NOT NULL,
    PRIMARY KEY (tm_player_id, valued_on)
);

CREATE TABLE IF NOT EXISTS player_value_scores (
    player_id            INTEGER PRIMARY KEY REFERENCES players(player_id),
    season               TEXT NOT NULL,
    age                  REAL,
    relegated            BOOLEAN NOT NULL,
    value_2016_eur       BIGINT NOT NULL,
    predicted_value_eur  BIGINT NOT NULL,
    value_gap_pct        REAL NOT NULL,      -- (predicted - actual) / actual, above 0 = looks cheap
    gap_rank             INTEGER NOT NULL,   -- 1 = biggest bargain
    value_2018_eur       BIGINT              -- NULL if retired or left the data
);

CREATE INDEX IF NOT EXISTS idx_scores_rank ON player_value_scores (gap_rank);
CREATE INDEX IF NOT EXISTS idx_metrics_xt ON player_season_metrics (xt_p90 DESC);

-- small key/value store for model and backtest summaries shown on the website
CREATE TABLE IF NOT EXISTS app_meta (
    key    TEXT PRIMARY KEY,
    value  JSONB NOT NULL
);

-- one row per player: the league spell where he played the most minutes
CREATE OR REPLACE VIEW player_main_season AS
SELECT DISTINCT ON (player_id) *
FROM player_season_metrics
ORDER BY player_id, minutes DESC;
