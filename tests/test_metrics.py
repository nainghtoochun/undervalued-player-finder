import json

import numpy as np
import pandas as pd
import pytest

from pipeline.player_metrics import minutes_played, per90, position_group
from pipeline.xg_model import freeze_frame_features


def _lineup(ids):
    return json.dumps({"formation": 442, "lineup": [
        {"player": {"id": i, "name": f"P{i}"}, "position": {"name": "Center Back"}} for i in ids]})


def _event(type_, minute, second=0, team="A", player_id=None, **extra):
    row = {"match_id": 1, "type": type_, "minute": minute, "second": second, "team": team,
           "player_id": player_id, "tactics": None, "substitution_replacement_id": None,
           "substitution_replacement": None, "foul_committed_card": None,
           "bad_behaviour_card": None, "player_off_permanent": None}
    row.update(extra)
    return row


@pytest.fixture
def match():
    """Team A starts players 1 and 2. Player 2 is subbed for 3 at 60:00.
    Player 1 gets a red card at 80:00. The match ends at 90:00."""
    return pd.DataFrame([
        _event("Starting XI", 0, tactics=_lineup([1, 2])),
        _event("Pass", 10, player_id=1),
        _event("Substitution", 60, player_id=2, substitution_replacement_id=3.0,
               substitution_replacement="P3"),
        _event("Foul Committed", 80, player_id=1, foul_committed_card="Red Card"),
        _event("Half End", 90),
    ])


def test_starter_who_plays_until_subbed(match):
    mins = minutes_played(match).set_index("player_id")["minutes"]
    assert mins[2] == pytest.approx(60)


def test_substitute_plays_from_coming_on_to_the_end(match):
    mins = minutes_played(match).set_index("player_id")["minutes"]
    assert mins[3] == pytest.approx(30)


def test_red_card_ends_minutes(match):
    mins = minutes_played(match).set_index("player_id")["minutes"]
    assert mins[1] == pytest.approx(80)


def test_per90_scales_and_filters():
    totals = pd.DataFrame({
        "player_id": [1, 2], "minutes": [1800.0, 450.0], "npxg": [10.0, 5.0], "xa": [2.0, 1.0],
        "xt_pass": [3.0, 1.0], "xt_carry": [1.0, 0.0], "np_goals": [9, 4], "np_shots": [60, 20],
    })
    out = per90(totals, min_minutes=900)
    assert list(out["player_id"]) == [1]  # 450 minutes is below the cut
    assert out.loc[0, "npxg_p90"] == pytest.approx(0.5)  # 10 xG over 20 full matches
    assert out.loc[0, "xt_p90"] == pytest.approx((3 + 1) / 1800 * 90)


@pytest.mark.parametrize("name, group", [
    ("Goalkeeper", "GK"), ("Left Center Back", "DEF"), ("Right Wing Back", "DEF"),
    ("Center Defensive Midfield", "MID"), ("Left Wing", "FWD"), ("Center Forward", "FWD"),
    (None, "UNK"),
])
def test_position_group(name, group):
    assert position_group(name) == group


def test_freeze_frame_counts_defenders_in_the_way():
    shot = [108.0, 40.0]  # penalty spot
    frame = json.dumps([
        {"location": [114.0, 40.0], "teammate": False, "position": {"name": "Center Back"}},  # in the way
        {"location": [100.0, 10.0], "teammate": False, "position": {"name": "Left Back"}},    # far away
        {"location": [119.0, 40.0], "teammate": False, "position": {"name": "Goalkeeper"}},
        {"location": [110.0, 40.0], "teammate": True, "position": {"name": "Center Forward"}},
    ])
    f = freeze_frame_features(shot, frame)
    assert f["defenders_in_cone"] == 1
    assert f["keeper_in_cone"] == 1
    assert f["keeper_dist_to_goal"] == pytest.approx(1.0)
    assert f["nearest_defender"] == pytest.approx(6.0)


def test_missing_freeze_frame_is_safe():
    f = freeze_frame_features([100.0, 40.0], None)
    assert f["has_freeze_frame"] == 0 and np.isnan(f["nearest_defender"])
