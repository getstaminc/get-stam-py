"""add italy

Revision ID: c06225115194
Revises: 72289ac8a760
Create Date: 2025-12-01 20:56:42.207135

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
revision: str = 'c06225115194'
down_revision: Union[str, None] = '72289ac8a760'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed Italian (Serie A) games from CSVs located in migrations/italy_csvs.

    This migration mirrors the defensive approach used by the Bundesliga seeder:
    - skip rows with unparseable dates
    - translate team names via translate_soccer_team_name
    - map spreadsheet/raw names to canonical DB names when needed
    - skip rows where teams are not found in the `teams` table (and report them)
    - avoid duplicate inserts by checking for existing league/date/home/away rows
    """
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "italy_csvs")
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
        'Atalanta': 'Atalanta BC',
        'Bari': 'Bari',
        'Benevento': 'Benevento',
        'Bologna': 'Bologna',
        'Brescia': 'Brescia',
        'Cagliari': 'Cagliari',
        'Carpi': 'A.C. Carpi',
        'Catania': 'Catania',
        'Cesena': 'Cesena FC',
        'Chievo': 'Chievo Verona',
        'Como': 'Como',
        'Cremonese': 'Cremonese',
        'Crotone': 'Crotone',
        'Empoli': 'Empoli',
        'Fiorentina': 'Fiorentina',
        'Frosinone': 'Frosinone',
        'Genoa': 'Genoa',
        'Inter': 'Inter Milan',
        'Juventus': 'Juventus',
        'Lazio': 'Lazio',
        'Lecce': 'Lecce',
        'Livorno': 'Livorno',
        'Milan': 'AC Milan',
        'Monza': 'Monza',
        'Napoli': 'Napoli',
        'Novara': 'Novara',
        'Palermo': 'Palermo',
        'Parma': 'Parma',
        'Pescara': 'Pescara',
        'Pisa': 'Pisa',
        'Roma': 'AS Roma',
        'Salernitana': 'Salernitana',
        'Sampdoria': 'Sampdoria',
        'Sassuolo': 'Sassuolo',
        'Siena': 'Siena',
        'Spal': 'SPAL',
        'Spezia': 'Spezia',
        'Torino': 'Torino',
        'Udinese': 'Udinese',
        'Venezia': 'Venezia',
        'Verona': 'Hellas Verona FC',
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

                # lookup team ids (ensure teams exist; if absent, insert a minimal team row)
                def ensure_team(team_name_val):
                    """Return team_id for team_name_val, inserting a minimal teams row if needed.

                    This keeps the migration idempotent: it only inserts when a team_name is missing.
                    Inserts use sport='SOCCER'. If insertion fails for any reason we still return None.
                    """
                    # try to find first
                    t_id = bind.execute(
                        sa.select(teams_table.c.team_id).where(teams_table.c.team_name == team_name_val)
                    ).scalar()
                    if t_id is not None:
                        return t_id
                    # not found -> insert a minimal row (idempotent: check again before insert)
                    try:
                        existing = bind.execute(
                            sa.select(sa.func.count()).select_from(teams_table).where(teams_table.c.team_name == team_name_val)
                        ).scalar()
                        if not existing or int(existing) == 0:
                            bind.execute(
                                sa.text(
                                    "INSERT INTO teams (team_name, sport) VALUES (:team_name, :sport)"
                                ),
                                {"team_name": team_name_val, "sport": 'SOCCER'}
                            )
                    except Exception:
                        # swallow and let caller handle missing id
                        return None
                    # re-query
                    try:
                        return bind.execute(
                            sa.select(teams_table.c.team_id).where(teams_table.c.team_name == team_name_val)
                        ).scalar()
                    except Exception:
                        return None

                home_id = ensure_team(home_name)
                away_id = ensure_team(away_name)

                if home_id is None or away_id is None:
                    # Immediately stop and surface which team(s) could not be resolved.
                    missing_parts = []
                    if home_id is None:
                        missing_parts.append(f"home={home_name!r} raw={home_raw!r}")
                    if away_id is None:
                        missing_parts.append(f"away={away_name!r} raw={away_raw!r}")
                    filename = os.path.basename(path)
                    raise RuntimeError(
                        f"Missing team_id for {', '.join(missing_parts)} in {filename} date={date_raw}"
                    )

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
                exists_q = sa.select(sa.func.count()).select_from(soccer_games).where(
                    sa.and_(
                        soccer_games.c.league == 'SERIE A',
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
                        "league": 'SERIE A',
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
