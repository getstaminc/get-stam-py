"""Regression guards for jobs/ncaab_odds_api_seed_yesterdays_games.py.

Covers the two orientation/period bugs found in final review:
  * parse_odds_data must assign home/away by OUR notion of home/away, not the
    Odds API game's own home_team/away_team -- Odds API frequently reverses
    neutral-site games relative to ESPN (confirmed live on the real
    2026-11-01 Villanova/Notre Dame game).
  * overtime points must sum EVERY overtime period, not just OT1.
"""
from jobs.ncaab_odds_api_seed_yesterdays_games import parse_odds_data


def _odds_game(home_team, away_team):
    """Historical-odds-shaped payload for Villanova vs Notre Dame, with the
    caller choosing which side the Odds API calls 'home'."""
    def outcomes(key):
        if key == "h2h":
            return [{"name": "Villanova Wildcats", "price": 265},
                    {"name": "Notre Dame Fighting Irish", "price": -335}]
        return [{"name": "Villanova Wildcats", "point": 7.5},
                {"name": "Notre Dame Fighting Irish", "point": -7.5}]

    return {
        "id": "5bee3fb00be225402b2d2d7842398207",
        "home_team": home_team,
        "away_team": away_team,
        "bookmakers": [{
            "key": "draftkings",
            "markets": [
                {"key": "h2h", "outcomes": outcomes("h2h")},
                {"key": "spreads", "outcomes": outcomes("spreads")},
                {"key": "totals", "outcomes": [{"name": "Over", "point": 147.5},
                                               {"name": "Under", "point": 147.5}]},
            ],
        }],
    }


# ESPN (and therefore our ncaab_games row) treats Villanova as home.
OUR_HOME, OUR_AWAY = "VILLA", "NOTRE"
EXPECTED = {
    "home_money_line": 265, "away_money_line": -335,
    "home_line": 7.5, "away_line": -7.5, "total": 147.5,
}


def test_parse_odds_data_agreeing_orientation():
    """Odds API agrees with ESPN that Villanova is home."""
    game = _odds_game("Villanova Wildcats", "Notre Dame Fighting Irish")
    assert parse_odds_data(game, OUR_HOME, OUR_AWAY) == EXPECTED


def test_parse_odds_data_reversed_orientation_does_not_swap():
    """Odds API calls Notre Dame home (the real, live-confirmed case). Our
    home/away must still be Villanova/Notre Dame -- values must NOT swap."""
    game = _odds_game("Notre Dame Fighting Irish", "Villanova Wildcats")
    assert parse_odds_data(game, OUR_HOME, OUR_AWAY) == EXPECTED


def test_parse_odds_data_without_db_names_uses_odds_api_orientation():
    """Back-compat: with no db_home/db_away the old positional behaviour holds."""
    game = _odds_game("Notre Dame Fighting Irish", "Villanova Wildcats")
    result = parse_odds_data(game)
    assert result["home_money_line"] == -335
    assert result["home_line"] == -7.5


def test_parse_odds_data_no_bookmakers():
    assert parse_odds_data({"home_team": "A", "away_team": "B", "bookmakers": []}) == {
        "home_money_line": None, "away_money_line": None,
        "home_line": None, "away_line": None, "total": None,
    }


def _halves_and_overtime(linescores):
    """Mirror of the half/OT derivation in seed_yesterdays_ncaab_games."""
    qs = list(linescores) or None
    if qs and len(qs) >= 2:
        return qs[0], qs[1], (sum(qs[2:]) if len(qs) > 2 else None)
    return None, None, None


def test_regulation_game_has_no_overtime():
    first, second, ot = _halves_and_overtime([35, 37])
    assert (first, second, ot) == (35, 37, None)


def test_single_overtime():
    first, second, ot = _halves_and_overtime([35, 37, 9])
    assert ot == 9
    assert first + second + ot == 81


def test_multi_overtime_sums_every_period():
    """A 5-period (double-OT... triple-OT) game: halves + OT must equal the
    final score. Taking only linescores[2] summed 12 points short."""
    linescores = [35, 37, 9, 7, 5]
    first, second, ot = _halves_and_overtime(linescores)
    assert ot == 21
    assert first + second + ot == sum(linescores)
