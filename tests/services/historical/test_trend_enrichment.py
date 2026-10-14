from unittest.mock import patch

import pytest

from api.services.historical.trend_enrichment import enrich_game_trends
from api.services.historical import trend_collision_service


def _game_trends():
    return {
        'game': {'home': {'team': 'Huskers', 'odds': {'h2h': -150}}, 'away': {'team': 'Sooners', 'odds': {'h2h': 130}}},
        'homeTeamTrends': [],
        'awayTeamTrends': [],
        'headToHeadTrends': [],
        'homeTeamHomeTrends': [{'type': 'win_streak', 'count': 5, 'description': 'Huskers won 5 straight at home'}],
        'awayTeamAwayTrends': [{'type': 'loss_streak', 'count': 5, 'description': 'Sooners lost 5 straight on the road'}],
        'homeAtHomeH2HTrends': [],
    }


def test_collision_trends_attached_when_stats_available():
    stats = {
        'sample_size': 14,
        'straight_up': {'home_side_win_rate': 0.62, 'sample_size': 14},
        'ats': {'home_side_cover_rate': 0.55, 'sample_size': 12},
        'total': {'over_rate': 0.48, 'sample_size': 14},
    }
    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_enrichment.get_collision_stats', return_value=stats):
        results = enrich_game_trends([_game_trends()], 'ncaaf')

    collisions = results[0]['collisionTrends']
    assert len(collisions) == 1
    c = collisions[0]
    assert c['type'] in ('win_streak', 'loss_streak')
    assert c['sample_size'] == 14
    assert c['continuation_rate'] == 0.62  # straight_up is furthest from 0.5 among the three -> primary

    # Fix #3: headline uses "the trend-matching side's win", not "the home side's win"
    assert "the trend-matching side's win continues 62% of the time" in c['description']
    assert "home side's" not in c['description']

    # Fix #4: the sample size is surfaced as a third " — "-delimited segment
    assert c['description'].endswith(' — 14 historical meetings')

    # Fix #2: venue is threaded through to both trend dicts, and the phrase mentions it.
    # Both criteria here come from the venue_specific lists (homeTeamHomeTrends/awayTeamAwayTrends).
    assert c['home_trend'] == {'team': 'Huskers', 'type': 'win_streak', 'count': 5, 'venue': 'venue_specific'}
    assert c['away_trend'] == {'team': 'Sooners', 'type': 'loss_streak', 'count': 5, 'venue': 'venue_specific'}
    assert "Huskers' 5-game win streak at home" in c['description']
    assert "Sooners' 5-game skid on the road" in c['description']

    assert c['straight_up_rate'] == 0.62
    assert c['ats_rate'] == 0.55
    assert c['total_rate'] == 0.48
    assert c['secondary_rates'] == [
        {'label': 'ATS', 'rate': 0.55, 'sample_size': 12},
        {'label': 'Total', 'rate': 0.48, 'sample_size': 14},
    ]


def test_collision_trends_empty_when_no_stats():
    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_enrichment.get_collision_stats', return_value=None):
        results = enrich_game_trends([_game_trends()], 'ncaaf')

    assert results[0]['collisionTrends'] == []


def test_collision_trends_skipped_when_sample_size_below_three():
    """Fix #1: a result with sample_size < 3 must be treated as if get_collision_stats
    returned nothing at all, even though the nested per-metric stats look confident."""
    stats = {
        'sample_size': 2,
        'straight_up': {'home_side_win_rate': 1.0, 'sample_size': 2},
    }
    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_enrichment.get_collision_stats', return_value=stats):
        results = enrich_game_trends([_game_trends()], 'ncaaf')

    assert results[0]['collisionTrends'] == []


def test_collision_trends_skipped_when_primary_metric_sample_below_three():
    """Final-review re-review finding: the overall sample_size floor (fix #1) isn't
    enough on its own -- a collision can have a healthy overall sample_size but a
    primary metric (the one actually picked for the headline/sort/description) backed
    by far fewer instances, e.g. because ats/total exclude pushes and missing lines.
    Here overall sample_size=6 passes the floor, but the metric furthest from 50%
    (ats, at 100%) is backed by only 1 instance -- that must still be suppressed,
    exactly like a sub-3 overall sample_size would be.

    Uses mismatched trend-type dimensions (win_streak vs cover_streak) so the
    same-dimension-priority rule (see test_collision_headline_uses_total_when_both_sides_are_over_under_streaks)
    doesn't force straight_up here -- this test is specifically about the
    deviation-based fallback path."""
    game_trends = {
        'game': {'home': {'team': 'Huskers', 'odds': {'h2h': -150}}, 'away': {'team': 'Sooners', 'odds': {'h2h': 130}}},
        'homeTeamTrends': [{'type': 'win_streak', 'count': 5, 'description': 'd'}],
        'awayTeamTrends': [{'type': 'cover_streak', 'count': 5, 'description': 'd'}],
        'headToHeadTrends': [],
        'homeTeamHomeTrends': [],
        'awayTeamAwayTrends': [],
        'homeAtHomeH2HTrends': [],
    }
    stats = {
        'sample_size': 6,
        'straight_up': {'home_side_win_rate': 0.5, 'sample_size': 6},
        'ats': {'home_side_cover_rate': 1.0, 'sample_size': 1},
    }
    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_enrichment.get_collision_stats', return_value=stats):
        results = enrich_game_trends([game_trends], 'ncaaf')

    assert results[0]['collisionTrends'] == []


def test_collision_headline_uses_total_when_both_sides_are_over_under_streaks():
    """A user-reported confusion: an OVER streak meeting an UNDER streak headlined
    with 'the trend-matching side's win continues 58%' -- i.e. the straight-up
    winner, which has nothing to do with the over/under collision the card is
    actually about, just because straight_up happened to deviate furthest from
    50%. When both sides share a dimension (here, 'total'), that dimension must
    be the headline regardless of which number is most extreme."""
    game_trends = {
        'game': {'home': {'team': 'Falcons', 'odds': {'h2h': -150}}, 'away': {'team': 'Bears', 'odds': {'h2h': 130}}},
        'homeTeamTrends': [{'type': 'over_streak', 'count': 3, 'description': 'd'}],
        'awayTeamTrends': [{'type': 'under_streak', 'count': 4, 'description': 'd'}],
        'headToHeadTrends': [],
        'homeTeamHomeTrends': [],
        'awayTeamAwayTrends': [],
        'homeAtHomeH2HTrends': [],
    }
    stats = {
        'sample_size': 69,
        'straight_up': {'home_side_win_rate': 0.58, 'sample_size': 69},  # furthest from 50% -- must NOT win
        'total': {'over_rate': 0.5797101449275363, 'sample_size': 69},   # shared dimension -- must win
    }
    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_enrichment.get_collision_stats', return_value=stats):
        results = enrich_game_trends([game_trends], 'nfl')

    collisions = results[0]['collisionTrends']
    assert len(collisions) == 1
    c = collisions[0]
    assert "the OVER continues 58% of the time" in c['description']
    assert "win" not in c['description']
    assert c['continuation_rate'] == pytest.approx(0.5797101449275363)


def test_collision_headline_excludes_unrelated_metric_on_mixed_dimension_pair():
    """A second user-reported case: a no_cover_streak (ATS) meeting an under_streak
    (total) headlined with 'the trend-matching side's win continues 0% of the time'
    -- the straight-up winner, which is unrelated to either side's trend (ATS and
    total), but happened to be the most extreme of the three numbers purely from
    small-sample noise (0 of 4). straight_up must never be eligible here; the
    headline must come from whichever of ATS/total (the two that ARE relevant) is
    more extreme, even though straight_up's deviation from 50% is larger."""
    game_trends = {
        'game': {'home': {'team': 'Falcons', 'odds': {'h2h': -150}}, 'away': {'team': 'Bears', 'odds': {'h2h': 130}}},
        'homeTeamHomeTrends': [{'type': 'no_cover_streak', 'count': 6, 'description': 'd'}],
        'awayTeamAwayTrends': [{'type': 'under_streak', 'count': 4, 'description': 'd'}],
        'homeTeamTrends': [], 'awayTeamTrends': [],
        'headToHeadTrends': [], 'homeAtHomeH2HTrends': [],
    }
    stats = {
        'sample_size': 4,
        'straight_up': {'home_side_win_rate': 0.0, 'sample_size': 4},  # most extreme, but IRRELEVANT -- must not be picked
        'ats': {'home_side_cover_rate': 0.25, 'sample_size': 4},        # relevant (home side's trend is ATS)
        'total': {'over_rate': 0.4, 'sample_size': 4},                  # relevant (away side's trend is total)
    }
    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_enrichment.get_collision_stats', return_value=stats):
        results = enrich_game_trends([game_trends], 'nfl')

    collisions = results[0]['collisionTrends']
    assert len(collisions) == 1
    c = collisions[0]
    # Between the two relevant metrics (ats=0.25, total=0.4), ats deviates more from 0.5 -> wins.
    assert "win" not in c['description']
    assert c['continuation_rate'] == pytest.approx(0.25)
    assert "trend-matching side's cover continues 25% of the time" in c['description']


def test_collision_trends_capped_when_more_than_3_pairs_qualify():
    """Fix #1 / #7: with more than 3 qualifying pairs, only the top 3 by sample_size
    survive, sorted descending -- the rest are dropped even though they qualified."""
    game_trends = {
        'game': {'home': {'team': 'Huskers', 'odds': {'h2h': -150}}, 'away': {'team': 'Sooners', 'odds': {'h2h': 130}}},
        'homeTeamTrends': [
            {'type': 'win_streak', 'count': 5, 'description': 'd'},
            {'type': 'cover_streak', 'count': 4, 'description': 'd'},
            {'type': 'over_streak', 'count': 3, 'description': 'd'},
        ],
        'awayTeamTrends': [
            {'type': 'loss_streak', 'count': 5, 'description': 'd'},
            {'type': 'no_cover_streak', 'count': 4, 'description': 'd'},
        ],
        'headToHeadTrends': [],
        'homeTeamHomeTrends': [],
        'awayTeamAwayTrends': [],
        'homeAtHomeH2HTrends': [],
    }
    # 3 home criteria x 2 away criteria = 6 calls, each given a distinct (and all-qualifying) sample_size.
    sample_sizes = [10, 3, 20, 4, 5, 15]
    call_order = {'n': 0}

    def fake_stats(sport, home_c, away_c):
        n = sample_sizes[call_order['n']]
        call_order['n'] += 1
        return {'sample_size': n, 'straight_up': {'home_side_win_rate': 0.6, 'sample_size': n}}

    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_enrichment.get_collision_stats', side_effect=fake_stats):
        results = enrich_game_trends([game_trends], 'ncaaf')

    collisions = results[0]['collisionTrends']
    assert len(collisions) == 3
    assert [c['sample_size'] for c in collisions] == [20, 15, 10]


def test_collision_pairing_exception_does_not_crash_other_pairings():
    """Fix #6: an exception raised while evaluating one home/away pairing must not
    prevent the other pairings in the same game (or other games) from being evaluated."""
    game_trends = {
        'game': {'home': {'team': 'Huskers', 'odds': {'h2h': -150}}, 'away': {'team': 'Sooners', 'odds': {'h2h': 130}}},
        'homeTeamTrends': [
            {'type': 'win_streak', 'count': 5, 'description': 'd'},
            {'type': 'cover_streak', 'count': 4, 'description': 'd'},
        ],
        'awayTeamTrends': [
            {'type': 'loss_streak', 'count': 5, 'description': 'd'},
        ],
        'headToHeadTrends': [],
        'homeTeamHomeTrends': [],
        'awayTeamAwayTrends': [],
        'homeAtHomeH2HTrends': [],
    }
    call_order = {'n': 0}

    def fake_stats(sport, home_c, away_c):
        call_order['n'] += 1
        if call_order['n'] == 1:
            raise RuntimeError("boom")
        return {'sample_size': 7, 'straight_up': {'home_side_win_rate': 0.6, 'sample_size': 7}}

    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_enrichment.get_collision_stats', side_effect=fake_stats):
        # Must not raise.
        results = enrich_game_trends([game_trends], 'ncaaf')

    collisions = results[0]['collisionTrends']
    assert len(collisions) == 1
    assert collisions[0]['sample_size'] == 7


def test_collision_trends_unmocked_end_to_end_through_real_collision_service():
    """Fix #7: an integration test that does NOT mock get_collision_stats -- it patches
    only the three things trend_collision_service itself pulls from trend_context_service
    (get_sport_context, SPORT_CONFIG, get_trend_types), same as
    tests/services/historical/test_trend_collision_service.py, and then calls the real
    (unmocked) enrich_game_trends end-to-end. A field-name typo on either side of the
    get_collision_stats mock boundary would not be caught by the other tests in this
    file, since they all mock that function directly."""
    trend_collision_service._collision_cache.clear()

    def wins(prefix):
        return [
            {'game_id': f'{prefix}{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 10, 'aw': 5, 'tl': None, 'ln': None, 'is_home': True}
            for i in range(1, 6)
        ]

    def losses(prefix):
        return [
            {'game_id': f'{prefix}{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 5, 'aw': 10, 'tl': None, 'ln': None, 'is_home': False}
            for i in range(1, 6)
        ]

    # Three historical general win_streak(home-side)/loss_streak(away-side) collisions,
    # mirroring test_multiple_matches_aggregate_with_push_excluded_from_its_metric in
    # test_trend_collision_service.py: G1/G3 match straight, G2 matches only via the
    # general-pool swap. 2/3 home-side wins straight-up.
    g1 = {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 25, 'ln': -3}
    g2 = {'game_id': 'g2', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 25, 'ln': -10}
    g3 = {'game_id': 'g3', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 35, 'ln': -15}

    team_games = {
        'P': wins('p') + [{**g1, 'is_home': True}],
        'Q': losses('q') + [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 10, 'aw': 20, 'tl': 25, 'ln': 3, 'is_home': False}],
        'R': losses('r') + [{**g2, 'is_home': True}],
        'S': wins('s') + [{'game_id': 'g2', 'game_date': '2026-01-01', 'hs': 10, 'aw': 20, 'tl': 25, 'ln': 10, 'is_home': False}],
        'T': wins('t') + [{**g3, 'is_home': True}],
        'U': losses('u') + [{'game_id': 'g3', 'game_date': '2026-01-01', 'hs': 10, 'aw': 20, 'tl': 35, 'ln': 15, 'is_home': False}],
    }
    home_h2h_games = {
        ('P', 'Q'): [g1],
        ('R', 'S'): [g2],
        ('T', 'U'): [g3],
    }

    def _ctx():
        return {'team_games': team_games, 'home_h2h_games': home_h2h_games}

    game_trends = {
        'game': {'home': {'team': 'Wildcats', 'odds': {'h2h': -150}}, 'away': {'team': 'Aggies', 'odds': {'h2h': 130}}},
        'homeTeamTrends': [{'type': 'win_streak', 'count': 5, 'description': 'd'}],
        'awayTeamTrends': [{'type': 'loss_streak', 'count': 5, 'description': 'd'}],
        'headToHeadTrends': [],
        'homeTeamHomeTrends': [],
        'awayTeamAwayTrends': [],
        'homeAtHomeH2HTrends': [],
    }

    with patch('api.services.historical.trend_enrichment.get_streak_context', return_value=''), \
         patch('api.services.historical.trend_enrichment.get_streak_stats', return_value=None), \
         patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx()), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'ncaaf': {'home_spread': 'home_line', 'away_spread': 'away_line'}}):
        results = enrich_game_trends([game_trends], 'ncaaf')

    collisions = results[0]['collisionTrends']
    assert len(collisions) == 1
    c = collisions[0]
    assert c['sample_size'] == 3
    assert c['continuation_rate'] == pytest.approx(2 / 3)
    assert c['home_trend'] == {'team': 'Wildcats', 'type': 'win_streak', 'count': 5, 'venue': 'general'}
    assert c['away_trend'] == {'team': 'Aggies', 'type': 'loss_streak', 'count': 5, 'venue': 'general'}
    assert "Wildcats' 5-game win streak" in c['description']
    assert "Aggies' 5-game skid" in c['description']
    assert "trend-matching side's win continues 67% of the time" in c['description']
    assert c['description'].endswith(' — 3 historical meetings')
