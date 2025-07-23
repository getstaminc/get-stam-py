"""seed soccer elp 10 and 11

Revision ID: 4baa8f03b8ec
Revises: fc33bced5ead
Create Date: 2025-07-08 20:49:43.717621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import Integer, String, Date, Float, Time
from datetime import datetime
import csv
import os
# Import your translation function
from soccer_utils import translate_soccer_team_name


# revision identifiers, used by Alembic.
revision: str = '4baa8f03b8ec'
down_revision: Union[str, None] = 'fc33bced5ead'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def parse_start_time(row):
    """
    Returns a Python time object from the 'Time' column in the row,
    or None if the column is missing or not parseable.
    """
    time_str = row.get("Time")
    if time_str:
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except Exception:
            return None
    return None

def upgrade():
    # List of CSV files to process
    csv_files = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "soccer_csvs", "condensed columns - epl10_11.csv"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "soccer_csvs", "condensed columns - epl11_12.csv"),
    ]

    # Get connection and metadata
    bind = op.get_bind()

    # Reflect teams table for lookups
    teams_table = sa.Table('teams', sa.MetaData(), autoload_with=bind)

    for csv_path in csv_files:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Translate team names
                home_team_db = translate_soccer_team_name(row["HomeTeam"])
                away_team_db = translate_soccer_team_name(row["AwayTeam"])

                # Look up team IDs
                home_team_id = bind.execute(
                    sa.select(teams_table.c.team_id).where(teams_table.c.team_name == home_team_db)
                ).scalar()
                away_team_id = bind.execute(
                    sa.select(teams_table.c.team_id).where(teams_table.c.team_name == away_team_db)
                ).scalar()

                # Parse date (CSV is DD/MM/YY)
                game_date = datetime.strptime(row["Date"], "%d/%m/%y").strftime("%Y-%m-%d")

                start_time = parse_start_time(row)

                # Convert numeric fields (handle missing or empty)
                def to_int(val):
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return None

                # Calculate derived fields
                FTHG = to_int(row.get("FTHG"))
                FTAG = to_int(row.get("FTAG"))
                HTHG = to_int(row.get("HTHG"))
                HTAG = to_int(row.get("HTAG"))
                B365H = to_int(row.get("B365H"))
                B365D = to_int(row.get("B365D"))
                B365A = to_int(row.get("B365A"))
                B365_over = to_int(row.get("B365>2.5"))
                B365_under = to_int(row.get("B365<2.5"))
                AHCh = None
                try:
                    AHCh = float(row.get("AHCh")) if row.get("AHCh") not in (None, '', 'NA') else None
                except Exception:
                    AHCh = None

                total_goals = FTHG + FTAG if FTHG is not None and FTAG is not None else None
                home_second_half_goals = FTHG - HTHG if FTHG is not None and HTHG is not None else None
                away_second_half_goals = FTAG - HTAG if FTAG is not None and HTAG is not None else None

                bind.execute(
                    sa.text("""
                        INSERT INTO soccer_games (
                            odds_id, league, game_date, home_team_id, away_team_id,
                            home_team_name, away_team_name, home_goals, total_goals, away_goals,
                            home_money_line, draw_money_line, away_money_line,
                            home_spread, away_spread, total_over_point, total_over_price,
                            total_under_point, total_under_price,
                            home_first_half_goals, away_first_half_goals,
                            home_second_half_goals, away_second_half_goals,
                            away_overtime, home_overtime, start_time
                        ) VALUES (
                            :odds_id, :league, :game_date, :home_team_id, :away_team_id,
                            :home_team_name, :away_team_name, :home_goals, :total_goals, :away_goals,
                            :home_money_line, :draw_money_line, :away_money_line,
                            :home_spread, :away_spread, :total_over_point, :total_over_price,
                            :total_under_point, :total_under_price,
                            :home_first_half_goals, :away_first_half_goals,
                            :home_second_half_goals, :away_second_half_goals,
                            :away_overtime, :home_overtime, :start_time
                        )
                    """),
                    {
                        "odds_id": None,
                        "league": "EPL",
                        "game_date": game_date,
                        "home_team_id": home_team_id,
                        "away_team_id": away_team_id,
                        "home_team_name": home_team_db,
                        "away_team_name": away_team_db,
                        "home_goals": FTHG,
                        "total_goals": total_goals,
                        "away_goals": FTAG,
                        "home_money_line": B365H,
                        "draw_money_line": B365D,
                        "away_money_line": B365A,
                        "home_spread": AHCh,
                        "away_spread": -AHCh if AHCh is not None else None,
                        "total_over_point": 2.5,
                        "total_over_price": B365_over,
                        "total_under_point": 2.5,
                        "total_under_price": B365_under,
                        "home_first_half_goals": HTHG,
                        "away_first_half_goals": HTAG,
                        "home_second_half_goals": home_second_half_goals,
                        "away_second_half_goals": away_second_half_goals,
                        "away_overtime": None,
                        "home_overtime": None,
                        "start_time": start_time
                    }
                )

def downgrade():
    pass
