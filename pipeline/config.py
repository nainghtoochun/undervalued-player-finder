from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_SB = ROOT / "data" / "raw" / "statsbomb"
RAW_TM = ROOT / "data" / "raw" / "transfermarkt"
PROCESSED = ROOT / "data" / "processed"

# StatsBomb open data, 2015/16 season (season_id 27).
# Verify the ids with statsbombpy.sb.competitions() before the first run.
SEASON_ID = 27
COMPETITIONS = {
    "Premier League": 2,
    "La Liga": 11,
    "1. Bundesliga": 9,
    "Serie A": 12,
    "Ligue 1": 7,
}

# The Bundesliga 2015/16 in StatsBomb open data only has Bayer Leverkusen's 34 matches,
# not the full 306. We use it to train xG and xT (more shots and passes help),
# but leave it out of the player table, where it would only cover one club fairly.
PLAYER_LEAGUES = ["Premier League", "La Liga", "Serie A", "Ligue 1"]

# StatsBomb pitch is 120 x 80, attacking left to right.
PITCH_X, PITCH_Y = 120, 80
GOAL_X, GOAL_Y = 120, 40
POST_LOW_Y, POST_HIGH_Y = 36, 44

MIN_MINUTES = 900            # ignore players below this
VALUATION_DATE = "2016-08-31"  # market value right after the season (latest on or before)
VALUATION_WINDOW_START = "2016-01-01"
BACKTEST_DATE = "2018-08-31"    # value two summers later
BACKTEST_WINDOW_START = "2018-01-01"
