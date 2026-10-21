from datetime import date

from jobs.nhl_historical_player_odds_import import parse_historical_player_props


FIXTURE_ODDS_DATA = {
    "id": "0922c474e6588f94af491684dbae6cdb",
    "home_team": "Calgary Flames",
    "away_team": "Carolina Hurricanes",
    "bookmakers": [
        {
            "key": "draftkings",
            "markets": [
                {
                    "key": "player_goals",
                    "outcomes": [
                        {"name": "Over", "description": "Sebastian Aho", "price": 165, "point": 0.5},
                        {"name": "Under", "description": "Sebastian Aho", "price": -225, "point": 0.5},
                    ],
                },
                {
                    "key": "player_assists",
                    "outcomes": [
                        {"name": "Over", "description": "Sebastian Aho", "price": -130, "point": 0.5},
                        {"name": "Under", "description": "Sebastian Aho", "price": -105, "point": 0.5},
                    ],
                },
                {
                    "key": "player_total_saves",
                    "outcomes": [
                        {"name": "Over", "description": "Devin Cooley", "price": -115, "point": 27.5},
                        {"name": "Under", "description": "Devin Cooley", "price": -120, "point": 27.5},
                    ],
                },
                {
                    "key": "player_goal_scorer_anytime",
                    "outcomes": [
                        {"name": "Yes", "description": "Andrei Svechnikov", "price": 155},
                    ],
                },
            ],
        }
    ],
}


def test_parse_standard_over_under_market():
    props = parse_historical_player_props(FIXTURE_ODDS_DATA, "2026-10-18T22:10:00Z")
    aho_goals = next(p for p in props if p["player_name"] == "Sebastian Aho" and p["stat_type"] == "goals")
    assert aho_goals["line"] == 0.5
    assert aho_goals["over_price"] == 165
    assert aho_goals["under_price"] == -225
    assert aho_goals["game_date"] == date(2026, 10, 18)


def test_parse_anytime_goal_scorer_binary_market():
    props = parse_historical_player_props(FIXTURE_ODDS_DATA, "2026-10-18T22:10:00Z")
    anytime = next(p for p in props if p["player_name"] == "Andrei Svechnikov")
    assert anytime["stat_type"] == "goal_scorer_anytime"
    assert anytime["line"] == 0.5
    assert anytime["over_price"] == 155
    assert anytime["under_price"] is None


def test_parse_skips_outcomes_missing_point_on_standard_markets():
    data = {
        **FIXTURE_ODDS_DATA,
        "bookmakers": [{
            "key": "draftkings",
            "markets": [{
                "key": "player_goals",
                "outcomes": [{"name": "Over", "description": "No Point Player", "price": 100, "point": None}],
            }],
        }],
    }
    props = parse_historical_player_props(data, "2026-10-18T22:10:00Z")
    assert props == []


def test_parse_ignores_non_draftkings_bookmakers():
    data = {**FIXTURE_ODDS_DATA, "bookmakers": [{"key": "fanduel", "markets": FIXTURE_ODDS_DATA["bookmakers"][0]["markets"]}]}
    assert parse_historical_player_props(data, "2026-10-18T22:10:00Z") == []
