"""Shared enrichment for trend descriptions.

Adds team names, venues, and historical continuation context to the raw
trend descriptions returned by trend services. Mirrors the enrichment logic
in jobs/send_daily_trends_digest.py so the live trends endpoint can produce
the same rich format.
"""

from .trend_context_service import get_streak_context, get_streak_stats


def _enrich_desc(t: dict, team: str, venue: str) -> str:
    """Build a descriptive trend sentence with team name and optional venue context."""
    tt, n = t['type'], t['count']
    venue_suffix = f" {venue}" if venue else ""
    if tt == 'win_streak':
        return f"{team} won {n} straight{venue_suffix}"
    if tt == 'loss_streak':
        return f"{team} lost {n} straight{venue_suffix}"
    if tt in ('over_streak', 'under_streak'):
        direction = 'OVER' if tt == 'over_streak' else 'UNDER'
        if venue:
            return f"Total went {direction} {n} straight {venue} ({team})"
        return f"Total went {direction} {n} straight ({team})"
    if tt == 'cover_streak':
        return f"{team} covered {n} straight spreads{venue_suffix}"
    if tt == 'no_cover_streak':
        return f"{team} failed to cover {n} straight spreads{venue_suffix}"
    return t['description']


def enrich_game_trends(results: list, sport: str) -> list:
    """Add team names, venues, and historical continuation context to trend descriptions.

    Mutates each trend dict's 'description' field in-place and returns results.
    """
    for game_trends in results:
        game = game_trends.get('game', {})
        home = (game.get('home') or {}).get('team', '')
        away = (game.get('away') or {}).get('team', '')
        home_ml = ((game.get('home') or {}).get('odds') or {}).get('h2h')
        away_ml = ((game.get('away') or {}).get('odds') or {}).get('h2h')

        # (category, focal_team, h2h_mode, today_ml, venue)
        trend_keys = [
            ('homeTeamTrends',      home, None,         home_ml, ''),
            ('awayTeamTrends',      away, None,         away_ml, ''),
            ('homeTeamHomeTrends',  home, None,         home_ml, 'at home'),
            ('awayTeamAwayTrends',  away, None,         away_ml, 'away'),
            ('headToHeadTrends',    None, 'gen_h2h',    None,    None),
            ('homeAtHomeH2HTrends', home, 'home_h2h',   home_ml, None),
        ]

        for key, focal_team, h2h_mode, today_ml, venue in trend_keys:
            trends = game_trends.get(key) or []
            for t in trends:
                stat_mode = 'team' if h2h_mode is None else h2h_mode
                if h2h_mode is None:
                    desc = _enrich_desc(t, focal_team, venue)
                    ctx = get_streak_context(
                        sport, t['type'], t['count'], 'team',
                        today_ml=today_ml,
                        today_team=focal_team,
                    )
                else:
                    desc = t['description']
                    if h2h_mode == 'gen_h2h':
                        if home_ml is not None and home_ml < 0:
                            ctx_ml, ctx_team = home_ml, home
                        elif away_ml is not None and away_ml < 0:
                            ctx_ml, ctx_team = away_ml, away
                        else:
                            ctx_ml, ctx_team = home_ml, home
                    else:  # home_h2h
                        ctx_ml, ctx_team = home_ml, home
                    ctx = get_streak_context(
                        sport, t['type'], t['count'], h2h_mode,
                        today_ml=ctx_ml,
                        today_team=ctx_team,
                    )
                if ctx:
                    desc = f"{desc} — {ctx}"
                t['description'] = desc

                # Attach structured stats for confidence scoring
                stats = get_streak_stats(sport, t['type'], t['count'], stat_mode)
                if stats:
                    t['continuation_rate'] = stats['rate']
                    t['sample_size'] = stats['sample_size']

    return results
