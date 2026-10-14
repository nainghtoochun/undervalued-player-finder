"""Download StatsBomb open event data for the chosen season and save as parquet.

Run one league:  python -m pipeline.ingest_statsbomb --league "Premier League"
Run all five:    python -m pipeline.ingest_statsbomb
"""
import argparse
import json
import time
import warnings
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
from statsbombpy import sb

from pipeline.config import COMPETITIONS, RAW_SB, SEASON_ID

warnings.filterwarnings("ignore", message="credentials were not supplied")


def _events(match_id: int, retries: int = 6) -> pd.DataFrame:
    for attempt in range(retries):
        try:
            ev = sb.events(match_id=match_id)
            ev["match_id"] = match_id
            return ev
        except requests.exceptions.RequestException as err:  # rate limits (HTTP 429), network blips
            wait = 2 ** attempt
            print(f"match {match_id}: {err.__class__.__name__}, retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"could not download match {match_id}")


COORD_COLUMNS = {
    "location", "pass_end_location", "carry_end_location", "shot_end_location",
    "goalkeeper_end_location",
}
JSON_COLUMNS = {"shot_freeze_frame", "tactics", "related_events"}


def _to_json(v):
    if isinstance(v, str):  # already JSON text, keep it
        return v
    if isinstance(v, (list, dict)):
        return json.dumps(v)
    return None


def _is_text(s: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)


def _save(df: pd.DataFrame, path, matches_per_part: int | None = None) -> None:
    """Parquet needs one type per column.

    Coordinates stay as float lists, nested columns become JSON text
    (read them back with json.loads), and other mixed columns become strings.
    """
    df = df.copy()
    for col in df.columns:
        if col in COORD_COLUMNS:
            df[col] = df[col].apply(lambda v: [float(x) for x in v] if isinstance(v, list) else None)
        elif col in JSON_COLUMNS:
            df[col] = df[col].apply(_to_json)
        elif _is_text(df[col]) and df[col].dropna().map(type).eq(bool).all():
            df[col] = df[col].astype("boolean")  # flags like under_pressure: True or missing
        elif _is_text(df[col]):
            df[col] = df[col].where(df[col].isna(), df[col].astype(str))
    if matches_per_part is None:
        df.to_parquet(path, compression="zstd")
        return
    # events are split into parts (a folder of small files) so each file stays
    # well under GitHub's and OneDrive's comfortable sizes
    path.mkdir(parents=True, exist_ok=True)
    ids = sorted(df["match_id"].unique())
    for i in range(0, len(ids), matches_per_part):
        part = df[df["match_id"].isin(ids[i:i + matches_per_part])]
        part.to_parquet(path / f"part-{i // matches_per_part:02d}.parquet", compression="zstd")


def download_league(name: str, competition_id: int, workers: int = 4) -> None:
    out = RAW_SB / f"{competition_id}_{SEASON_ID}_events"
    if out.exists():
        print(f"skip {name}, already downloaded")
        return
    matches = sb.matches(competition_id=competition_id, season_id=SEASON_ID)
    print(f"{name}: downloading {len(matches)} matches")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        frames = list(pool.map(_events, matches["match_id"]))
    events = pd.concat(frames, ignore_index=True)
    events["league"] = name
    _save(events, out, matches_per_part=40)
    _save(matches, RAW_SB / f"{competition_id}_{SEASON_ID}_matches.parquet")
    print(f"saved {name}: {len(events):,} events -> {out.name}/")


def load_events(leagues: list[str] | None = None, columns: list[str] | None = None,
                types: list[str] | None = None) -> pd.DataFrame:
    """Read downloaded leagues back into one DataFrame.

    Pass `columns` to load only what you need, and `types` (like ["Shot"]) to keep
    only some event types. All five leagues with every column is about
    5 million rows x 120 columns, too big for most laptops.
    """
    names = leagues or list(COMPETITIONS)
    frames = []
    for name in names:
        path = RAW_SB / f"{COMPETITIONS[name]}_{SEASON_ID}_events"
        for f in sorted(path.glob("*.parquet")):
            filters = [("type", "in", types)] if types else None
            part = pd.read_parquet(f, columns=columns, filters=filters)
            part["league"] = name
            frames.append(part)
    if not frames:
        raise FileNotFoundError("no events downloaded yet, run pipeline.ingest_statsbomb first")
    return pd.concat(frames, ignore_index=True)


def downloaded_leagues() -> list[str]:
    return [n for n, cid in COMPETITIONS.items() if (RAW_SB / f"{cid}_{SEASON_ID}_events").exists()]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", choices=list(COMPETITIONS), help="download only this league")
    args = parser.parse_args()
    RAW_SB.mkdir(parents=True, exist_ok=True)
    targets = {args.league: COMPETITIONS[args.league]} if args.league else COMPETITIONS
    for name, cid in targets.items():
        download_league(name, cid)
