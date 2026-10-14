"""Load Transfermarkt market values and match players to StatsBomb ids.

Data: transfermarkt-datasets by dcaribou (GitHub / Kaggle "player-scores").
Download players.csv and player_valuations.csv into data/raw/transfermarkt/.

TODO week 3
1. Take each player's valuation closest to VALUATION_DATE and to BACKTEST_DATE.
2. Match names to StatsBomb players with rapidfuzz, restricted to the same club and season.
3. Save a manual_matches.csv for the cases fuzzy matching gets wrong, and report the match rate.
"""
