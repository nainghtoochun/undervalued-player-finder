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

# StatsBomb pitch is 120 x 80, attacking left to right.
PITCH_X, PITCH_Y = 120, 80
GOAL_X, GOAL_Y = 120, 40
POST_LOW_Y, POST_HIGH_Y = 36, 44

MIN_MINUTES = 900            # ignore players below this
VALUATION_DATE = "2016-07-01"  # market value snapshot after the season
BACKTEST_DATE = "2018-07-01"   # value two years later
