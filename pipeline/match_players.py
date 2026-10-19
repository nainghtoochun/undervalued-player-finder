"""Match StatsBomb players to Transfermarkt players.

The two sources spell names differently ("Lionel Andrés Messi Cuccittini" vs
"Lionel Messi") and give clubs different names ("Lyon" vs "Olympique Lyon").
So we match in two steps, both inside one league so we never compare
players who could not be the same person.

1. Clubs. Score every StatsBomb club against every Transfermarkt club in the
   same league and pick the best one-to-one pairing (Hungarian algorithm).
2. Players. Inside each club, score every pair of players on name similarity
   plus how close their 2015/16 league minutes are, then pick the best
   one-to-one pairing again. Pairs below MIN_NAME_SCORE are rejected.

data/manual_matches.csv can override any match by hand.

Run: python -m pipeline.match_players   (after python -m pipeline.player_metrics)
"""
import unicodedata

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from scipy.optimize import linear_sum_assignment

from pipeline.config import PLAYER_LEAGUES, PROCESSED, RAW_SB, RAW_TM, ROOT

TM_LEAGUES = {"Premier League": "GB1", "La Liga": "ES1", "Serie A": "IT1", "Ligue 1": "FR1"}
TM_SEASON = 2015  # Transfermarkt labels 2015/16 as 2015
MIN_NAME_SCORE = 70
MANUAL = ROOT / "data" / "manual_matches.csv"
NICKNAMES = RAW_SB / "player_nicknames.csv"

# words that say nothing about which club it is
CLUB_STOPWORDS = {"fc", "afc", "cf", "ac", "as", "ss", "sc", "us", "ogc", "losc", "rc", "cd", "ud", "sd",
                  "rcd", "sco", "hsc", "de", "of", "the", "calcio", "club", "olympique", "stade"}


def normalize(text: str) -> str:
    """Lower case, no accents, letters and spaces only."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return " ".join("".join(c if c.isalnum() else " " for c in text.lower()).split())


def club_key(name: str) -> str:
    words = [w for w in normalize(name).split() if w not in CLUB_STOPWORDS]
    return " ".join(words) or normalize(name)


def name_score(a: str, b: str) -> float:
    """0 to 100. token_set_ratio handles one name being a shorter form of the other."""
    a, b = normalize(a), normalize(b)
    return max(fuzz.token_set_ratio(a, b), fuzz.WRatio(a, b))


def fetch_nicknames() -> pd.DataFrame:
    """StatsBomb event data uses full legal names ("Jorge Resurrección Merodio"), but its
    lineups also carry the name fans use ("Koke"). We fetch just enough lineups to
    cover every player once, and cache them."""
    import warnings

    from statsbombpy import sb

    from pipeline.ingest_statsbomb import load_events

    warnings.filterwarnings("ignore", message="credentials were not supplied")
    have = pd.read_csv(NICKNAMES) if NICKNAMES.exists() else pd.DataFrame(
        columns=["player_id", "player_name", "player_nickname"])
    ev = load_events(PLAYER_LEAGUES, columns=["match_id", "player_id"], types=["Pass", "Carry", "Shot"])
    ev = ev.dropna().astype({"player_id": int}).drop_duplicates()
    todo = set(ev["player_id"]) - set(have["player_id"])
    by_match = ev[ev["player_id"].isin(todo)].groupby("match_id")["player_id"].apply(set)
    rows = []
    while todo and len(by_match):  # greedy: the match that covers most missing players first
        match_id = by_match.apply(lambda p: len(p & todo)).idxmax()
        for df in sb.lineups(match_id=int(match_id)).values():
            rows.append(df[["player_id", "player_name", "player_nickname"]])
            todo -= set(df["player_id"])
        by_match = by_match.drop(match_id)
    if rows:
        have = pd.concat([have, *rows], ignore_index=True).drop_duplicates("player_id")
        have.to_csv(NICKNAMES, index=False)
        print(f"fetched nicknames from {len(rows) // 2} lineups")
    return have


def best_pairs(score: np.ndarray) -> list[tuple[int, int]]:
    """One-to-one pairing that maximises the total score."""
    rows, cols = linear_sum_assignment(-score)
    return list(zip(rows, cols))


def match_clubs(sb_players: pd.DataFrame, tm_clubs: pd.DataFrame, tm_minutes: pd.DataFrame) -> pd.DataFrame:
    """Pair clubs by name AND by how many players they share.

    Names alone fail on clubs like AC Milan and Inter Milan, which look alike once
    "AC" is removed. Squads never look alike, so shared players settle it.
    """
    sb_clubs = sorted(sb_players["team"].unique())
    tm_names = tm_minutes.groupby("tm_club_id")["tm_name"].apply(lambda s: [normalize(x) for x in s])
    score = np.zeros((len(sb_clubs), len(tm_clubs)))
    for i, club in enumerate(sb_clubs):
        squad = sb_players[sb_players["team"] == club]
        sb_names = [normalize(x) for x in squad["player"]] + [
            normalize(x) for x in squad.get("nickname", pd.Series(dtype=str)).dropna()]
        for j, (cid, cname) in enumerate(zip(tm_clubs["club_id"], tm_clubs["club_name"])):
            tm_squad = tm_names.get(cid, [])
            shared = sum(any(fuzz.token_set_ratio(a, b) >= 90 for a in sb_names) for b in tm_squad)
            overlap = shared / max(len(tm_squad), 1)
            score[i, j] = 0.3 * fuzz.token_set_ratio(club_key(club), club_key(cname)) + 70 * overlap
    pairs = best_pairs(score)
    return pd.DataFrame([{"team": sb_clubs[i], "tm_club_id": int(tm_clubs["club_id"].iloc[j]),
                          "tm_club_name": tm_clubs["club_name"].iloc[j], "club_score": score[i, j]}
                         for i, j in pairs])


def match_players_in_club(sb: pd.DataFrame, tm: pd.DataFrame) -> pd.DataFrame:
    """sb: player_id, player, minutes. tm: tm_player_id, tm_name, tm_minutes."""
    if sb.empty or tm.empty:
        return pd.DataFrame()
    nick = sb["nickname"] if "nickname" in sb else sb["player"]
    names = np.array([[max(name_score(a, b), name_score(n, b) if isinstance(n, str) else 0)
                       for b in tm["tm_name"]] for a, n in zip(sb["player"], nick)])
    m1 = sb["minutes"].to_numpy()[:, None]
    m2 = tm["tm_minutes"].to_numpy()[None, :]
    minutes_close = 1 - np.abs(m1 - m2) / np.maximum(np.maximum(m1, m2), 1)
    total = names + 15 * minutes_close  # names decide, minutes break ties
    rows = []
    for i, j in best_pairs(total):
        if names[i, j] >= MIN_NAME_SCORE:
            rows.append({"player_id": int(sb["player_id"].iloc[i]),
                         "tm_player_id": int(tm["tm_player_id"].iloc[j]),
                         "tm_name": tm["tm_name"].iloc[j], "name_score": names[i, j],
                         "minutes_close": minutes_close[i, j]})
    return pd.DataFrame(rows)


def load_tm_season() -> tuple[pd.DataFrame, pd.DataFrame]:
    """League games and per player per club minutes for 2015/16."""
    games = pd.read_csv(RAW_TM / "games.csv.gz",
                        usecols=["game_id", "competition_id", "season", "home_club_id", "home_club_name"])
    games = games[(games["season"] == TM_SEASON) & games["competition_id"].isin(TM_LEAGUES.values())]
    apps = pd.read_csv(RAW_TM / "appearances.csv.gz",
                       usecols=["game_id", "player_id", "player_club_id", "player_name", "minutes_played"])
    apps = apps[apps["game_id"].isin(games["game_id"])].merge(
        games[["game_id", "competition_id"]], on="game_id")
    minutes = (apps.groupby(["competition_id", "player_club_id", "player_id", "player_name"])["minutes_played"]
               .sum().reset_index()
               .rename(columns={"player_id": "tm_player_id", "player_name": "tm_name",
                                "minutes_played": "tm_minutes", "player_club_id": "tm_club_id"}))
    clubs = (games.rename(columns={"home_club_id": "club_id", "home_club_name": "club_name"})
             [["competition_id", "club_id", "club_name"]].drop_duplicates())
    return clubs, minutes


def match_all(players: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """players: the per player table from player_metrics (all minutes, not only 900+)."""
    clubs, tm_minutes = load_tm_season()
    nick = fetch_nicknames()[["player_id", "player_nickname"]].rename(columns={"player_nickname": "nickname"})
    players = players.merge(nick, on="player_id", how="left")
    club_maps, matches = [], []
    for league, comp in TM_LEAGUES.items():
        sb_league = players[players["league"] == league]
        cmap = match_clubs(sb_league, clubs[clubs["competition_id"] == comp],
                           tm_minutes[tm_minutes["competition_id"] == comp])
        cmap["league"] = league
        club_maps.append(cmap)
        for _, c in cmap.iterrows():
            sb = sb_league[sb_league["team"] == c["team"]]
            tm = tm_minutes[(tm_minutes["competition_id"] == comp) & (tm_minutes["tm_club_id"] == c["tm_club_id"])]
            m = match_players_in_club(sb.reset_index(drop=True), tm.reset_index(drop=True))
            if not m.empty:
                matches.append(m.assign(league=league, team=c["team"]))
    result = pd.concat(matches, ignore_index=True)

    if MANUAL.exists():  # hand fixes win: player_id,tm_player_id
        manual = pd.read_csv(MANUAL)
        result = result[~result["player_id"].isin(manual["player_id"])]
        result = pd.concat([result, manual.assign(name_score=100.0, minutes_close=np.nan)], ignore_index=True)
    return result, pd.concat(club_maps, ignore_index=True)


if __name__ == "__main__":
    totals = pd.read_parquet(PROCESSED / "player_totals.parquet")
    matches, club_map = match_all(totals)
    weak = club_map[club_map["club_score"] < 40]
    print("club pairs with a low name score (check these):")
    print(weak[["league", "team", "tm_club_name", "club_score"]].to_string(index=False) if len(weak) else "  none")

    regulars = totals[totals["minutes"] >= 900]
    matched = regulars["player_id"].isin(matches["player_id"])
    print(f"\nmatched {matched.sum()} of {len(regulars)} players with 900+ minutes ({matched.mean():.1%})")
    print(f"all players: {len(matches)} of {len(totals)} ({len(matches) / len(totals):.1%})")
    print("\nunmatched regulars (add them to data/manual_matches.csv if you know them):")
    print(regulars[~matched][["league", "team", "player", "minutes"]].to_string(index=False))

    matches.to_csv(PROCESSED / "player_matches.csv", index=False)
    club_map.to_csv(PROCESSED / "club_matches.csv", index=False)
