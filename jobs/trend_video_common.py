"""
Shared helpers for the trend-video script generators (MLB/NFL/NCAAF) and the
weekly scheduler (plan_daily_trend_videos.py) that drives them.
"""

from datetime import datetime, timedelta


def next_weekday(from_date_str, target_weekday):
    """Next date on/after from_date_str that falls on target_weekday (Monday=0
    ... Sunday=6) — always strictly in the future, never from_date_str itself,
    even if from_date_str already falls on target_weekday."""
    d = datetime.strptime(from_date_str, "%Y-%m-%d").date()
    days_ahead = (target_weekday - d.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (d + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


def commence_hour_et(commence_time_str, eastern_tz):
    """Parse a game's commence_time (ISO 8601, typically UTC) and return its
    hour of day in US/Eastern (0-23), or None if unparseable/missing."""
    if not commence_time_str:
        return None
    try:
        dt = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone(eastern_tz).hour


# Named soft time-of-day preferences used when picking which games get a
# video on a given day. These are TIEBREAKS around trend score, not hard
# filters: games in the preferred window are tried first (sorted by trend
# score among themselves), but if there aren't enough of them, games outside
# the window still fill the remaining slots rather than leaving them empty.
TIME_PREFERENCES = {
    # Friday's NCAAF look-ahead to Saturday — prefer the earlier kickoffs.
    "earlier_in_day": lambda hour: hour < 17,
    # Saturday's own NCAAF slate — prefer games later than the noon/1pm ET window.
    "not_noon_or_1pm": lambda hour: hour >= 14,
    # Saturday's NFL look-ahead to Sunday — prefer the early (1pm ET) game block.
    "early_block": lambda hour: hour < 14,
    # Sunday's own NFL slate — prefer the afternoon window (4pm ET) or later.
    "afternoon_or_later": lambda hour: hour >= 16,
}


def select_top_games(entries, max_games, time_pref=None, eastern_tz=None):
    """Rank entries by trend score (entry["_top_trend_score"], set by the
    caller) and take the top max_games. If time_pref names a window in
    TIME_PREFERENCES, games inside that window are preferred over games
    outside it (each group still internally ordered by trend score) —
    a soft tiebreak, not a hard filter; games outside the window still fill
    remaining slots if not enough preferred-window games qualify.
    """
    entries = sorted(entries, key=lambda e: e["_top_trend_score"], reverse=True)
    if time_pref is None:
        return entries[:max_games]

    predicate = TIME_PREFERENCES[time_pref]
    preferred, other = [], []
    for e in entries:
        hour = commence_hour_et(e["game"].get("commence_time"), eastern_tz)
        (preferred if (hour is not None and predicate(hour)) else other).append(e)
    return (preferred + other)[:max_games]


LOOKAHEAD_PROMPT_NOTE = (
    "\n\nThis is a preview of a game that hasn't happened yet and isn't today's "
    'action — open the script with a clear "looking ahead" framing (for example '
    '"Let\'s look ahead to..." or "Looking ahead at...") rather than implying '
    "this game is happening today."
)
