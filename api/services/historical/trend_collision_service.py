"""Trend collision service — given a trend active on each side of a matchup
(any of the 6 streak types, at any venue-scope), find every historical game
where that same collision occurred league-wide and report what happened.
"""

from typing import Any, Dict, List, Optional, Tuple

from .trend_context_service import SPORT_CONFIG, get_sport_context, get_trend_types


def trend_dimension(trend_type: str) -> Optional[str]:
    """Which of the three outcome metrics (straight_up/ats/total) a trend type
    is about. Lives here (rather than in trend_enrichment.py, the other module
    that needs it) so trend_overview_service.py can import it from a common
    lower-level module without a circular import."""
    return {
        'win_streak': 'straight_up', 'loss_streak': 'straight_up',
        'cover_streak': 'ats', 'no_cover_streak': 'ats',
        'over_streak': 'total', 'under_streak': 'total',
    }.get(trend_type)


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


_collision_cache: Dict[str, Dict] = {}


def _load_collision_context(sport: str) -> Any:
    if sport in _collision_cache:
        return _collision_cache[sport]

    ctx = get_sport_context(sport)
    if not ctx:
        return None

    cfg = SPORT_CONFIG.get(sport, {})
    has_spread = bool(cfg.get('home_spread') and cfg.get('away_spread'))
    trend_types = get_trend_types(sport)

    general, home_venue, away_venue = _build_entering_streaks(ctx.get('team_games', {}), trend_types)
    collision_index = _build_collision_index(
        ctx.get('home_h2h_games', {}), general, home_venue, away_venue, has_spread,
    )

    result = {'collision_index': collision_index}
    _collision_cache[sport] = result
    return result


def get_collision_stats(
    sport: str,
    home_criterion: Dict[str, Any],
    away_criterion: Dict[str, Any],
) -> Any:
    """Scan the sport's collision_index for every historical game matching both
    criteria (>= threshold). 'home_side' in the result labels whichever team
    satisfied home_criterion in each matched game — the literal home team,
    unless both criteria are 'general' and a role-swapped arrangement matched
    instead (general trends carry no venue identity, so either physical team
    may satisfy either side of the query)."""
    valid_venues = ('general', 'venue_specific')
    if home_criterion['venue'] not in valid_venues or away_criterion['venue'] not in valid_venues:
        raise ValueError(
            "criterion 'venue' must be 'general' or 'venue_specific', got "
            f"home={home_criterion['venue']!r} away={away_criterion['venue']!r}"
        )

    ctx = _load_collision_context(sport)
    if not ctx:
        return None

    both_general = home_criterion['venue'] == 'general' and away_criterion['venue'] == 'general'

    matches = 0
    su_wins = su_total = 0
    ats_wins = ats_total = 0
    over_count = over_total = 0

    for game in ctx['collision_index']:
        home_pool = game['home']['home_venue'] if home_criterion['venue'] == 'venue_specific' else game['home']['general']
        away_pool = game['away']['away_venue'] if away_criterion['venue'] == 'venue_specific' else game['away']['general']
        home_val = home_pool.get(home_criterion['trend_type'], 0)
        away_val = away_pool.get(away_criterion['trend_type'], 0)

        straight = home_val >= home_criterion['min_length'] and away_val >= away_criterion['min_length']

        swapped = False
        if not straight and both_general:
            swapped_home_val = game['away']['general'].get(home_criterion['trend_type'], 0)
            swapped_away_val = game['home']['general'].get(away_criterion['trend_type'], 0)
            swapped = swapped_home_val >= home_criterion['min_length'] and swapped_away_val >= away_criterion['min_length']

        if not (straight or swapped):
            continue

        matches += 1
        home_side_is_literal_home = straight

        winner = game['outcome']['winner']
        if winner is not None:
            su_total += 1
            home_side_won = (winner == 'home') if home_side_is_literal_home else (winner == 'away')
            if home_side_won:
                su_wins += 1

        ats_result = game['outcome']['ats_result']
        if ats_result not in (None, 'push'):
            ats_total += 1
            home_side_covered = (ats_result == 'home') if home_side_is_literal_home else (ats_result == 'away')
            if home_side_covered:
                ats_wins += 1

        total_result = game['outcome']['total_result']
        if total_result not in (None, 'push'):
            over_total += 1
            if total_result == 'over':
                over_count += 1

    if matches == 0:
        return None

    return {
        'sample_size': matches,
        'straight_up': {'home_side_win_rate': su_wins / su_total, 'sample_size': su_total} if su_total else None,
        'ats': {'home_side_cover_rate': ats_wins / ats_total, 'sample_size': ats_total} if ats_total else None,
        'total': {'over_rate': over_count / over_total, 'sample_size': over_total} if over_total else None,
    }
