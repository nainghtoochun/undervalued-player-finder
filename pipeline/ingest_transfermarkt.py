"""Download Transfermarkt data (transfermarkt-datasets by dcaribou).

Run: python -m pipeline.ingest_transfermarkt

Saves gzipped CSVs into data/raw/transfermarkt/. The files are a snapshot
published by the project, so this only needs to run once.
"""
import requests

from pipeline.config import RAW_TM

BASE = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"
FILES = [
    "players",            # one row per player: name, birth date, position
    "player_valuations",  # market value history (date, value in EUR)
    "appearances",        # who played in which game, for which club
    "games",              # game date, season, competition
    "clubs",              # club names
    "competitions",       # league names and ids
]


def download(name: str) -> None:
    out = RAW_TM / f"{name}.csv.gz"
    if out.exists():
        print(f"skip {name}, already downloaded")
        return
    url = f"{BASE}/{name}.csv.gz"
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        tmp = out.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.replace(out)
    print(f"saved {out.name} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    RAW_TM.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        download(name)
