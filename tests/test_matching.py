import numpy as np
import pandas as pd
import pytest

from pipeline.match_players import club_key, match_clubs, match_players_in_club, name_score, normalize
from pipeline.value_model import value_at


def test_normalize_strips_accents_and_case():
    assert normalize("Kléper Laveran Lima Ferreira") == "kleper laveran lima ferreira"
    assert normalize("N'Golo Kanté") == "n golo kante"


def test_short_name_matches_full_name():
    assert name_score("Lionel Andrés Messi Cuccittini", "Lionel Messi") == 100
    assert name_score("Lionel Messi", "Cristiano Ronaldo") < 50


def test_club_key_drops_filler_words():
    assert club_key("Olympique de Marseille") == club_key("Olympique Marseille") == "marseille"


def test_squads_decide_between_lookalike_club_names():
    # after dropping "AC", both names contain "milan", so names alone are a coin flip
    sb = pd.DataFrame({"team": ["AC Milan", "AC Milan", "Inter Milan", "Inter Milan"],
                       "player": ["Gianluigi Donnarumma", "Carlos Bacca", "Mauro Icardi", "Samir Handanovic"]})
    tm_clubs = pd.DataFrame({"club_id": [46, 5], "club_name": ["Inter Milan", "AC Milan"]})
    tm_minutes = pd.DataFrame({"tm_club_id": [5, 5, 46, 46],
                               "tm_name": ["Gianluigi Donnarumma", "Carlos Bacca", "Mauro Icardi", "Samir Handanovic"]})
    pairs = match_clubs(sb, tm_clubs, tm_minutes).set_index("team")["tm_club_id"]
    assert pairs["AC Milan"] == 5 and pairs["Inter Milan"] == 46


def test_nickname_and_minutes_pick_the_right_player():
    sb = pd.DataFrame({"player_id": [1, 2], "player": ["Jorge Resurrección Merodio", "Antoine Griezmann"],
                       "nickname": ["Koke", None], "minutes": [3062.0, 3000.0]})
    tm = pd.DataFrame({"tm_player_id": [10, 20], "tm_name": ["Antoine Griezmann", "Koke"],
                       "tm_minutes": [2990.0, 3050.0]})
    m = match_players_in_club(sb, tm).set_index("player_id")["tm_player_id"]
    assert m[1] == 20 and m[2] == 10


def test_weak_name_match_is_rejected():
    sb = pd.DataFrame({"player_id": [1], "player": ["Totally Different"], "minutes": [1000.0]})
    tm = pd.DataFrame({"tm_player_id": [10], "tm_name": ["Someone Else"], "tm_minutes": [1000.0]})
    assert match_players_in_club(sb, tm).empty


def test_value_at_takes_latest_value_in_window():
    vals = pd.DataFrame({"player_id": [1, 1, 1, 2], "market_value_in_eur": [1, 2, 3, 9],
                         "date": ["2015-12-01", "2016-02-01", "2016-07-15", "2017-01-01"]})
    v = value_at(vals, "2016-01-01", "2016-08-31", "v")
    assert v.to_dict() == {1: 3}  # player 2 has no value inside the window


@pytest.mark.parametrize("seed", [0, 1])
def test_backtest_finds_a_planted_signal(seed):
    from pipeline.value_model import backtest

    rng = np.random.default_rng(seed)
    n = 400
    gap = rng.normal(size=n)
    v16 = np.exp(rng.normal(15, 1, n))
    df = pd.DataFrame({
        "player_id": range(n), "log_gap": gap, "value_2016": v16,
        "value_2018": v16 * np.exp(0.3 * gap + rng.normal(0, 0.3, n)),  # cheap players really do rise
        "age": rng.uniform(19, 34, n), "position_group": rng.choice(["DEF", "MID", "FWD"], n),
        "league": rng.choice(["A", "B"], n),
    })
    df["age_sq"] = df["age"] ** 2
    summary, by_q = backtest(df, top_n=40, n_boot=200)
    assert summary["extra_growth_ci95"][0] > 0
    assert by_q["extra_growth_log"].is_monotonic_increasing


def test_stats_premium_test_finds_a_planted_effect():
    from pipeline.ablation import stats_premium_test

    rng = np.random.default_rng(0)
    n = 600
    v16 = np.exp(rng.normal(15, 1, n))
    simple_gap = rng.normal(0, 0.5, n)
    premium = rng.normal(0, 0.35, n)  # extra fair value that comes only from xG, xA and xT
    base = pd.DataFrame({
        "player_id": range(n), "value_2016": v16, "age": rng.uniform(19, 34, n),
        "position_group": rng.choice(["DEF", "MID", "FWD"], n), "league": rng.choice(["A", "B"], n),
        "value_2018": v16 * np.exp(0.3 * premium + rng.normal(0, 0.2, n)),  # players with better stats rise
    })
    base["age_sq"] = base["age"] ** 2
    simple = base.assign(log_gap=simple_gap, predicted_value_eur=v16 * np.exp(simple_gap))
    full = base.assign(log_gap=simple_gap + premium, predicted_value_eur=v16 * np.exp(simple_gap + premium))
    result = stats_premium_test(full, simple, n_boot=200)
    assert result["ci95"][0] > 0
    assert result["high_minus_low_premium_within_fifths"] > 0
