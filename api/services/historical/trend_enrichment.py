"""Shared enrichment for trend descriptions.

Adds team names, venues, and historical continuation context to the raw
trend descriptions returned by trend services. Mirrors the enrichment logic
in jobs/send_daily_trends_digest.py so the live trends endpoint can produce
the same rich format.
"""

from .trend_context_service import get_streak_context, get_streak_stats
from .trend_collision_service import get_collision_stats


def _enrich_desc(t: dict, team: str, venue: str) -> str:
    """Build a descriptive trend sentence with team name and optional venue context."""
    tt, n = t['type'], t['count']
    venue_suffix = f" {venue}" if venue else ""
    if tt == 'win_streak':
        return f"{team} won {n} straight{venue_suffix}"
    if tt == 'loss_streak':
        return f"{team} lost {n} straight{venue_suffix}"
    if tt == 'draw_streak':
        return f"{team} drew {n} straight{venue_suffix}"
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


def _collision_rate_label(key: str) -> str:
    return {'straight_up': 'Win', 'ats': 'ATS', 'total': 'Total'}[key]


def _pick_primary_metric(stats: dict):
    """Pick whichever of straight_up/ats/total deviates most from 50% to drive
    the headline sentence and confidence badge; the rest become secondary_rates."""
    candidates = []
    if stats.get('straight_up'):
        candidates.append(('straight_up', stats['straight_up']['home_side_win_rate'], stats['straight_up']['sample_size']))
    if stats.get('ats'):
        candidates.append(('ats', stats['ats']['home_side_cover_rate'], stats['ats']['sample_size']))
    if stats.get('total'):
        candidates.append(('total', stats['total']['over_rate'], stats['total']['sample_size']))
    if not candidates:
        return None
    return max(candidates, key=lambda c: abs(c[1] - 0.5))


def _collision_phrase(team: str, trend: dict) -> str:
    tt, n = trend['type'], trend['count']
    word = {
        'win_streak': f'{n}-game win streak',
        'loss_streak': f'{n}-game skid',
        'cover_streak': f'{n}-game covering streak',
        'no_cover_streak': f'{n}-game run of failing to cover',
        'over_streak': f'{n}-game OVER streak',
        'under_streak': f'{n}-game UNDER streak',
    }.get(tt, f'{tt} of {n}')
    return f"{team}'s {word}"


def _build_collision_entry(home: str, home_trend: dict, away: str, away_trend: dict, stats: dict):
    primary = _pick_primary_metric(stats)
    if primary is None:
        return None
    primary_key, primary_rate, primary_sample = primary

    matchup = f"{_collision_phrase(home, home_trend)} meets {_collision_phrase(away, away_trend)}"
    pct = f"{round(primary_rate * 100)}%"
    sentence = (
        f"Historically when this collision has happened, the home side's "
        f"{_collision_rate_label(primary_key).lower()} continues {pct} of the time "
        f"({primary_sample} instances)"
    )

    secondary_rates = []
    for key in ('straight_up', 'ats', 'total'):
        if key == primary_key or not stats.get(key):
            continue
        rate_field = {'straight_up': 'home_side_win_rate', 'ats': 'home_side_cover_rate', 'total': 'over_rate'}[key]
        secondary_rates.append({
            'label': _collision_rate_label(key),
            'rate': stats[key][rate_field],
            'sample_size': stats[key]['sample_size'],
        })

    return {
        'type': 'win_streak' if primary_rate >= 0.5 else 'loss_streak',
        'count': max(home_trend['count'], away_trend['count']),
        'description': f"{matchup} — {sentence}",
        'continuation_rate': primary_rate,
        'sample_size': primary_sample,
        'home_trend': {'team': home, 'type': home_trend['type'], 'count': home_trend['count']},
        'away_trend': {'team': away, 'type': away_trend['type'], 'count': away_trend['count']},
        'straight_up_rate': stats['straight_up']['home_side_win_rate'] if stats.get('straight_up') else None,
        'ats_rate': stats['ats']['home_side_cover_rate'] if stats.get('ats') else None,
        'total_rate': stats['total']['over_rate'] if stats.get('total') else None,
        'secondary_rates': secondary_rates,
    }


def _collision_criteria(trends: list, venue: str) -> list:
    return [{'trend_type': t['type'], 'min_length': t['count'], 'venue': venue, 'raw': t} for t in trends]


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

        home_criteria = (
            _collision_criteria(game_trends.get('homeTeamTrends') or [], 'general')
            + _collision_criteria(game_trends.get('homeTeamHomeTrends') or [], 'venue_specific')
        )
        away_criteria = (
            _collision_criteria(game_trends.get('awayTeamTrends') or [], 'general')
            + _collision_criteria(game_trends.get('awayTeamAwayTrends') or [], 'venue_specific')
        )

        collision_trends = []
        for hc in home_criteria:
            for ac in away_criteria:
                stats = get_collision_stats(
                    sport,
                    {'trend_type': hc['trend_type'], 'min_length': hc['min_length'], 'venue': hc['venue']},
                    {'trend_type': ac['trend_type'], 'min_length': ac['min_length'], 'venue': ac['venue']},
                )
                if not stats:
                    continue
                entry = _build_collision_entry(home, hc['raw'], away, ac['raw'], stats)
                if entry:
                    collision_trends.append(entry)
        game_trends['collisionTrends'] = collision_trends

    return results
