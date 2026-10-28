from api.services.historical.trend_context_service import get_trend_types


def test_get_trend_types_includes_cover_for_sports_with_real_spread():
    assert get_trend_types('nfl') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak', 'cover_streak', 'no_cover_streak')
    assert get_trend_types('ncaaf') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak', 'cover_streak', 'no_cover_streak')
    assert get_trend_types('soccer_epl') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak', 'cover_streak', 'no_cover_streak')


def test_get_trend_types_excludes_cover_for_sports_without_real_spread():
    assert get_trend_types('mlb') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak')
    assert get_trend_types('nba') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak')
    assert get_trend_types('nhl') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak')


def test_get_trend_types_unknown_sport_returns_base_only():
    assert get_trend_types('not_a_sport') == ('over_streak', 'under_streak', 'win_streak', 'loss_streak')
