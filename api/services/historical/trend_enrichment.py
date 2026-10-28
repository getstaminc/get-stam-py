"""Shared enrichment for trend descriptions.

Adds team names, venues, and historical continuation context to the raw
trend descriptions returned by trend services. Mirrors the enrichment logic
in jobs/send_daily_trends_digest.py so the live trends endpoint can produce
the same rich format.
"""

from .trend_context_service import get_streak_context, get_streak_stats
from .trend_collision_service import get_collision_stats, trend_dimension
from .trend_overview_service import build_market_overview


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


def _pick_primary_metric(stats: dict, home_type: str = None, away_type: str = None):
    """Pick the metric to drive the headline sentence and confidence badge.

    The language must match the trend: the sentence always names the home
    side's own trend (see _build_collision_entry), so the metric must be the
    one that trend is actually about -- a covering streak means the headline
    is about covering, never about winning outright, even if the win-rate
    number happens to be more statistically extreme. Only when home's own
    dimension has no data at all (e.g. a sport without a modeled spread) do
    we fall back to the away side's dimension, then to whichever available
    metric deviates most from 50%. A metric unrelated to either side (e.g.
    the straight-up winner on an ATS-vs-total collision) is never a
    candidate at all. The rest become secondary_rates.
    """
    candidates = []
    if stats.get('straight_up'):
        candidates.append(('straight_up', stats['straight_up']['home_side_win_rate'], stats['straight_up']['sample_size']))
    if stats.get('ats'):
        candidates.append(('ats', stats['ats']['home_side_cover_rate'], stats['ats']['sample_size']))
    if stats.get('total'):
        candidates.append(('total', stats['total']['over_rate'], stats['total']['sample_size']))
    if not candidates:
        return None

    home_dim = trend_dimension(home_type)
    for c in candidates:
        if c[0] == home_dim:
            return c

    away_dim = trend_dimension(away_type)
    relevant_dims = {d for d in (home_dim, away_dim) if d}
    relevant_candidates = [c for c in candidates if c[0] in relevant_dims]
    pool = relevant_candidates or candidates  # degrade gracefully if no relevant metric has data

    return max(pool, key=lambda c: abs(c[1] - 0.5))


def _possessive(team: str) -> str:
    return f"{team}'" if team.endswith('s') else f"{team}'s"


def _trend_word(trend: dict) -> str:
    tt, n = trend['type'], trend['count']
    return {
        'win_streak': f'{n}-game win streak',
        'loss_streak': f'{n}-game loss streak',
        'cover_streak': f'{n}-game covering streak',
        'no_cover_streak': f'{n}-game run of failing to cover',
        'over_streak': f'{n}-game OVER streak',
        'under_streak': f'{n}-game UNDER streak',
    }.get(tt, f'{tt} of {n}')


def _collision_phrase(team: str, trend: dict, venue_suffix: str = "") -> str:
    return f"{_possessive(team)} {_trend_word(trend)}{venue_suffix}"


def _build_collision_entry(home: str, home_trend: dict, home_venue: str, away: str, away_trend: dict, away_venue: str, stats: dict):
    primary = _pick_primary_metric(stats, home_trend.get('type'), away_trend.get('type'))
    if primary is None:
        return None
    primary_key, primary_rate, primary_sample = primary

    home_suffix = " at home" if home_venue == 'venue_specific' else ""
    away_suffix = " on the road" if away_venue == 'venue_specific' else ""
    matchup = (
        f"{_collision_phrase(home, home_trend, home_suffix)} meets "
        f"{_collision_phrase(away, away_trend, away_suffix)}"
    )
    pct = f"{round(primary_rate * 100)}%"
    if primary_key == 'total':
        sentence = (
            f"Historically when this collision has happened, the OVER "
            f"continues {pct} of the time"
        )
    else:
        # A noun that can sensibly "continue" in prose -- 'ats'/'ATS' can't
        # (it isn't a thing that continues), but 'cover' reads naturally
        # parallel to 'win': "...'s cover continues X%".
        metric_word = {'straight_up': 'win', 'ats': 'cover'}[primary_key]
        # A swap can only ever happen when BOTH criteria are 'general' (see
        # get_collision_stats). Whenever either side is venue_specific, no
        # swap was possible, so every matching game is a "straight" match --
        # home_side is GUARANTEED to be the literal home team, so we can
        # safely name real teams and state both sides' rates (they're
        # complementary within the same non-push denominator). Only when
        # BOTH sides are general (a real swap could have happened, so a
        # single matched instance might be either team) do we fall back to
        # the generic "trend-matching side" framing, since we can't safely
        # attribute the pooled rate to one specific team.
        can_swap = home_venue == 'general' and away_venue == 'general'
        if can_swap:
            # This rate is always about whichever side carries the home-position
            # trend (the metric is tracked as "home_side_...", which get_collision_stats
            # re-attributes to whichever physical team actually has that trend even
            # when a swap matched) -- name that trend explicitly rather than the
            # unhelpfully vague "trend-matching side." Regardless of how the
            # historical SAMPLE was pooled, TODAY's matchup is concrete: `home` is
            # literally the team carrying this trend right now, so a blunt bet
            # recommendation can always be stated -- and must flip to `away` when
            # the rate is below 50%, since that means the other side wins/covers
            # more often.
            bet_team = home if primary_rate >= 0.5 else away
            bet_verb = 'win' if primary_key == 'straight_up' else 'cover'
            sentence = (
                f"Historically when this collision has happened, the "
                f"{_trend_word(home_trend)} team's {metric_word} continues {pct} of the time "
                f"({bet_team} to {bet_verb})"
            )
        else:
            opponent_pct = f"{round((1 - primary_rate) * 100)}%"
            sentence = (
                f"Historically when this collision has happened, "
                f"{_possessive(home)} {metric_word} continues {pct} of the time "
                f"({away} {metric_word}s {opponent_pct} of the time)"
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
        'description': f"{matchup} — {sentence} — {primary_sample} historical meetings",
        'continuation_rate': primary_rate,
        'sample_size': primary_sample,
        'home_trend': {'team': home, 'type': home_trend['type'], 'count': home_trend['count'], 'venue': home_venue},
        'away_trend': {'team': away, 'type': away_trend['type'], 'count': away_trend['count'], 'venue': away_venue},
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
                # A total (over/under) trend may only collide with another total
                # trend -- never with a spread (ats) or moneyline (straight_up)
                # trend. Spread and moneyline may still collide with each other.
                home_is_total = trend_dimension(hc['trend_type']) == 'total'
                away_is_total = trend_dimension(ac['trend_type']) == 'total'
                if home_is_total != away_is_total:
                    continue
                try:
                    stats = get_collision_stats(
                        sport,
                        {'trend_type': hc['trend_type'], 'min_length': hc['min_length'], 'venue': hc['venue']},
                        {'trend_type': ac['trend_type'], 'min_length': ac['min_length'], 'venue': ac['venue']},
                    )
                    if not stats or stats.get('sample_size', 0) < 3:
                        continue
                    entry = _build_collision_entry(
                        home, hc['raw'], hc['venue'],
                        away, ac['raw'], ac['venue'],
                        stats,
                    )
                    # The overall sample_size floor above isn't sufficient on its own:
                    # the primary metric actually driving the headline/sort/description
                    # can be backed by far fewer instances than the overall collision
                    # (e.g. ats/total exclude pushes and missing lines), so it needs
                    # its own floor too.
                    if entry and entry['sample_size'] >= 3:
                        collision_trends.append(entry)
                except Exception as e:
                    print(
                        f"[trend_enrichment] collision pairing failed for {sport}: "
                        f"home={hc.get('trend_type')}/{hc.get('min_length')}/{hc.get('venue')} "
                        f"away={ac.get('trend_type')}/{ac.get('min_length')}/{ac.get('venue')}: {e}"
                    )
                    continue

        collision_trends.sort(key=lambda c: c['sample_size'], reverse=True)
        game_trends['collisionTrends'] = collision_trends[:3]

        game_trends['marketOverview'] = build_market_overview(game_trends)

    return results
