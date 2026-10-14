"""Run the pipeline end to end. More steps get added each week.

Run: python -m pipeline.run_all
"""
import runpy

STEPS = [
    "pipeline.xg_model",        # week 2: train and compare xG models
    "pipeline.player_metrics",  # week 2: xT grid and per 90 player table
    # week 3: pipeline.ingest_transfermarkt, pipeline.value_model, load to Postgres
]

if __name__ == "__main__":
    for step in STEPS:
        print(f"\n===== {step} =====")
        runpy.run_module(step, run_name="__main__")
