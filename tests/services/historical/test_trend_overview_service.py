import pytest

from api.services.historical.trend_overview_service import build_market_overview


def _base_game_trends(**overrides):
    game_trends = {
        'game': {'home': {'team': 'Giants'}, 'away': {'team': 'Saints'}},
        'homeTeamTrends': [],
        'awayTeamTrends': [],
        'homeTeamHomeTrends': [],
        'awayTeamAwayTrends': [],
        'headToHeadTrends': [],
        'homeAtHomeH2HTrends': [],
        'collisionTrends': [],
    }
    game_trends.update(overrides)
    return game_trends


def test_no_trends_anywhere_returns_none():
    assert build_market_overview(_base_game_trends()) is None


def test_single_home_win_streak_leans_home_for_moneyline():
    """Home team's own win_streak continuing IS home winning -- no flip needed."""
    game_trends = _base_game_trends(homeTeamTrends=[
        {'type': 'win_streak', 'count': 4, 'description': 'd', 'continuation_rate': 0.8, 'sample_size': 50},
    ])
    overview = build_market_overview(game_trends)
    assert overview['moneyline']['lean'] == 'Giants'
    assert overview['moneyline']['probability'] == pytest.approx(0.8)
    assert overview['moneyline']['sample_size'] == 50
    assert overview['moneyline']['trend_count'] == 1
    assert 'spread' not in overview
    assert 'total' not in overview


def test_home_loss_streak_flips_to_favor_away_team():
    """Home team's own loss_streak continuing means home LOSES again -- so the
    moneyline lean is the AWAY team, at the complementary probability."""
    game_trends = _base_game_trends(homeTeamTrends=[
        {'type': 'loss_streak', 'count': 3, 'description': 'd', 'continuation_rate': 0.7, 'sample_size': 40},
    ])
    overview = build_market_overview(game_trends)
    assert overview['moneyline']['lean'] == 'Saints'
    assert overview['moneyline']['probability'] == pytest.approx(0.7)


def test_away_win_streak_flips_relative_to_home_perspective():
    """An AWAY team's own win_streak continuing means the away team wins --
    which from the home-centric 'probability home wins' framing is 1 - rate,
    but the lean should still correctly point at the away team since its own
    rate (0.75) is what's above 50%."""
    game_trends = _base_game_trends(awayTeamTrends=[
        {'type': 'win_streak', 'count': 5, 'description': 'd', 'continuation_rate': 0.75, 'sample_size': 60},
    ])
    overview = build_market_overview(game_trends)
    assert overview['moneyline']['lean'] == 'Saints'
    assert overview['moneyline']['probability'] == pytest.approx(0.75)


def test_away_loss_streak_flips_to_favor_home_team():
    game_trends = _base_game_trends(awayTeamTrends=[
        {'type': 'loss_streak', 'count': 3, 'description': 'd', 'continuation_rate': 0.6, 'sample_size': 30},
    ])
    overview = build_market_overview(game_trends)
    assert overview['moneyline']['lean'] == 'Giants'
    assert overview['moneyline']['probability'] == pytest.approx(0.6)


def test_weighted_blend_across_multiple_trends_same_market():
    """Two trends both bearing on moneyline, weighted by sample_size:
    home win_streak (0.8 home-favorable, n=10) and away loss_streak
    (0.6 home-favorable, n=90) -> blended = (0.8*10 + 0.6*90) / 100 = 0.62."""
    game_trends = _base_game_trends(
        homeTeamTrends=[{'type': 'win_streak', 'count': 4, 'description': 'd', 'continuation_rate': 0.8, 'sample_size': 10}],
        awayTeamTrends=[{'type': 'loss_streak', 'count': 3, 'description': 'd', 'continuation_rate': 0.6, 'sample_size': 90}],
    )
    overview = build_market_overview(game_trends)
    assert overview['moneyline']['probability'] == pytest.approx(0.62)
    assert overview['moneyline']['lean'] == 'Giants'
    assert overview['moneyline']['sample_size'] == 100
    assert overview['moneyline']['trend_count'] == 2


def test_cover_and_no_cover_streaks_feed_the_spread_market():
    game_trends = _base_game_trends(
        homeTeamHomeTrends=[{'type': 'cover_streak', 'count': 4, 'description': 'd', 'continuation_rate': 0.47, 'sample_size': 280}],
        awayTeamAwayTrends=[{'type': 'cover_streak', 'count': 7, 'description': 'd', 'continuation_rate': 0.48, 'sample_size': 31}],
    )
    overview = build_market_overview(game_trends)
    # Home: cover_streak continuing is home-favorable directly (0.47).
    # Away: cover_streak continuing is favorable to AWAY, so home-favorable = 1-0.48 = 0.52.
    # Blended home-favorable = (0.47*280 + 0.52*31) / 311 ≈ 0.475, which is BELOW 0.5 --
    # so the lean flips to Saints, reporting the complementary (1 - blended) probability.
    blended_home_favorable = (0.47 * 280 + 0.52 * 31) / 311
    assert overview['spread']['lean'] == 'Saints'
    assert overview['spread']['probability'] == pytest.approx(1 - blended_home_favorable)


def test_over_under_streaks_feed_the_total_market_regardless_of_side():
    """over_streak/under_streak don't depend on which team they're attached to --
    the total market is about the combined score, not either team."""
    game_trends = _base_game_trends(
        homeTeamTrends=[{'type': 'over_streak', 'count': 3, 'description': 'd', 'continuation_rate': 0.55, 'sample_size': 20}],
        awayTeamTrends=[{'type': 'under_streak', 'count': 4, 'description': 'd', 'continuation_rate': 0.4, 'sample_size': 15}],
    )
    overview = build_market_overview(game_trends)
    # home over_streak -> over_prob = 0.55 directly.
    # away under_streak continuing -> under happens 0.4 of the time -> over_prob = 1-0.4 = 0.6.
    expected = (0.55 * 20 + 0.6 * 15) / 35
    assert overview['total']['probability'] == pytest.approx(expected)
    assert overview['total']['lean'] == 'Over'


def test_total_lean_is_under_when_blended_probability_below_half():
    game_trends = _base_game_trends(homeTeamTrends=[
        {'type': 'under_streak', 'count': 3, 'description': 'd', 'continuation_rate': 0.7, 'sample_size': 25},
    ])
    overview = build_market_overview(game_trends)
    assert overview['total']['lean'] == 'Under'
    assert overview['total']['probability'] == pytest.approx(0.7)


def test_collision_trend_continuation_rate_used_directly_no_flip():
    """Collision entries are already home-side-outcome-framed (not streak-direction
    framed), so their continuation_rate is used as-is for whichever dimension the
    home_trend's own type maps to -- no win/loss or home/away flip."""
    game_trends = _base_game_trends(collisionTrends=[
        {
            'type': 'win_streak', 'count': 5, 'description': 'd',
            'continuation_rate': 0.68, 'sample_size': 161,
            'home_trend': {'team': 'Giants', 'type': 'cover_streak', 'count': 3, 'venue': 'general'},
            'away_trend': {'team': 'Saints', 'type': 'loss_streak', 'count': 3, 'venue': 'general'},
        },
    ])
    overview = build_market_overview(game_trends)
    # home_trend's type is cover_streak -> dimension 'ats' -> feeds spread, not moneyline.
    assert 'spread' in overview
    assert overview['spread']['probability'] == pytest.approx(0.68)
    assert overview['spread']['lean'] == 'Giants'
    assert 'moneyline' not in overview


def test_draw_streak_and_missing_stats_are_skipped_gracefully():
    game_trends = _base_game_trends(homeTeamTrends=[
        {'type': 'draw_streak', 'count': 3, 'description': 'd', 'continuation_rate': 0.5, 'sample_size': 10},
        {'type': 'win_streak', 'count': 4, 'description': 'd'},  # no continuation_rate/sample_size at all
        {'type': 'loss_streak', 'count': 2, 'description': 'd', 'continuation_rate': 0.6},  # no sample_size
    ])
    assert build_market_overview(game_trends) is None


def test_supporting_description_cites_the_largest_sample_trend():
    game_trends = _base_game_trends(
        homeTeamTrends=[{'type': 'win_streak', 'count': 4, 'description': 'small one', 'continuation_rate': 0.9, 'sample_size': 5}],
        awayTeamTrends=[{'type': 'loss_streak', 'count': 3, 'description': 'big one', 'continuation_rate': 0.55, 'sample_size': 500}],
    )
    overview = build_market_overview(game_trends)
    assert overview['moneyline']['supporting_description'] == 'big one'
