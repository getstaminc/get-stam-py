from jobs.nhl_espn_enrichment import (
    extract_period_goals,
    detect_overtime_shootout,
    is_playoff_game,
    count_powerplay_goals,
    find_starting_goalie,
)


def test_extract_period_goals_regulation():
    competitor = {"linescores": [{"displayValue": "1"}, {"displayValue": "0"}, {"displayValue": "2"}]}
    assert extract_period_goals(competitor) == [1, 0, 2]


def test_extract_period_goals_shootout_includes_bonus_entry():
    # DET 4 @ SJ 3, 2026-10-17, event 401892525 (real game, Final/SO)
    competitor = {"linescores": [{"displayValue": "1"}, {"displayValue": "0"}, {"displayValue": "2"}, {"displayValue": "0"}, {"displayValue": "1"}]}
    assert extract_period_goals(competitor) == [1, 0, 2, 0, 1]


def test_detect_overtime_shootout_plain_final():
    assert detect_overtime_shootout("Final") == (False, False)


def test_detect_overtime_shootout_ot_only():
    assert detect_overtime_shootout("Final/OT") == (True, False)


def test_detect_overtime_shootout_shootout():
    assert detect_overtime_shootout("Final/SO") == (True, True)


def test_is_playoff_game():
    assert is_playoff_game(3) is True
    assert is_playoff_game(2) is False
    assert is_playoff_game(1) is False


def test_count_powerplay_goals():
    plays = [
        {"type": {"text": "Goal"}, "scoringPlay": True, "team": {"id": "30"}, "strength": {"text": "Power Play"}},
        {"type": {"text": "Goal"}, "scoringPlay": True, "team": {"id": "30"}, "strength": {"text": "Even Strength"}},
        {"type": {"text": "Goal"}, "scoringPlay": True, "team": {"id": "9"}, "strength": {"text": "Power Play"}},
        {"type": {"text": "Shot"}, "scoringPlay": False, "team": {"id": "30"}, "strength": {"text": "Power Play"}},
    ]
    assert count_powerplay_goals(plays, "30") == 1
    assert count_powerplay_goals(plays, "9") == 1


def test_find_starting_goalie_identifies_opponent_starter():
    # Real play-by-play shape from FLA @ BUF, 2026-10-12, event 401892485.
    # Buffalo shoots (team id "2"); the saver named here is Florida's starter.
    plays = [
        {
            "type": {"text": "Shot"},
            "period": {"number": 1},
            "team": {"id": "2"},
            "participants": [
                {"athlete": {"displayName": "Rasmus Dahlin"}, "type": "shooter"},
                {"athlete": {"displayName": "Jacob Markstrom"}, "type": "saver"},
            ],
        },
        {
            "type": {"text": "Shot"},
            "period": {"number": 1},
            "team": {"id": "2"},
            "participants": [
                {"athlete": {"displayName": "Someone Else"}, "type": "shooter"},
                {"athlete": {"displayName": "Akira Schmid"}, "type": "saver"},
            ],
        },
    ]
    # Shots BY team "2" (Buffalo) are saved by Florida's starter -> pass Buffalo's id
    # to get Florida's starter (the opponent of whoever is shooting).
    assert find_starting_goalie(plays, "2") == "Jacob Markstrom"


def test_find_starting_goalie_no_shots_returns_none():
    assert find_starting_goalie([], "2") is None
