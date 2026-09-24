"""
Shared helpers for the trend-video script generators (MLB/NFL/NCAAF) and the
weekly scheduler (plan_daily_trend_videos.py) that drives them.
"""

from datetime import datetime, timedelta

from api.services.historical.trend_context_service import (
    find_odds_whiplash_trend,
    get_recent_series_games,
)


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


def _trend_alignment_note(entry, home_team, away_team, tiktok=False):
    """Idea: if both teams carry their own over/under streak into the game,
    note whether those two signals reinforce each other (same direction) or
    contradict each other (opposite directions) on tonight's total. No new
    continuation-rate stat here on purpose — just a plain observation for the
    model to weigh itself, not a scored/ranked trend of its own. tiktok=True
    swaps OVER/UNDER wording for high-/low-scoring, matching how over_streak/
    under_streak trends are already sanitized elsewhere for TikTok.
    """
    home_ou = next((t for t in (entry.get("homeTeamTrends") or []) if t["type"] in ("over_streak", "under_streak")), None)
    away_ou = next((t for t in (entry.get("awayTeamTrends") or []) if t["type"] in ("over_streak", "under_streak")), None)
    if not home_ou or not away_ou:
        return None

    def label(t):
        if tiktok:
            return "high-scoring" if t["type"] == "over_streak" else "low-scoring"
        return "OVER" if t["type"] == "over_streak" else "UNDER"

    if home_ou["type"] == away_ou["type"]:
        return (
            f"{home_team} and {away_team} are both trending {label(home_ou)} lately "
            f"({home_team} {home_ou['count']} straight, {away_team} {away_ou['count']} straight) — "
            "these are reinforcing signals pointing the same way on the total."
        )
    return (
        f"{home_team} has been trending {label(home_ou)} ({home_ou['count']} straight) while "
        f"{away_team} has been trending {label(away_ou)} ({away_ou['count']} straight) — "
        "these two signals contradict each other on the total, worth weighing which one actually matters more."
    )


def gather_extra_context(entry, sport, game, home_team, away_team, tiktok=False):
    """Collect supporting-context notes for a game — plain descriptive
    strings the model can weave in if useful, NOT scored/ranked trends
    competing for the primary-trend slot (that stays whatever
    rank_game_trends already picked). Covers:
      - the odds-whiplash situational patterns (find_odds_whiplash_trend)
      - the over/under trend-alignment note above
    Returns a list of strings (possibly empty) — the caller only renders an
    "Additional context" prompt section when this is non-empty. (The third
    idea, live-series awareness, is handled separately by
    annotate_live_series, which enriches an existing H2H trend's own
    description in place rather than adding a new note here.)
    """
    notes = []

    home = game["home"]
    away = game["away"]
    home_ml = (home.get("odds") or {}).get("h2h")
    away_ml = (away.get("odds") or {}).get("h2h")
    home_trend = find_odds_whiplash_trend(sport, home["team"], home_ml, True)
    if home_trend:
        notes.append(home_trend["description"])
    away_trend = find_odds_whiplash_trend(sport, away["team"], away_ml, False)
    if away_trend:
        notes.append(away_trend["description"])

    alignment_note = _trend_alignment_note(entry, home_team, away_team, tiktok=tiktok)
    if alignment_note:
        notes.append(alignment_note)

    return notes


_H2H_SOURCES = ("headToHeadTrends", "homeAtHomeH2HTrends")


def annotate_live_series(trends, sport, home_team, away_team, date_str):
    """For any H2H win/loss-streak trend in `trends`, check whether some of
    the streak's games were played within the last week (i.e. this is an
    active, ongoing series between these two teams, not just an H2H streak
    spread across older, separate meetings) and if so append a note to its
    description. Mutates the trend dicts in place; returns `trends`.
    """
    for t in trends:
        if t.get("type") not in ("win_streak", "loss_streak") or t.get("_source") not in _H2H_SOURCES:
            continue
        recent = get_recent_series_games(sport, home_team, away_team, date_str)
        if not recent:
            continue
        n = len(recent)
        if n == 1:
            note = " — including their most recent meeting just days ago"
        else:
            note = f" — including their last {n} meetings, all within the past week"
        t["description"] = t["description"] + note
    return trends


def format_extra_context(notes):
    """Render gather_extra_context()'s notes as an optional prompt section, or
    "" if there are none. Deliberately separate from the numbered/scored
    trend list — these are supporting observations the model can weave in if
    useful, not primary-trend candidates."""
    if not notes:
        return ""
    bullet_lines = "\n".join(f"- {n}" for n in notes)
    return (
        "\nAdditional context (weave in naturally if it strengthens or "
        "complicates the story — don't force it in if it doesn't fit):\n"
        f"{bullet_lines}\n"
    )


LOOKAHEAD_PROMPT_NOTE = (
    "\n\nThis is a preview of a game that hasn't happened yet and isn't today's "
    'action — open the script with a clear "looking ahead" framing (for example '
    '"Let\'s look ahead to..." or "Looking ahead at...") rather than implying '
    "this game is happening today."
)
