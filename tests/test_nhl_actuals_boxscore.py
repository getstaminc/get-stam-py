from jobs.nhl_historical_player_actuals_import_reverse import build_player_stats_lookup_nhl


FIXTURE_BOXSCORE = {
    "boxscore": {
        "players": [
            {
                "team": {"id": "30", "displayName": "Minnesota Wild"},
                "statistics": [
                    {
                        "name": "forwards",
                        "keys": ["blockedShots", "hits", "takeaways", "plusMinus", "timeOnIce",
                                  "powerPlayTimeOnIce", "shortHandedTimeOnIce", "evenStrengthTimeOnIce",
                                  "shifts", "goals", "ytdGoals", "assists", "shotsTotal", "shotsMissed",
                                  "shootoutGoals", "faceoffsWon", "faceoffsLost", "faceoffPercent",
                                  "giveaways", "penalties", "penaltyMinutes"],
                        "athletes": [{
                            "athlete": {"id": "4697086", "displayName": "Danila Yurov"},
                            "stats": ["0", "0", "0", "1", "14:02", "0:00", "0:00", "14:02", "16",
                                      "1", "10", "4", "3", "0", "0", "0", "0", "0", "0", "0", "0"],
                        }],
                    },
                    {"name": "defenses", "keys": [], "athletes": []},
                    {"name": "skaters", "keys": [], "athletes": []},
                    {
                        "name": "goalies",
                        "keys": ["goalsAgainst", "shotsAgainst", "shootoutSaves", "shootoutShotsAgainst",
                                  "saves", "savePct", "evenStrengthSaves", "powerPlaySaves",
                                  "shortHandedSaves", "timeOnIce", "ytdGoals", "penaltyMinutes"],
                        "athletes": [{
                            "athlete": {"id": "4874737", "displayName": "Jesper Wallstedt"},
                            "stats": ["1", "22", "0", "0", "21", ".955", "15", "4", "2", "60:00", "0", "0"],
                        }],
                    },
                ],
            },
        ],
    },
}


def test_build_player_stats_lookup_extracts_skater_stats():
    lookup, team_info = build_player_stats_lookup_nhl(FIXTURE_BOXSCORE)
    yurov = lookup["danila yurov"]
    assert yurov["actual_goals"] == 1
    assert yurov["actual_assists"] == 4
    assert yurov["actual_shots_on_goal"] == 3  # shotsTotal, NOT the shootoutGoals ("SOG") label
    assert yurov["actual_total_saves"] is None
    assert yurov["espn_player_id"] == "4697086"


def test_build_player_stats_lookup_extracts_goalie_saves():
    lookup, team_info = build_player_stats_lookup_nhl(FIXTURE_BOXSCORE)
    wallstedt = lookup["jesper wallstedt"]
    assert wallstedt["actual_total_saves"] == 21
    assert wallstedt["actual_goals"] is None


def test_build_player_stats_lookup_team_info():
    lookup, team_info = build_player_stats_lookup_nhl(FIXTURE_BOXSCORE)
    assert team_info == [{"name": "Minnesota Wild", "espn_id": "30"}]
