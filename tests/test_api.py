"""API tests against a real Postgres, in a separate test database.

They use TEST_DATABASE_URL, or `upf_test` on the local Docker database.
Your real `upf` database is never touched. If no Postgres is reachable,
the tests are skipped (CI starts one, so they always run there).
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from pipeline.config import ROOT

TEST_URL = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://upf:upf@localhost:5432/upf_test")


def _ensure_database(url: str) -> None:
    admin = create_engine(make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        name = make_url(url).database
        if not conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}).first():
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()


@pytest.fixture(scope="module")
def client():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    try:
        _ensure_database(TEST_URL)
        engine = create_engine(TEST_URL)
        with engine.connect():
            pass
    except Exception as err:  # noqa: BLE001 - any connection problem means "no database here"
        pytest.skip(f"no test Postgres available ({err.__class__.__name__})")

    with engine.begin() as conn:
        conn.execute(text("DROP VIEW IF EXISTS player_main_season"))
        conn.execute(text("DROP TABLE IF EXISTS app_meta, player_value_scores, player_season_metrics, "
                          "valuations, players CASCADE"))
        conn.execute(text((ROOT / "db" / "schema.sql").read_text()))
        conn.execute(text("""
            INSERT INTO players VALUES
              (1, 'Jorge Resurrección Merodio', 'Koke', 'Atlético Madrid', 'La Liga', 'Center Midfield', 'MID', 101, '1992-01-08'),
              (2, 'Cheap Winger', NULL, 'Small FC', 'Serie A', 'Left Wing', 'FWD', 102, '1993-05-01'),
              (3, 'Old Defender', NULL, 'Down FC', 'Serie A', 'Center Back', 'DEF', 103, '1981-01-01'),
              (4, 'Pricey Striker', NULL, 'Big FC', 'Premier League', 'Center Forward', 'FWD', 104, '1990-01-01')"""))
        conn.execute(text("""
            INSERT INTO player_season_metrics VALUES
              (1, 'La Liga', '2015/16', 'Atlético Madrid', 3000, 0.10, 0.30, 0.15, 0.05, 0.20, 0.08, 1.2),
              (2, 'Serie A', '2015/16', 'Small FC', 2000, 0.40, 0.30, 0.20, 0.15, 0.35, 0.35, 3.0),
              (2, 'Premier League', '2015/16', 'Other FC', 950, 0.20, 0.10, 0.05, 0.05, 0.10, 0.10, 2.0),
              (3, 'Serie A', '2015/16', 'Down FC', 2500, 0.02, 0.05, 0.03, 0.01, 0.04, 0.00, 0.3),
              (4, 'Premier League', '2015/16', 'Big FC', 2800, 0.60, 0.20, 0.12, 0.08, 0.20, 0.55, 3.5)"""))
        conn.execute(text("""
            INSERT INTO player_value_scores VALUES
              (1, '2015/16', 24.5, FALSE, 40000000, 35000000, -0.125, 3, 70000000),
              (2, '2015/16', 23.2, FALSE, 1000000, 8000000, 7.0, 1, 9000000),
              (3, '2015/16', 35.5, TRUE, 300000, 1500000, 4.0, 2, NULL),
              (4, '2015/16', 26.5, FALSE, 60000000, 30000000, -0.5, 4, 50000000)"""))
        conn.execute(text("""
            INSERT INTO valuations VALUES (102, '2015-07-01', 800000), (102, '2016-07-01', 1000000),
                                          (102, '2018-07-01', 9000000), (102, '2021-01-01', 2000000)"""))
        conn.execute(text("""INSERT INTO app_meta VALUES
              ('backtest', '{"top_n": 50}'), ('backtest_by_quintile', '[]'), ('value_model', '{"chosen": "ridge"}')"""))

    from api.main import app, get_conn

    def test_conn():
        with engine.connect() as conn:
            yield conn

    app.dependency_overrides[get_conn] = test_conn
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_summary_counts_each_player_once(client):
    s = client.get("/summary").json()
    assert s["players"] == 4  # player 2 has two league rows but counts once
    assert s["backtest"]["top_n"] == 50


def test_bargains_skip_old_and_relegated_by_default(client):
    names = [p["name"] for p in client.get("/bargains").json()]
    assert names == ["Cheap Winger", "Koke", "Pricey Striker"]  # rank order, Old Defender left out


def test_bargains_can_include_relegated(client):
    names = [p["name"] for p in client.get("/bargains?include_relegated=true&max_age=40").json()]
    assert names[:2] == ["Cheap Winger", "Old Defender"]


def test_player_uses_main_league_spell(client):
    p = client.get("/players/2").json()
    assert p["league"] == "Serie A" and p["minutes"] == 2000


def test_filters_and_sort(client):
    rows = client.get("/players?league=Serie A&sort=xt_p90").json()
    assert [r["player_id"] for r in rows] == [2, 3]
    rows = client.get("/players?max_value_eur=2000000").json()
    assert {r["player_id"] for r in rows} == {2, 3}


def test_search_matches_nickname(client):
    assert [r["name"] for r in client.get("/players?search=koke").json()] == ["Koke"]


def test_player_detail_has_percentiles_and_history(client):
    p = client.get("/players/2").json()
    assert p["percentiles"]["xt_p90"] == 100.0  # best FWD in the sample
    assert [v["value_eur"] for v in p["value_history"]] == [800000, 1000000, 9000000]  # 2021 is outside the range


def test_unknown_player_is_404(client):
    assert client.get("/players/999").status_code == 404


def test_bad_sort_is_rejected(client):
    assert client.get("/players?sort=name;DROP TABLE players").status_code == 422
