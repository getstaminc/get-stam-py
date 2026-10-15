"""Market overview — rolls up every trend already attached to a game (single-team,
H2H, and collision trends) into one blended lean per betting market (moneyline,
spread, total), so a card doesn't have to be read one trend at a time to get a
bottom line.
"""

from typing import Any, Dict, List, Optional, Tuple

from .trend_collision_service import trend_dimension

_POSITIVE_TYPES = {'win_streak', 'cover_streak', 'over_streak'}

_HOME_PERSPECTIVE_KEYS = ('homeTeamTrends', 'homeTeamHomeTrends', 'headToHeadTrends', 'homeAtHomeH2HTrends')
_AWAY_PERSPECTIVE_KEYS = ('awayTeamTrends', 'awayTeamAwayTrends')

_MARKET_LABELS = {'straight_up': 'moneyline', 'ats': 'spread', 'total': 'total'}


def _normalize_simple_trend(trend: Dict, side: str) -> Optional[Tuple[str, float, int]]:
    """A "simple" trend (single-team or H2H, as opposed to a collision) reports
    the probability ITS OWN streak continues, from one team's perspective. Convert
    that into (dimension, home_favorable_or_over_probability, sample_size):
    - win/cover/over continuing is favorable to the team/direction it belongs to.
    - loss/no_cover/under continuing is UNfavorable to that team (so flip to 1-rate).
    - for straight_up/ats, an away-side trend's favorability flips again relative
      to "probability home wins/covers" (total doesn't depend on side at all).
    Returns None if the trend lacks the data to be used, or isn't a type we track.
    """
    rate = trend.get('continuation_rate')
    sample_size = trend.get('sample_size')
    if rate is None or sample_size is None:
        return None

    dim = trend_dimension(trend.get('type'))
    if dim is None:
        return None

    favorable = rate if trend['type'] in _POSITIVE_TYPES else (1 - rate)
    if dim != 'total' and side == 'away':
        favorable = 1 - favorable

    return dim, favorable, sample_size


def _normalize_collision_trend(collision: Dict) -> Optional[Tuple[str, float, int]]:
    """A collision's continuation_rate is already home-side-outcome-framed
    (home_side_win_rate / home_side_cover_rate / over_rate directly) -- not
    streak-direction-framed -- so no win/loss or home/away flip is needed; it's
    used as-is for whichever dimension the home side's own trend type maps to."""
    rate = collision.get('continuation_rate')
    sample_size = collision.get('sample_size')
    if rate is None or sample_size is None:
        return None

    home_trend_type = (collision.get('home_trend') or {}).get('type')
    dim = trend_dimension(home_trend_type)
    if dim is None:
        return None

    return dim, rate, sample_size


def build_market_overview(game_trends: Dict) -> Optional[Dict[str, Dict[str, Any]]]:
    """Blend every trend on this game into one lean per market. Returns
    {'moneyline': {...}, 'spread': {...}, 'total': {...}} (only the markets that
    have at least one usable trend), or None if nothing was usable at all.

    Each market entry: {'lean', 'probability', 'trend_count', 'sample_size',
    'supporting_description'}. 'lean' is a team name for moneyline/spread, or
    'Over'/'Under' for total. 'probability' is the blended probability of
    whichever side/direction is leaned toward (always >= 0.5).
    """
    buckets: Dict[str, List[Tuple[float, int, Dict]]] = {'straight_up': [], 'ats': [], 'total': []}

    for key in _HOME_PERSPECTIVE_KEYS:
        for t in game_trends.get(key) or []:
            normalized = _normalize_simple_trend(t, side='home')
            if normalized:
                dim, prob, n = normalized
                buckets[dim].append((prob, n, t))

    for key in _AWAY_PERSPECTIVE_KEYS:
        for t in game_trends.get(key) or []:
            normalized = _normalize_simple_trend(t, side='away')
            if normalized:
                dim, prob, n = normalized
                buckets[dim].append((prob, n, t))

    for c in game_trends.get('collisionTrends') or []:
        normalized = _normalize_collision_trend(c)
        if normalized:
            dim, prob, n = normalized
            buckets[dim].append((prob, n, c))

    home = ((game_trends.get('game') or {}).get('home') or {}).get('team', '')
    away = ((game_trends.get('game') or {}).get('away') or {}).get('team', '')

    overview: Dict[str, Dict[str, Any]] = {}
    for dim, label in _MARKET_LABELS.items():
        entries = buckets[dim]
        total_n = sum(n for _, n, _ in entries)
        if not entries or total_n == 0:
            continue

        blended = sum(prob * n for prob, n, _ in entries) / total_n
        top_trend = max(entries, key=lambda e: e[1])[2]

        if dim == 'total':
            lean = 'Over' if blended >= 0.5 else 'Under'
            lean_probability = blended if blended >= 0.5 else 1 - blended
        else:
            lean = home if blended >= 0.5 else away
            lean_probability = blended if blended >= 0.5 else 1 - blended

        overview[label] = {
            'lean': lean,
            'probability': lean_probability,
            'trend_count': len(entries),
            'sample_size': total_n,
            'supporting_description': top_trend.get('description', ''),
        }

    return overview or None
