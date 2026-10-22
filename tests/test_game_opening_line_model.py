"""Pins the game_opening_lines schema the migration in Task 1 must produce —
no DB needed, this only inspects the SQLAlchemy model's metadata."""
from models.game_opening_line import GameOpeningLine


def test_table_name():
    assert GameOpeningLine.__tablename__ == 'game_opening_lines'


def test_unique_constraint_is_on_sport_and_event_id():
    constraint = next(
        c for c in GameOpeningLine.__table__.constraints
        if c.name == 'uq_game_opening_lines_sport_event'
    )
    assert {col.name for col in constraint.columns} == {'sport', 'odds_event_id'}


def test_has_all_expected_columns():
    column_names = {col.name for col in GameOpeningLine.__table__.columns}
    assert column_names == {
        'id', 'sport', 'odds_event_id', 'home_team', 'away_team', 'commence_time',
        'opening_snapshot_time', 'home_spread_point', 'home_spread_price',
        'away_spread_point', 'away_spread_price', 'home_moneyline', 'away_moneyline',
        'total_point', 'over_price', 'under_price', 'created_at',
    }
