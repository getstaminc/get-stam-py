"""add spanish games real

Revision ID: a4442577d435
Revises: 93cd539532d8
Create Date: 2025-11-03 21:02:51.785153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import csv
import os
from datetime import datetime



# revision identifiers, used by Alembic.
revision: str = 'a4442577d435'
down_revision: Union[str, None] = '93cd539532d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed Spanish (LaLiga) games from CSVs located in migrations/spanish_csvs.

    This is defensive like the German seeder: it skips rows with unparseable
    dates or missing teams, and avoids duplicate inserts by checking for an
    existing row for the same league/game_date/home/away.
    """
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spanish_csvs")
    if not os.path.isdir(base_dir):
        return

    bind = op.get_bind()
    teams_table = sa.Table('teams', sa.MetaData(), autoload_with=bind)
    soccer_games = sa.Table('soccer_games', sa.MetaData(), autoload_with=bind)

    def parse_date(d: str):
        # Expect dates in strict DD/MM/YYYY format (e.g. 22/08/2025)
        try:
            return datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            raise ValueError(f"Unrecognized date format (expected DD/MM/YYYY): {d}")

    def parse_start_time(row):
        time_str = row.get("Time")
        if time_str:
            try:
                return datetime.strptime(time_str, "%H:%M").time()
            except Exception:
                return None
        return None

    def to_int(v):
        try:
            if v is None or v == '' or str(v).upper() == 'NA':
                return None
            return int(float(v))
        except Exception:
            return None

    # Mapping from CSV names to canonical DB / Odds API names provided by user
    csv_to_canonical = {
        'Alaves': 'Alavés',
        'Almeria': 'Almería',
        'Ath Bilbao': 'Athletic Bilbao',
        'Ath Madrid': 'Atlético Madrid',
        'Barcelona': 'Barcelona',
        'Betis': 'Real Betis',
        'Cadiz': 'Cádiz CF',
        'Celta': 'Celta Vigo',
        'Cordoba': 'Córdoba',
        'Eibar': 'SD Eibar',
        'Elche': 'Elche CF',
        'Espanol': 'Espanyol',
        'Getafe': 'Getafe',
        'Girona': 'Girona',
        'Granada': 'Granada CF',
        'Hercules': 'Hercules CF',
        'Huesca': 'SD Huesca',
        'La Coruna': 'Deportivo La Coruña',
        'Las Palmas': 'Las Palmas',
        'Leganes': 'Leganés',
        'Levante': 'Levante',
        'Malaga': 'Málaga',
        'Mallorca': 'Mallorca',
        'Osasuna': 'CA Osasuna',
        'Oviedo': 'Oviedo',
        'Real Madrid': 'Real Madrid',
        'Santander': 'Real Racing Club de Santander',
        'Sevilla': 'Sevilla',
        'Sociedad': 'Real Sociedad',
        'Sp Gijon': 'Sporting Gijón',
        'Valencia': 'Valencia',
        'Valladolid': 'Real Valladolid CF',
        'Vallecano': 'Rayo Vallecano',
        'Villarreal': 'Villarreal',
        'Zaragoza': 'Zaragoza',
    }

    csv_files = sorted(
        os.path.join(base_dir, f)
        for f in os.listdir(base_dir)
        if f.lower().endswith('.csv') and not f.startswith('.') and not f.startswith('~')
    )

    missing_team_rows = []
    processed_rows = 0
    for path in csv_files:
        if not os.path.isfile(path):
            continue
        print(f"[alembic] processing CSV: {os.path.basename(path)}")
        with open(path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                row = {k.strip(): v for k, v in row.items()}
                date_raw = row.get('Date')
                if not date_raw:
                    continue
                try:
                    game_date = parse_date(date_raw)
                except Exception:
                    continue

                home_raw = row.get('HomeTeam') or row.get('Home')
                away_raw = row.get('AwayTeam') or row.get('Away')
                if not home_raw or not away_raw:
                    continue

                # map CSV short name to canonical name
                canonical_home = csv_to_canonical.get(home_raw.strip(), home_raw.strip())
                canonical_away = csv_to_canonical.get(away_raw.strip(), away_raw.strip())

                # lookup team ids (sport='SOCCER')
                home_id = bind.execute(sa.select(teams_table.c.team_id).where(
                    sa.and_(teams_table.c.team_name == canonical_home, teams_table.c.sport == 'SOCCER')
                )).scalar()
                away_id = bind.execute(sa.select(teams_table.c.team_id).where(
                    sa.and_(teams_table.c.team_name == canonical_away, teams_table.c.sport == 'SOCCER')
                )).scalar()

                if home_id is None or away_id is None:
                    missing = {}
                    if home_id is None:
                        missing['home_team_name'] = canonical_home
                        missing['home_team_raw'] = home_raw
                    if away_id is None:
                        missing['away_team_name'] = canonical_away
                        missing['away_team_raw'] = away_raw
                    missing.update({'csv_file': os.path.basename(path), 'date': date_raw})
                    missing_team_rows.append(missing)
                    continue

                # parse scores/odds similar to German seeder
                FTHG = to_int(row.get('FTHG'))
                FTAG = to_int(row.get('FTAG'))
                HTHG = to_int(row.get('HTHG'))
                HTAG = to_int(row.get('HTAG'))
                start_time = parse_start_time(row)
                B365H = to_int(row.get('B365H'))
                B365D = to_int(row.get('B365D'))
                B365A = to_int(row.get('B365A'))
                over_price = to_int(row.get('BbAv>2.5') or row.get('B365>2.5'))
                under_price = to_int(row.get('BbAv<2.5') or row.get('B365<2.5'))
                AHCh = None
                try:
                    raw_ah = row.get('BbAHh') or row.get('BbAH') or row.get('AHCh')
                    if raw_ah not in (None, '', 'NA'):
                        AHCh = float(raw_ah)
                except Exception:
                    AHCh = None

                total_goals = None
                if FTHG is not None and FTAG is not None:
                    total_goals = FTHG + FTAG

                home_second_half = None
                away_second_half = None
                if FTHG is not None and HTHG is not None:
                    home_second_half = FTHG - HTHG
                if FTAG is not None and HTAG is not None:
                    away_second_half = FTAG - HTAG

                # avoid duplicates (league 'LA LIGA')
                exists_q = sa.select(sa.func.count()).select_from(soccer_games).where(
                    sa.and_(
                        soccer_games.c.league == 'LA LIGA',
                        soccer_games.c.game_date == game_date,
                        soccer_games.c.home_team_id == home_id,
                        soccer_games.c.away_team_id == away_id,
                    )
                )
                already = bind.execute(exists_q).scalar()
                if already and int(already) > 0:
                    continue

                bind.execute(
                    sa.text(
                        """
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
                        """
                    ),
                    {
                        "odds_id": None,
                        "league": 'LA LIGA',
                        "game_date": game_date,
                        "home_team_id": home_id,
                        "away_team_id": away_id,
                        "home_team_name": canonical_home,
                        "away_team_name": canonical_away,
                        "home_goals": FTHG,
                        "total_goals": total_goals,
                        "away_goals": FTAG,
                        "home_money_line": B365H,
                        "draw_money_line": B365D,
                        "away_money_line": B365A,
                        "home_spread": AHCh,
                        "away_spread": -AHCh if AHCh is not None else None,
                        "total_over_point": 2.5,
                        "total_over_price": over_price,
                        "total_under_point": 2.5,
                        "total_under_price": under_price,
                        "home_first_half_goals": HTHG,
                        "away_first_half_goals": HTAG,
                        "home_second_half_goals": home_second_half,
                        "away_second_half_goals": away_second_half,
                        "away_overtime": None,
                        "home_overtime": None,
                        "start_time": start_time,
                    }
                )
                processed_rows += 1

    if missing_team_rows:
        lines = [
            f"{m['csv_file']} date={m['date']} - " + ", ".join(
                f"{k}={v!r}" for k, v in m.items() if k not in ('csv_file', 'date')
            )
            for m in missing_team_rows
        ]
        summary = (
            f"Missing team mappings detected in {len(missing_team_rows)} row(s).\n" +
            "Add the missing teams to the `teams` table (sport='SOCCER') or update your mapping.\n" +
            "Missing rows:\n" + "\n".join(lines)
        )
        raise RuntimeError(summary)
    else:
        print(f"[alembic] processed {processed_rows} rows from {len(csv_files)} CSV file(s).")


def downgrade() -> None:
    # no-op: bulk import rollback is environment-specific and may be destructive
    return
