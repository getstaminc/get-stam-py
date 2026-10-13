import pytest

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


from api.services.historical.trend_collision_service import _build_collision_index


def test_collision_index_records_winner_ats_and_total():
    home_h2h_games = {
        ('Huskers', 'Sooners'): [
            {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 30, 'aw': 20, 'tl': 45, 'ln': -3},  # home wins, home covers (30-3=27>20), over (50>45)
        ],
    }
    general = {'Huskers': {'g1': {'win_streak': 5}}, 'Sooners': {'g1': {'loss_streak': 5}}}
    home_venue = {'Huskers': {'g1': {'win_streak': 5}}}
    away_venue = {'Sooners': {'g1': {'loss_streak': 5}}}

    index = _build_collision_index(home_h2h_games, general, home_venue, away_venue, has_spread=True)

    assert len(index) == 1
    record = index[0]
    assert record['game_id'] == 'g1'
    assert record['home']['name'] == 'Huskers'
    assert record['home']['general'] == {'win_streak': 5}
    assert record['home']['home_venue'] == {'win_streak': 5}
    assert record['away']['name'] == 'Sooners'
    assert record['away']['general'] == {'loss_streak': 5}
    assert record['away']['away_venue'] == {'loss_streak': 5}
    assert record['outcome'] == {'winner': 'home', 'ats_result': 'home', 'total_result': 'over'}


def test_collision_index_handles_ties_pushes_and_missing_data():
    home_h2h_games = {
        ('A', 'B'): [
            {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 10, 'aw': 10, 'tl': 20, 'ln': 0},   # tie, ats push, total push
            {'game_id': 'g2', 'game_date': '2026-01-02', 'hs': 10, 'aw': 8, 'tl': None, 'ln': None},  # no spread/total configured
        ],
    }
    index = _build_collision_index(home_h2h_games, {}, {}, {}, has_spread=True)
    g1, g2 = (r for r in index if r['game_id'] in ('g1', 'g2'))
    assert g1['outcome'] == {'winner': None, 'ats_result': 'push', 'total_result': 'push'}
    assert g2['outcome'] == {'winner': 'home', 'ats_result': None, 'total_result': None}  # ln/tl both None -> no spread/total data for this game


from unittest.mock import patch
from api.services.historical.trend_collision_service import get_collision_stats, _collision_cache


def _ctx(team_games, home_h2h_games):
    return {'team_games': team_games, 'home_h2h_games': home_h2h_games}


def setup_function(_):
    _collision_cache.clear()


def test_venue_specific_criteria_are_pinned_to_their_role_no_swap():
    # Home team's home-venue win_streak of 5 meets away team's away-venue loss_streak of 5.
    # A reversed arrangement (if it existed) must NOT be counted for venue-specific criteria.
    # Huskers' and Sooners' only *recorded matchup* is g1 (hs=30, aw=10, tl=35 -> total 40 is OVER,
    # ln=-3 -> home covers 27>10). Five prior home wins/away losses (dated before g1) give each team
    # an entering streak of exactly 5 at g1 — the minimum the query asks for.
    deciding = {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 30, 'aw': 10, 'tl': 35, 'ln': -3}
    home_h2h_games = {('Huskers', 'Sooners'): [deciding]}

    prior_huskers_home_wins = [
        {'game_id': f'h{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 20, 'aw': 10, 'tl': 30, 'ln': -3, 'is_home': True}
        for i in range(1, 6)
    ]
    prior_sooners_away_losses = [
        {'game_id': f's{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 10, 'aw': 20, 'tl': 30, 'ln': 3, 'is_home': False}
        for i in range(1, 6)
    ]
    team_games = {
        'Huskers': prior_huskers_home_wins + [{**deciding, 'is_home': True}],
        'Sooners': prior_sooners_away_losses + [{**deciding, 'hs': 10, 'aw': 30, 'ln': 3, 'is_home': False}],
    }

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'ncaaf': {'home_spread': 'home_line', 'away_spread': 'away_line'}}):
        stats = get_collision_stats(
            'ncaaf',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'venue_specific'},
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'venue_specific'},
        )

    assert stats['sample_size'] == 1
    assert stats['straight_up']['home_side_win_rate'] == 1.0
    assert stats['ats']['home_side_cover_rate'] == 1.0
    assert stats['total']['over_rate'] == 1.0


def test_general_criteria_pool_both_arrangements():
    # Team A enters with a 5-game win_streak as the home_h2h AWAY team (A@B), and B enters with a
    # 5-game loss_streak as the home_h2h HOME team. Since both criteria are general, querying
    # "home: win_streak>=5, away: loss_streak>=5" must still match via the swapped arrangement.
    prior_a_wins = [
        {'game_id': f'a{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 20, 'aw': 10, 'tl': 30, 'ln': None, 'is_home': True}
        for i in range(1, 6)
    ]
    prior_b_losses = [
        {'game_id': f'b{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 10, 'aw': 20, 'tl': 30, 'ln': None, 'is_home': True}
        for i in range(1, 6)
    ]
    # The deciding game: B is home, A is away (A still carries its general win_streak, B its general loss_streak)
    deciding = {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 15, 'aw': 25, 'tl': 30, 'ln': None}
    team_games = {
        'A': prior_a_wins + [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 25, 'aw': 15, 'tl': 30, 'ln': None, 'is_home': False}],
        'B': prior_b_losses + [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 15, 'aw': 25, 'tl': 30, 'ln': None, 'is_home': True}],
    }
    home_h2h_games = {('B', 'A'): [deciding]}  # the prior games belong to other opponents; only g1 is B-vs-A

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'mlb': {}}):
        stats = get_collision_stats(
            'mlb',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'general'},
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'general'},
        )

    assert stats['sample_size'] == 1
    # A (literal away team) satisfied the "home" criterion via the swap, and A lost this game (15<25 means
    # literal home B=15 lost, literal away A=25 won) -> home_side (=A) won.
    assert stats['straight_up']['home_side_win_rate'] == 1.0


def test_below_threshold_does_not_match():
    team_games = {
        'A': [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 30, 'ln': None, 'is_home': True}],
        'B': [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 10, 'aw': 20, 'tl': 30, 'ln': None, 'is_home': False}],
    }
    home_h2h_games = {('A', 'B'): [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 30, 'ln': None}]}

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'mlb': {}}):
        stats = get_collision_stats(
            'mlb',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'general'},  # A has 0 entering win_streak (first game)
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'general'},
        )

    assert stats is None


def test_no_sport_context_returns_none():
    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=None):
        assert get_collision_stats(
            'mlb',
            {'trend_type': 'win_streak', 'min_length': 3, 'venue': 'general'},
            {'trend_type': 'loss_streak', 'min_length': 3, 'venue': 'general'},
        ) is None


def test_venue_specific_pair_does_not_match_via_general_swap():
    """both_general gate (fix round 1, finding #1): a venue_specific/venue_specific
    query must NEVER match through a role-swapped arrangement, even when the swap
    condition would be satisfied using general pools. Here H (literal home team)
    carries a general LOSS streak (the away_criterion's profile) and A (literal
    away team) carries a general WIN streak (the home_criterion's profile) -- the
    "hot"/"cold" streaks sit on the physically opposite roles from what this
    venue_specific query asks for. Neither team has the matching VENUE-PINNED
    streak either (H has no prior home games at all; A has no prior away games
    at all), so straight fails too. If `if not straight and both_general:` were
    ever weakened to `if not straight:`, this would incorrectly match via the
    general-pool swap -- see the sibling test below, which proves the same
    fixture DOES match once both criteria are 'general'."""
    prior_h_losses = [
        {'game_id': f'h{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 5, 'aw': 10, 'tl': None, 'ln': None, 'is_home': False}
        for i in range(1, 6)
    ]
    prior_a_wins = [
        {'game_id': f'a{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 10, 'aw': 5, 'tl': None, 'ln': None, 'is_home': True}
        for i in range(1, 6)
    ]
    deciding = {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 25, 'ln': -3}
    team_games = {
        'H': prior_h_losses + [{**deciding, 'is_home': True}],
        'A': prior_a_wins + [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 10, 'aw': 20, 'tl': 25, 'ln': 3, 'is_home': False}],
    }
    home_h2h_games = {('H', 'A'): [deciding]}

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'ncaaf': {'home_spread': 'home_line', 'away_spread': 'away_line'}}):
        stats = get_collision_stats(
            'ncaaf',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'venue_specific'},
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'venue_specific'},
        )

    assert stats is None


def test_general_pair_matches_via_swap_with_same_opposite_role_fixture():
    """Sibling to the test above: the identical fixture, but both criteria are
    'general'. Since general criteria carry no venue identity, the swapped
    arrangement (A satisfies the win_streak slot, H satisfies the loss_streak
    slot) is a legitimate match. This proves the `and both_general` gate is
    load-bearing: general queries still pool across both arrangements as
    designed, while the venue_specific/venue_specific version of this exact
    fixture (previous test) correctly returns None."""
    prior_h_losses = [
        {'game_id': f'h{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 5, 'aw': 10, 'tl': None, 'ln': None, 'is_home': False}
        for i in range(1, 6)
    ]
    prior_a_wins = [
        {'game_id': f'a{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 10, 'aw': 5, 'tl': None, 'ln': None, 'is_home': True}
        for i in range(1, 6)
    ]
    deciding = {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 25, 'ln': -3}
    team_games = {
        'H': prior_h_losses + [{**deciding, 'is_home': True}],
        'A': prior_a_wins + [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 10, 'aw': 20, 'tl': 25, 'ln': 3, 'is_home': False}],
    }
    home_h2h_games = {('H', 'A'): [deciding]}

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'ncaaf': {'home_spread': 'home_line', 'away_spread': 'away_line'}}):
        stats = get_collision_stats(
            'ncaaf',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'general'},
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'general'},
        )

    assert stats is not None
    assert stats['sample_size'] == 1
    # Match came via swap (home_side_is_literal_home=False): the literal AWAY team (A)
    # satisfied the home_criterion, and A actually LOST the literal game (H=20 beat A=10
    # straight-up) -> home_side (A) lost -> home_side_win_rate must be 0.0, not 1.0. A
    # sign-flip bug in the home_side_won expression would silently invert this to 1.0.
    assert stats['straight_up']['home_side_win_rate'] == 0.0


def test_mixed_general_and_venue_specific_criteria_match_straight():
    """No prior coverage existed for a mixed general/venue_specific pair (fix
    round 1, finding #2a). H2 (home) straight-matches on a general win_streak,
    A2 (away) straight-matches on an away_venue (venue_specific) loss_streak --
    both_general is False here, but straight alone is enough."""
    prior_h2_wins = [
        {'game_id': f'h{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 10, 'aw': 5, 'tl': None, 'ln': None, 'is_home': True}
        for i in range(1, 6)
    ]
    prior_a2_away_losses = [
        {'game_id': f'a{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 5, 'aw': 10, 'tl': None, 'ln': None, 'is_home': False}
        for i in range(1, 6)
    ]
    deciding = {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 25, 'ln': -3}
    team_games = {
        'H2': prior_h2_wins + [{**deciding, 'is_home': True}],
        'A2': prior_a2_away_losses + [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 10, 'aw': 20, 'tl': 25, 'ln': 3, 'is_home': False}],
    }
    home_h2h_games = {('H2', 'A2'): [deciding]}

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'ncaaf': {'home_spread': 'home_line', 'away_spread': 'away_line'}}):
        stats = get_collision_stats(
            'ncaaf',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'general'},
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'venue_specific'},
        )

    assert stats is not None
    assert stats['sample_size'] == 1
    assert stats['straight_up']['home_side_win_rate'] == 1.0


def test_mixed_general_and_venue_specific_criteria_never_swap():
    """Fix round 1, finding #2b: a mixed general/venue_specific pair must never
    match via a swap, even on a fixture where the raw swap arithmetic (which
    always reads the *general* pools on both sides, regardless of what the
    criteria's own 'venue' fields say) would line up. Reuses the exact
    opposite-role fixture from the venue_specific/venue_specific test above --
    H's general loss_streak is 5 and A's general win_streak is 5, which is
    exactly what the swap formula would check -- but because one side here is
    'venue_specific', both_general is False, so the swap is never attempted and
    the result must be None."""
    prior_h_losses = [
        {'game_id': f'h{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 5, 'aw': 10, 'tl': None, 'ln': None, 'is_home': False}
        for i in range(1, 6)
    ]
    prior_a_wins = [
        {'game_id': f'a{i}', 'game_date': f'2025-12-{i:02d}', 'hs': 10, 'aw': 5, 'tl': None, 'ln': None, 'is_home': True}
        for i in range(1, 6)
    ]
    deciding = {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 25, 'ln': -3}
    team_games = {
        'H': prior_h_losses + [{**deciding, 'is_home': True}],
        'A': prior_a_wins + [{'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 10, 'aw': 20, 'tl': 25, 'ln': 3, 'is_home': False}],
    }
    home_h2h_games = {('H', 'A'): [deciding]}

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'ncaaf': {'home_spread': 'home_line', 'away_spread': 'away_line'}}):
        stats = get_collision_stats(
            'ncaaf',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'general'},
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'venue_specific'},
        )

    assert stats is None


def test_multiple_matches_aggregate_with_push_excluded_from_its_metric():
    """Fix round 1, finding #3: 3 historical games match the same general/general
    query -- one matches straight (P/Q), one matches ONLY via the swap (R/S), and
    one matches straight again (T/U). G2 (R/S) has an ATS push. Values are chosen
    so a sign-flip bug in home_side bookkeeping for the swapped game would
    visibly change the straight_up rate (2 wins / 3 = 0.667, not a trivial
    0.0/1.0), the push is excluded from the ats denominator (2, not 3) while
    still counting toward the overall sample_size (3), and the ats/total rates
    are themselves non-trivial (0.5 and 0.667) rather than accidentally-correct
    0.0/1.0 values."""
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

    # G1: P (home) straight-matches (win_streak>=5 general), Q (away) straight-matches
    # (loss_streak>=5 general). P wins straight-up, covers, and the total goes over.
    g1 = {'game_id': 'g1', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 25, 'ln': -3}
    # G2: R (home) is on a general LOSS streak and S (away) is on a general WIN streak --
    # the opposite of what straight needs -- so this matches ONLY via the swap (S satisfies
    # the home_criterion's win_streak slot, R satisfies the away_criterion's loss_streak
    # slot). R wins the literal game, so the swapped home_side (S) LOSES. ATS is a push.
    g2 = {'game_id': 'g2', 'game_date': '2026-01-01', 'hs': 20, 'aw': 10, 'tl': 25, 'ln': -10}
    # G3: T (home) straight-matches like G1 and wins straight-up, but does NOT cover
    # (big home line) and the total goes under -- keeps the ats/total rates non-trivial.
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

    with patch('api.services.historical.trend_collision_service.get_sport_context', return_value=_ctx(team_games, home_h2h_games)), \
         patch('api.services.historical.trend_collision_service.get_trend_types', return_value=('win_streak', 'loss_streak')), \
         patch('api.services.historical.trend_collision_service.SPORT_CONFIG', {'ncaaf': {'home_spread': 'home_line', 'away_spread': 'away_line'}}):
        stats = get_collision_stats(
            'ncaaf',
            {'trend_type': 'win_streak', 'min_length': 5, 'venue': 'general'},
            {'trend_type': 'loss_streak', 'min_length': 5, 'venue': 'general'},
        )

    assert stats['sample_size'] == 3
    # G1 win (P, straight), G2 loss (S via swap -- literal home R won, so swapped
    # home_side S lost), G3 win (T, straight) -> 2/3.
    assert stats['straight_up']['sample_size'] == 3
    assert stats['straight_up']['home_side_win_rate'] == pytest.approx(2 / 3)
    # G2 is a push -> excluded from the ats denominator (2, not 3) though still counted
    # in the overall sample_size (3) above. G1 covers (win), G3 does not (loss) -> 1/2.
    assert stats['ats']['sample_size'] == 2
    assert stats['ats']['home_side_cover_rate'] == pytest.approx(0.5)
    # G1 over, G2 over, G3 under -> 2/3.
    assert stats['total']['sample_size'] == 3
    assert stats['total']['over_rate'] == pytest.approx(2 / 3)


def test_unrecognized_venue_value_raises_value_error():
    """Fix round 1, finding #4: a typo'd venue (e.g. 'generl', 'home_venue')
    must raise ValueError rather than silently falling through to the general
    pool. Checked on both the home and away criterion."""
    with pytest.raises(ValueError):
        get_collision_stats(
            'mlb',
            {'trend_type': 'win_streak', 'min_length': 3, 'venue': 'generl'},
            {'trend_type': 'loss_streak', 'min_length': 3, 'venue': 'general'},
        )

    with pytest.raises(ValueError):
        get_collision_stats(
            'mlb',
            {'trend_type': 'win_streak', 'min_length': 3, 'venue': 'general'},
            {'trend_type': 'loss_streak', 'min_length': 3, 'venue': 'home_venue'},
        )
