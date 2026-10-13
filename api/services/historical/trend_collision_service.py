"""Trend collision service — given a trend active on each side of a matchup
(any of the 6 streak types, at any venue-scope), find every historical game
where that same collision occurred league-wide and report what happened.
"""

from typing import Any, Dict, List, Tuple


def _typed_results(games: List[Dict], trend_type: str) -> List[Tuple[Any, bool]]:
    """Chronologically-ordered (game_id, result) pairs for one trend type.
    Games missing the data a type needs are skipped entirely (same semantics
    as trend_context_service._game_results)."""
    out: List[Tuple[Any, bool]] = []
    for g in sorted(games, key=lambda x: x['game_date']):
        hs, aw, tl, ln = g.get('hs'), g.get('aw'), g.get('tl'), g.get('ln')
        if hs is None or aw is None:
            continue
        if trend_type in ('over_streak', 'under_streak') and tl is None:
            continue
        if trend_type in ('cover_streak', 'no_cover_streak') and ln is None:
            continue

        if trend_type == 'over_streak':
            result = (hs + aw) > tl
        elif trend_type == 'under_streak':
            result = (hs + aw) < tl
        elif trend_type == 'win_streak':
            result = hs > aw
        elif trend_type == 'loss_streak':
            result = hs < aw
        elif trend_type == 'cover_streak':
            result = (hs + ln) > aw
        elif trend_type == 'no_cover_streak':
            result = (hs + ln) < aw
        else:
            continue
        out.append((g['game_id'], result))
    return out


def _entering_streaks_for_games(games: List[Dict], trend_type: str) -> Dict[Any, int]:
    """Entering-streak snapshot (the running count BEFORE each game) for one
    trend type, walked forward chronologically."""
    snapshots: Dict[Any, int] = {}
    current = 0
    for game_id, result in _typed_results(games, trend_type):
        snapshots[game_id] = current
        current = current + 1 if result else 0
    return snapshots


def _build_entering_streaks(
    team_games: Dict[str, List[Dict]],
    trend_types: Tuple[str, ...],
) -> Tuple[Dict[str, Dict[Any, Dict[str, int]]], Dict[str, Dict[Any, Dict[str, int]]], Dict[str, Dict[Any, Dict[str, int]]]]:
    """For every team, compute entering-streak snapshots in three flavors:
    general (all games), home_venue (only games that team played at home),
    away_venue (only games that team played away). Returns
    (general, home_venue, away_venue), each shaped
    {team_name: {game_id: {trend_type: entering_streak_count}}}.
    """
    general: Dict[str, Dict[Any, Dict[str, int]]] = {}
    home_venue: Dict[str, Dict[Any, Dict[str, int]]] = {}
    away_venue: Dict[str, Dict[Any, Dict[str, int]]] = {}

    for team, games in team_games.items():
        general[team] = {}
        home_venue[team] = {}
        away_venue[team] = {}
        home_games = [g for g in games if g.get('is_home')]
        away_games = [g for g in games if not g.get('is_home')]

        for tt in trend_types:
            for game_id, count in _entering_streaks_for_games(games, tt).items():
                general[team].setdefault(game_id, {})[tt] = count
            for game_id, count in _entering_streaks_for_games(home_games, tt).items():
                home_venue[team].setdefault(game_id, {})[tt] = count
            for game_id, count in _entering_streaks_for_games(away_games, tt).items():
                away_venue[team].setdefault(game_id, {})[tt] = count

    return general, home_venue, away_venue


def _build_collision_index(
    home_h2h_games: Dict[Tuple[str, str], List[Dict]],
    general: Dict[str, Dict[Any, Dict[str, int]]],
    home_venue: Dict[str, Dict[Any, Dict[str, int]]],
    away_venue: Dict[str, Dict[Any, Dict[str, int]]],
    has_spread: bool,
) -> List[Dict]:
    """One record per historical game, carrying both teams' entering streaks
    and that game's outcome (straight-up / ATS / total)."""
    index: List[Dict] = []
    for (home_team, away_team), games in home_h2h_games.items():
        for g in games:
            game_id = g['game_id']
            hs, aw, tl, ln = g.get('hs'), g.get('aw'), g.get('tl'), g.get('ln')
            if hs is None or aw is None:
                continue

            if hs > aw:
                winner = 'home'
            elif hs < aw:
                winner = 'away'
            else:
                winner = None

            if has_spread and ln is not None:
                if hs + ln > aw:
                    ats_result = 'home'
                elif hs + ln < aw:
                    ats_result = 'away'
                else:
                    ats_result = 'push'
            else:
                ats_result = None

            if tl is not None:
                total = hs + aw
                if total > tl:
                    total_result = 'over'
                elif total < tl:
                    total_result = 'under'
                else:
                    total_result = 'push'
            else:
                total_result = None

            index.append({
                'game_id': game_id,
                'home': {
                    'name': home_team,
                    'general': general.get(home_team, {}).get(game_id, {}),
                    'home_venue': home_venue.get(home_team, {}).get(game_id, {}),
                },
                'away': {
                    'name': away_team,
                    'general': general.get(away_team, {}).get(game_id, {}),
                    'away_venue': away_venue.get(away_team, {}).get(game_id, {}),
                },
                'outcome': {
                    'winner': winner,
                    'ats_result': ats_result,
                    'total_result': total_result,
                },
            })
    return index
