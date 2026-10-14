CREATE TABLE IF NOT EXISTS players (
    player_id        INTEGER PRIMARY KEY,   -- StatsBomb player id
    name             TEXT NOT NULL,
    team             TEXT,
    league           TEXT,
    position_group   TEXT,                   -- GK, DEF, MID, FWD
    birth_date       DATE,
    tm_player_id     INTEGER                 -- Transfermarkt id after matching
);

CREATE TABLE IF NOT EXISTS player_season_metrics (
    player_id        INTEGER REFERENCES players(player_id),
    season           TEXT NOT NULL,
    minutes          INTEGER NOT NULL,
    npxg_p90         REAL,
    xa_p90           REAL,
    xt_pass_p90      REAL,
    xt_carry_p90     REAL,
    xt_total_p90     REAL,
    PRIMARY KEY (player_id, season)
);

CREATE TABLE IF NOT EXISTS valuations (
    tm_player_id     INTEGER NOT NULL,
    valued_on        DATE NOT NULL,
    market_value_eur BIGINT NOT NULL,
    PRIMARY KEY (tm_player_id, valued_on)
);

CREATE TABLE IF NOT EXISTS player_value_scores (
    player_id            INTEGER REFERENCES players(player_id),
    season               TEXT NOT NULL,
    market_value_eur     BIGINT,
    predicted_value_eur  BIGINT,
    value_gap_pct        REAL,              -- (predicted - actual) / actual
    value_2y_later_eur   BIGINT,            -- for the backtest
    PRIMARY KEY (player_id, season)
);
