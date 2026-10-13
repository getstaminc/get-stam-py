from unittest.mock import patch

from api.services.historical.trend_enrichment import enrich_game_trends


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
    assert 'continues 62% of the time' in c['description']
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
