"""Run the pipeline end to end. More steps get added each week.

Run: python -m pipeline.run_all
"""
import runpy

STEPS = [
    "pipeline.xg_model",        # week 2: train and compare xG models
    "pipeline.player_metrics",  # week 2: xT grid and per 90 player table
    "pipeline.match_players",   # week 3: link StatsBomb players to Transfermarkt
    "pipeline.value_model",     # week 3: fair value, value gap and the 2018 backtest
    # loading into Postgres is separate: docker compose up -d, then python -m pipeline.load_db
]

if __name__ == "__main__":
    for step in STEPS:
        print(f"\n===== {step} =====")
        runpy.run_module(step, run_name="__main__")
