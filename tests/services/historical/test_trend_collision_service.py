from api.services.historical.trend_collision_service import _build_entering_streaks

TREND_TYPES = ('over_streak', 'under_streak', 'win_streak', 'loss_streak', 'cover_streak', 'no_cover_streak')


def _game(game_id, date, hs, aw, tl, ln, is_home):
    return {'game_id': game_id, 'game_date': date, 'hs': hs, 'aw': aw, 'tl': tl, 'ln': ln, 'is_home': is_home}


def test_general_entering_streak_walks_forward_and_resets():
    # Dodgers: W, W, L, W (chronological) -> entering win_streak before each game: 0, 1, 0, 0
    games = [
        _game('g1', '2026-01-01', 5, 1, 6, 0, True),   # win
        _game('g2', '2026-01-02', 5, 1, 6, 0, False),  # win
        _game('g3', '2026-01-03', 1, 5, 6, 0, True),   # loss
        _game('g4', '2026-01-04', 5, 1, 6, 0, False),  # win
    ]
    general, _, _ = _build_entering_streaks({'Dodgers': games}, TREND_TYPES)
    assert general['Dodgers']['g1']['win_streak'] == 0
    assert general['Dodgers']['g2']['win_streak'] == 1
    assert general['Dodgers']['g3']['win_streak'] == 2
    assert general['Dodgers']['g4']['win_streak'] == 0


def test_home_venue_entering_streak_only_counts_home_games():
    # Dodgers home games only, in order: W (g1), L (g3) -> entering win_streak: 0, 1
    # g2/g4 are away games and must not affect the home-only sequence at all.
    games = [
        _game('g1', '2026-01-01', 5, 1, 6, 0, True),   # home win
        _game('g2', '2026-01-02', 1, 5, 6, 0, False),  # away loss
        _game('g3', '2026-01-03', 1, 5, 6, 0, True),   # home loss
        _game('g4', '2026-01-04', 5, 1, 6, 0, False),  # away win
    ]
    _, home_venue, away_venue = _build_entering_streaks({'Dodgers': games}, TREND_TYPES)
    assert home_venue['Dodgers']['g1']['win_streak'] == 0
    assert home_venue['Dodgers']['g3']['win_streak'] == 1
    assert 'g2' not in home_venue['Dodgers']
    assert 'g4' not in home_venue['Dodgers']
    assert away_venue['Dodgers']['g2']['loss_streak'] == 0
    assert away_venue['Dodgers']['g4']['loss_streak'] == 1  # entering g4, away loss-streak is 1 (from g2)


def test_entering_streak_skips_games_missing_required_data_for_that_trend_type():
    # g2 has no spread ('ln' is None) -> excluded from cover_streak's sequence only.
    games = [
        _game('g1', '2026-01-01', 5, 1, 6, -3, True),   # covers (5-3=2 < 1? no: 5+(-3)=2 > 1 -> covers)
        _game('g2', '2026-01-02', 5, 1, 6, None, True),  # no spread data
        _game('g3', '2026-01-03', 5, 1, 6, -3, True),   # covers
    ]
    general, _, _ = _build_entering_streaks({'Dodgers': games}, TREND_TYPES)
    assert general['Dodgers']['g1']['cover_streak'] == 0
    assert 'cover_streak' not in general['Dodgers'].get('g2', {})
    assert general['Dodgers']['g3']['cover_streak'] == 1  # only g1 counted as prior cover
