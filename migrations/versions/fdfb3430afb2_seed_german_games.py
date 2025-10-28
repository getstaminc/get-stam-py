"""seed german games

Revision ID: fdfb3430afb2
Revises: 681e4f9087cc
Create Date: 2025-10-27 20:27:14.920230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import csv
import os
from datetime import datetime
# translation helper used elsewhere in the project
from soccer_utils import translate_soccer_team_name


# revision identifiers, used by Alembic.
revision: str = 'fdfb3430afb2'
down_revision: Union[str, None] = '681e4f9087cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed German (Bundesliga) games from CSVs located in migrations/german_csvs.

    This migration is defensive: it will skip rows that cannot be parsed or
    where the corresponding teams are not present in the `teams` table.
    It also checks for an existing soccer_games row with the same league,
    game_date, home_team_id and away_team_id to avoid duplicate inserts.
    """
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "german_csvs")
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

    def to_int(v):
        try:
            if v is None or v == '' or str(v).upper() == 'NA':
                return None
            return int(float(v))
        except Exception:
            return None

    # Mapping from incoming/raw or translated names to canonical DB team names
    canonical_team_map = {
        'Augsburg': 'Augsburg',
        'Bayern Munich': 'Bayern Munich',
        'Bielefeld': 'Arminia Bielefeld',
        'Bochum': 'VfL Bochum',
        'Braunschweig': 'Eintracht Braunschweig',
        'Darmstadt': 'SV Darmstadt 98',
        'Dortmund': 'Borussia Dortmund',
        'Ein Frankfurt': 'Eintracht Frankfurt',
        'FC Koln': '1. FC Köln',
        'Fortuna Dusseldorf': 'Fortuna Düsseldorf',
        'Freiburg': 'SC Freiburg',
        'Greuther Furth': 'Greuther Fürth',
        'Hamburg': 'Hamburger SV',
        'Hannover': 'Hannover 96',
        'Heidenheim': '1. FC Heidenheim',
        'Hertha': 'Hertha Berlin',
        'Hoffenheim': 'TSG Hoffenheim',
        'Holstein Kiel': 'Holstein Kiel',
        'Ingolstadt': 'FC Ingolstadt 04',
        'Kaiserslautern': '1. FC Kaiserslautern',
        'Leverkusen': 'Bayer Leverkusen',
        "M'gladbach": 'Borussia Monchengladbach',
        'Mainz': 'FSV Mainz 05',
        'Nurnberg': '1. FC Nürnberg',
        'Paderborn': 'SC Paderborn',
        'RB Leipzig': 'RB Leipzig',
        'Schalke 04': 'FC Schalke 04',
        'St Pauli': 'FC St. Pauli',
        'Stuttgart': 'VfB Stuttgart',
        'Union Berlin': 'Union Berlin',
        'Werder Bremen': 'Werder Bremen',
        'Wolfsburg': 'VfL Wolfsburg',
    }
    # Collect CSV files only, ignore hidden/temp files, and sort for deterministic order
    csv_files = sorted(
        os.path.join(base_dir, f)
        for f in os.listdir(base_dir)
        if f.lower().endswith('.csv') and not f.startswith('.') and not f.startswith('~')
    )

    # collect missing team references to report them all at once (non-destructive during parsing)
    missing_team_rows = []
    processed_rows = 0
    for path in csv_files:
        # defensive: skip non-files (directories) and log which files are processed
        if not os.path.isfile(path):
            continue
        print(f"[alembic] processing CSV: {os.path.basename(path)}")
        with open(path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                # normalize keys
                row = {k.strip(): v for k, v in row.items()}

                date_raw = row.get('Date')
                if not date_raw:
                    continue
                try:
                    game_date = parse_date(date_raw)
                except Exception:
                    # skip bad date rows
                    continue

                home_raw = row.get('HomeTeam') or row.get('Home')
                away_raw = row.get('AwayTeam') or row.get('Away')
                if not home_raw or not away_raw:
                    continue

                home_name = translate_soccer_team_name(home_raw)
                away_name = translate_soccer_team_name(away_raw)

                # normalize to canonical DB names if a mapping exists
                def _canonical(raw, translated):
                    # prefer exact raw match first, then translated match
                    if raw in canonical_team_map:
                        return canonical_team_map[raw]
                    if translated in canonical_team_map:
                        return canonical_team_map[translated]
                    return translated

                canonical_home = _canonical(home_raw, home_name)
                canonical_away = _canonical(away_raw, away_name)

                # log when we applied a mapping (helps debugging)
                if canonical_home != home_name:
                    print(f"[alembic] mapped home '{home_raw}' -> '{canonical_home}'")
                if canonical_away != away_name:
                    print(f"[alembic] mapped away '{away_raw}' -> '{canonical_away}'")

                home_name = canonical_home
                away_name = canonical_away

                # lookup team ids
                home_id = bind.execute(sa.select(teams_table.c.team_id).where(teams_table.c.team_name == home_name)).scalar()
                away_id = bind.execute(sa.select(teams_table.c.team_id).where(teams_table.c.team_name == away_name)).scalar()

                if home_id is None or away_id is None:
                    # Collect missing team references and continue parsing other rows/files.
                    missing = {}
                    if home_id is None:
                        missing['home_team_name'] = home_name
                        missing['home_team_raw'] = home_raw
                    if away_id is None:
                        missing['away_team_name'] = away_name
                        missing['away_team_raw'] = away_raw
                    missing.update({
                        'csv_file': os.path.basename(path),
                        'date': date_raw,
                    })
                    missing_team_rows.append(missing)
                    # Skip this row (do not insert)
                    continue

                # parse scores and odds
                FTHG = to_int(row.get('FTHG'))
                FTAG = to_int(row.get('FTAG'))
                HTHG = to_int(row.get('HTHG'))
                HTAG = to_int(row.get('HTAG'))

                # parse kickoff/start time from the 'Time' column only (per spec)
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

                # avoid duplicates: check if a row already exists for same league/date/home/away
                # SQLAlchemy select signature changed in newer versions: pass the column(s) as args
                exists_q = sa.select(sa.func.count()).select_from(soccer_games).where(
                    sa.and_(
                        soccer_games.c.league == 'BUNDESLIGA',
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
                        "league": 'BUNDESLIGA',
                        "game_date": game_date,
                        "home_team_id": home_id,
                        "away_team_id": away_id,
                        "home_team_name": home_name,
                        "away_team_name": away_name,
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

    # After processing all files, if there were missing team references, raise an aggregated error
    if missing_team_rows:
        lines = [
            f"{m['csv_file']} date={m['date']} - " + ", ".join(
                f"{k}={v!r}" for k, v in m.items() if k not in ('csv_file', 'date')
            )
            for m in missing_team_rows
        ]
        summary = (
            f"Missing team mappings detected in {len(missing_team_rows)} row(s).\n" +
            "Add the missing teams to the `teams` table (sport='SOCCER') or update your translation helper.\n" +
            "Missing rows:\n" + "\n".join(lines)
        )
        raise RuntimeError(summary)
    else:
        print(f"[alembic] processed {processed_rows} rows from {len(csv_files)} CSV file(s).")


def downgrade() -> None:
    # leaving downgrade as a no-op — reversing bulk imports is environment-specific
    # and may remove rows unintentionally. Implement if you need targeted removals.
    return
