"""2fix neutral site games

Revision ID: a1f64c3aeeb7
Revises: 61a15c7f6166
Create Date: 2025-06-11 21:35:06.750887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = 'a1f64c3aeeb7'
down_revision: Union[str, None] = '61a15c7f6166'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    conn = op.get_bind()

    # List of specific records to update
    records_to_update = [
        {'game_id': 18388, 'game_date': '2024-11-10', 'home_team_id': 50, 'away_team_id': 56},
        {'game_id': 18403, 'game_date': '2024-10-20', 'home_team_id': 58, 'away_team_id': 65},
        {'game_id': 18338, 'game_date': '2023-11-12', 'home_team_id': 34, 'away_team_id': 58},
        {'game_id': 18343, 'game_date': '2023-10-15', 'home_team_id': 36, 'away_team_id': 64},
        {'game_id': 18378, 'game_date': '2023-10-08', 'home_team_id': 47, 'away_team_id': 65},
        {'game_id': 18363, 'game_date': '2023-02-12', 'home_team_id': 43, 'away_team_id': 51},
        {'game_id': 18357, 'game_date': '2022-11-13', 'home_team_id': 41, 'away_team_id': 57},
        {'game_id': 18404, 'game_date': '2022-10-30', 'home_team_id': 61, 'away_team_id': 65},
        {'game_id': 18373, 'game_date': '2021-10-17', 'home_team_id': 46, 'away_team_id': 65},
        {'game_id': 18362, 'game_date': '2021-02-07', 'home_team_id': 43, 'away_team_id': 57},
        {'game_id': 18356, 'game_date': '2021-01-03', 'home_team_id': 41, 'away_team_id': 48},
        {'game_id': 18368, 'game_date': '2020-12-13', 'home_team_id': 44, 'away_team_id': 48},
        {'game_id': 18377, 'game_date': '2020-12-07', 'home_team_id': 47, 'away_team_id': 48},
        {'game_id': 18361, 'game_date': '2020-02-02', 'home_team_id': 43, 'away_team_id': 48},
        {'game_id': 18340, 'game_date': '2019-11-03', 'home_team_id': 35, 'away_team_id': 65},
        {'game_id': 18348, 'game_date': '2019-10-27', 'home_team_id': 38, 'away_team_id': 49},
        {'game_id': 18399, 'game_date': '2019-10-13', 'home_team_id': 56, 'away_team_id': 57},
        {'game_id': 18396, 'game_date': '2019-10-06', 'home_team_id': 55, 'away_team_id': 60},
        {'game_id': 18390, 'game_date': '2018-10-28', 'home_team_id': 51, 'away_team_id': 65},
        {'game_id': 18355, 'game_date': '2018-10-14', 'home_team_id': 41, 'away_team_id': 60},
        {'game_id': 18389, 'game_date': '2018-02-04', 'home_team_id': 51, 'away_team_id': 58},
        {'game_id': 18402, 'game_date': '2017-11-19', 'home_team_id': 58, 'away_team_id': 60},
        {'game_id': 18351, 'game_date': '2017-10-22', 'home_team_id': 40, 'away_team_id': 49},
        {'game_id': 18342, 'game_date': '2017-09-24', 'home_team_id': 36, 'away_team_id': 65},
        {'game_id': 18401, 'game_date': '2017-02-05', 'home_team_id': 58, 'away_team_id': 63},
        {'game_id': 18337, 'game_date': '2016-10-02', 'home_team_id': 34, 'away_team_id': 65},
        {'game_id': 18398, 'game_date': '2016-02-07', 'home_team_id': 56, 'away_team_id': 61},
        {'game_id': 18376, 'game_date': '2015-10-25', 'home_team_id': 47, 'away_team_id': 65},
        {'game_id': 18369, 'game_date': '2014-11-09', 'home_team_id': 45, 'away_team_id': 65},
        {'game_id': 18392, 'game_date': '2014-10-26', 'home_team_id': 52, 'away_team_id': 63},
        {'game_id': 18370, 'game_date': '2014-09-28', 'home_team_id': 46, 'away_team_id': 60},
        {'game_id': 18353, 'game_date': '2014-02-02', 'home_team_id': 41, 'away_team_id': 61},
        {'game_id': 18380, 'game_date': '2013-10-27', 'home_team_id': 48, 'away_team_id': 65},
        {'game_id': 18346, 'game_date': '2013-09-29', 'home_team_id': 37, 'away_team_id': 53},
        {'game_id': 18341, 'game_date': '2013-02-03', 'home_team_id': 36, 'away_team_id': 48},
        {'game_id': 18352, 'game_date': '2012-12-16', 'home_team_id': 41, 'away_team_id': 47},
        {'game_id': 18386, 'game_date': '2012-02-05', 'home_team_id': 50, 'away_team_id': 58},
        {'game_id': 18367, 'game_date': '2011-10-30', 'home_team_id': 44, 'away_team_id': 47},
        {'game_id': 18395, 'game_date': '2011-10-23', 'home_team_id': 55, 'away_team_id': 57},
        {'game_id': 18345, 'game_date': '2011-02-06', 'home_team_id': 37, 'away_team_id': 54},
        {'game_id': 18385, 'game_date': '2010-12-13', 'home_team_id': 50, 'away_team_id': 53},
        {'game_id': 18344, 'game_date': '2009-02-01', 'home_team_id': 37, 'away_team_id': 40},
    ]

    # Update each record
    for record in records_to_update:
        conn.execute(text("""
            UPDATE nfl_games
            SET 
                home_team_id = away_team_id,
                away_team_id = home_team_id,
                home_team_name = away_team_name,
                away_team_name = home_team_name,
                home_points = away_points,
                away_points = home_points,
                home_line = away_line,
                away_line = home_line,
                home_quarter_scores = away_quarter_scores,
                away_quarter_scores = home_quarter_scores,
                home_first_half_points = away_first_half_points,
                away_first_half_points = home_first_half_points,
                home_second_half_points = away_second_half_points,
                away_second_half_points = home_second_half_points,
                home_overtime_points = away_overtime_points,
                away_overtime_points = home_overtime_points,
                home_money_line = away_money_line,
                away_money_line = home_money_line
            WHERE game_id = :game_id
              AND game_date = :game_date
              AND home_team_id = :home_team_id
              AND away_team_id = :away_team_id
        """), record)


def downgrade():
    conn = op.get_bind()

    # Revert the changes for the same records
    records_to_update = [
        {'game_id': 18366, 'game_date': '2025-02-09', 'home_team_id': 43, 'away_team_id': 51},
        # (Repeat the same list as in the upgrade function)
    ]

    for record in records_to_update:
        conn.execute(text("""
            UPDATE nfl_games
            SET 
                home_team_id = away_team_id,
                away_team_id = home_team_id,
                home_team_name = away_team_name,
                away_team_name = home_team_name,
                home_points = away_points,
                away_points = home_points,
                home_line = away_line,
                away_line = home_line,
                home_quarter_scores = away_quarter_scores,
                away_quarter_scores = home_quarter_scores,
                home_first_half_points = away_first_half_points,
                away_first_half_points = home_first_half_points,
                home_second_half_points = away_second_half_points,
                away_second_half_points = home_second_half_points,
                home_overtime_points = away_overtime_points,
                away_overtime_points = home_overtime_points,
                home_money_line = away_money_line,
                away_money_line = home_money_line
            WHERE game_id = :game_id
              AND game_date = :game_date
              AND home_team_id = :home_team_id
              AND away_team_id = :away_team_id
        """), record)
