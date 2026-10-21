"""Pure functions for enriching NHL games with data ESPN has but the Odds API
doesn't: period goals, overtime/shootout, playoffs, powerplay goals, and
starting goalies. All verified against real ESPN NHL summary responses —
see tests/test_nhl_espn_enrichment.py for the specific games checked.

ESPN's boxscore `starter` field on goalie entries is unpopulated (confirmed
null on every game checked), so starting goalie is derived from play-by-play
instead: the first period-1 shot a team takes is saved by the OPPOSING
team's starting goalie.
"""
from typing import List, Optional, Tuple


def extract_period_goals(competitor: dict) -> List[int]:
    """Per-period goals from ESPN's `linescores` array on a competitor. A
    shootout-deciding goal appears as a bonus 5th entry; left in as-is since
    nhl_games.home_period_goals/away_period_goals is an array column with no
    fixed length requirement."""
    return [int(entry["displayValue"]) for entry in competitor.get("linescores", [])]


def detect_overtime_shootout(status_detail: str) -> Tuple[bool, bool]:
    """ESPN's status.type.detail is literally 'Final', 'Final/OT', or
    'Final/SO'. A shootout game went through overtime first, so shoot_out=True
    implies overtime=True."""
    detail = status_detail or ""
    shoot_out = "SO" in detail
    overtime = shoot_out or "OT" in detail
    return overtime, shoot_out


def is_playoff_game(season_type: int) -> bool:
    """ESPN season.type: 1=preseason, 2=regular season, 3=postseason."""
    return season_type == 3


def count_powerplay_goals(plays: list, espn_team_id: str) -> int:
    """Count scoring plays credited to espn_team_id with strength.text ==
    'Power Play'. Only scoringPlay=True entries count — a non-scoring 'Shot'
    play can also carry strength info and must not be counted."""
    count = 0
    for play in plays:
        if not play.get("scoringPlay"):
            continue
        if str(play.get("team", {}).get("id", "")) != str(espn_team_id):
            continue
        if (play.get("strength") or {}).get("text") != "Power Play":
            continue
        count += 1
    return count


def find_starting_goalie(plays: list, shooting_espn_team_id: str) -> Optional[str]:
    """Return the name of the goalie who faced the FIRST period-1 shot taken
    BY shooting_espn_team_id — that goalie belongs to the opposing team, and
    is that team's starter. Pass the team that is SHOOTING; the name
    returned belongs to the OTHER team."""
    for play in plays:
        if play.get("type", {}).get("text") != "Shot":
            continue
        if play.get("period", {}).get("number") != 1:
            continue
        if str(play.get("team", {}).get("id", "")) != str(shooting_espn_team_id):
            continue
        for participant in play.get("participants", []):
            if participant.get("type") == "saver":
                return participant["athlete"]["displayName"]
    return None
