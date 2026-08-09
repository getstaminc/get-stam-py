"""Trend confidence scoring and ranking.

Python port of getConfidenceScore (getstam-react/src/components/TrendInsightCard.tsx)
and the trend-combining/sort logic in getstam-react/src/pages/HomePage.tsx, so
backend jobs can pick the same "top trend" a game would show on the homepage.
"""

from typing import Any, Dict, List

_UNFILTERED_ARRAYS = ("headToHeadTrends", "homeAtHomeH2HTrends")


def get_confidence_score(trend: Dict[str, Any]) -> float:
    """Port of getConfidenceScore, TrendInsightCard.tsx."""
    continuation_rate = trend.get("continuation_rate")
    sample_size = trend.get("sample_size") or 0
    count = trend.get("count", 0)

    if continuation_rate is not None and sample_size >= 5:
        deviation = abs(continuation_rate - 0.5)
        if deviation >= 0.15 and sample_size >= 10:
            return 4
        if deviation >= 0.08 and sample_size >= 5:
            return 3
        if deviation >= 0.04:
            return 2
        return 1

    if count >= 7:
        return 1
    if count >= 5:
        return 0.5
    return 0


def rank_game_trends(game_with_trends: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Port of the allTrends build+sort, HomePage.tsx.

    Combines headToHeadTrends/homeAtHomeH2HTrends (unfiltered) with the
    home/away-specific trend arrays, then the general team-trend arrays
    filtered to exclude types already covered by the more specific arrays.
    Each returned trend dict is tagged with '_source'. Sorted by
    confidence score descending, ties broken by streak count descending.
    """
    home_home = game_with_trends.get("homeTeamHomeTrends") or []
    away_away = game_with_trends.get("awayTeamAwayTrends") or []
    home_types = {t["type"] for t in home_home}
    away_types = {t["type"] for t in away_away}

    def tag(trends, source):
        return [dict(t, _source=source) for t in trends]

    all_trends: List[Dict[str, Any]] = []
    for source in _UNFILTERED_ARRAYS:
        all_trends.extend(tag(game_with_trends.get(source) or [], source))
    all_trends.extend(tag(home_home, "homeTeamHomeTrends"))
    all_trends.extend(tag(away_away, "awayTeamAwayTrends"))
    all_trends.extend(
        tag([t for t in (game_with_trends.get("homeTeamTrends") or []) if t["type"] not in home_types], "homeTeamTrends")
    )
    all_trends.extend(
        tag([t for t in (game_with_trends.get("awayTeamTrends") or []) if t["type"] not in away_types], "awayTeamTrends")
    )

    all_trends.sort(key=lambda t: (-get_confidence_score(t), -t.get("count", 0)))
    return all_trends
