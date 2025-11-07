"""15-19 newly added teams

Revision ID: 6f434a584626
Revises: a4442577d435
Create Date: 2025-11-04 14:36:31.200592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import requests
import time
from datetime import datetime
import json
import ast


# revision identifiers, used by Alembic.
revision: str = '6f434a584626'
down_revision: Union[str, None] = 'a4442577d435'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    SDQL_USERNAME = 'TimRoss'
    SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

    def get_historical_games(team, retries=4, delay=1):
        sdql_url = f"https://s3.sportsdatabase.com/NCAABB/query"
        # Avoid requesting fields with spaces (like 'quarter scores') because
        # the SDQL parser on the server can raise a SyntaxError when compiling
        # metacode for those field names. We'll omit them here and handle
        # missing quarter data gracefully downstream.
        fields = (
            "date,site,team,o:team,points,o:points,total,margin,line,o:line,"
            "playoffs,money line,o:money line,_t,start time"
        )
        sdql_query = fields + f"@team='{team}' and site='home' and date>20150101 and date<20190101"

        headers = {
            'user': SDQL_USERNAME,
            'token': SDQL_TOKEN
        }

        data = {'sdql': sdql_query}

        local_delay = delay
        for i in range(retries):
            try:
                response = requests.get(sdql_url, headers=headers, params=data)
                response.raise_for_status()
                try:
                    result = response.json()
                except Exception as e:
                    # Fallback: some SDQL responses are not strict JSON (HTML or
                    # single-quoted structures). Try ast.literal_eval as a best-effort
                    # fallback, otherwise log and skip this team.
                    snippet = (response.text or '')[:2000]
                    parsed = None
                    try:
                        parsed = ast.literal_eval(response.text)
                    except Exception:
                        parsed = None

                    if isinstance(parsed, dict) and parsed.get('headers') and parsed.get('groups'):
                        result = parsed
                    else:
                        print(f"SDQL response not JSON for team {team}: {e}; response snippet: {snippet}")
                        return []

                if result.get('headers') and result.get('groups'):
                    headers_row = result['headers']
                    rows = result['groups'][0]['columns']
                    formatted_result = [dict(zip(headers_row, row)) for row in zip(*rows)]

                    # Normalize date and cast quarter scores to JSON strings
                    for game in formatted_result:
                        try:
                            game['date'] = datetime.strptime(str(game['date']), '%Y%m%d').strftime('%Y-%m-%d')
                        except Exception:
                            # leave as-is if parsing fails
                            pass
                        game['quarter scores'] = json.dumps(game.get('quarter scores'))
                        game['o:quarter scores'] = json.dumps(game.get('o:quarter scores'))

                    return formatted_result
                else:
                    return []
            except requests.exceptions.RequestException as e:
                # On transient network/server errors (e.g. 502/503/429) back off
                # with increasing delay to avoid hammering SDQL.
                print(f"SDQL request failed: {e}; retrying in {local_delay}s")
                if i < retries - 1:
                    time.sleep(local_delay)
                    local_delay = min(local_delay * 2, 10)
                    continue
                else:
                    raise
            except ValueError as e:
                print(f"Error parsing SDQL response JSON: {e}")
                return []

    # Fetch all existing teams for NCAAB into a lookup so we don't try to
    # insert teams that already exist in the DB (even if they were created
    # on a different date).
    teams_dict = {
        team['team_name']: team['team_id']
        for team in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NCAAB'")) .mappings()
    }

    # But only process the teams that were created on 2025-11-03 (the set
    # of teams we want to seed games for).
    team_names = [
        row['team_name']
        for row in conn.execute(text("SELECT team_name FROM teams WHERE sport = 'NCAAB' AND created_at::date = '2025-11-03'")) .mappings()
    ]

    print(f"Found {len(teams_dict)} existing NCAAB teams in database; will process {len(team_names)} teams created on 2025-11-03.")
    # pause between consecutive SDQL requests to reduce rate of requests
    REQUEST_PAUSE_SECONDS = 3

    for team_name in team_names:
        games = get_historical_games(team_name)
        for game in games:
            # skip if points missing
            if game.get('points') is None or game.get('o:points') is None:
                print(f"Skipping game due to missing points: {game}")
                continue

            # Resolve or create team IDs. If a team is missing from `teams`,
            # insert it (idempotent) with sport='NCAAB' and re-query the id.
            home_name = game.get('team')
            away_name = game.get('o:team')

            def resolve_team_id(name):
                if not name:
                    return None
                tid = teams_dict.get(name)
                if tid is not None:
                    return tid
                # Insert idempotently
                try:
                    conn.execute(sa.text(
                        "INSERT INTO teams (team_name, sport) VALUES (:name, 'NCAAB') ON CONFLICT (team_name, sport) DO NOTHING"
                    ), {'name': name})
                except Exception as e:
                    print(f"Warning: could not insert team {name}: {e}")
                row = conn.execute(text("SELECT team_id FROM teams WHERE team_name = :name AND sport = 'NCAAB'"), {'name': name}).fetchone()
                if row:
                    teams_dict[name] = row[0]
                    print(f"Inserted/Found team {name} -> id {row[0]}")
                    return row[0]
                return None

            home_team_id = resolve_team_id(home_name)
            away_team_id = resolve_team_id(away_name)

            if home_team_id is None or away_team_id is None:
                print(f"Skipping game due to missing team ID after attempt to create: {game}")
                continue

            # Deserialize quarter scores
            try:
                home_q_raw = game.get('quarter scores')
                away_q_raw = game.get('o:quarter scores')

                if isinstance(home_q_raw, str):
                    home_q = json.loads(home_q_raw)
                else:
                    home_q = home_q_raw

                if isinstance(away_q_raw, str):
                    away_q = json.loads(away_q_raw)
                else:
                    away_q = away_q_raw
            except (TypeError, json.JSONDecodeError) as e:
                print(f"Invalid quarter scores for game: {game}")
                raise Exception("Invalid quarter scores format") from e

            # compute halves and overtime
            home_first_half = sum(home_q[:2]) if home_q else None
            away_first_half = sum(away_q[:2]) if away_q else None
            home_second_half = sum(home_q[2:4]) if home_q else None
            away_second_half = sum(away_q[2:4]) if away_q else None
            home_ot = home_q[4] if home_q and len(home_q) > 4 else None
            away_ot = away_q[4] if away_q and len(away_q) > 4 else None

            home_q_json = json.dumps(home_q) if home_q is not None else None
            away_q_json = json.dumps(away_q) if away_q is not None else None

            # parse optional start time
            start_time_val = None
            for time_key in ('start_time', 'start', 'time', 'start time'):
                raw_time = game.get(time_key)
                if raw_time:
                    s = str(raw_time).strip()
                    for fmt in ('%H:%M', '%H%M', '%H:%M:%S', '%H%M%S', '%I:%M%p', '%I:%M %p'):
                        try:
                            start_time_val = datetime.strptime(s, fmt).time()
                            break
                        except ValueError:
                            continue
                    if start_time_val is not None:
                        break

            # We do not import or populate sdql_game_id here; leave that field
            # managed elsewhere. Insert the game row normally.
            conn.execute(text("""
                INSERT INTO ncaab_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_points, away_points, total_points, total_margin, total, home_line, away_line,
                    home_quarter_scores, away_quarter_scores, home_first_half_points, away_first_half_points,
                    home_second_half_points, away_second_half_points, home_overtime_points, away_overtime_points,
                    home_money_line, away_money_line, playoffs, start_time
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_points, :away_points, :total_points, :total_margin, :total, :home_line, :away_line,
                    :home_quarter_scores, :away_quarter_scores, :home_first_half_points, :away_first_half_points,
                    :home_second_half_points, :away_second_half_points, :home_overtime_points, :away_overtime_points,
                    :home_money_line, :away_money_line, :playoffs, :start_time
                )
            """), {
                'game_date': game.get('date'),
                'game_site': game.get('site'),
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'home_team_name': game.get('team'),
                'away_team_name': game.get('o:team'),
                'home_points': game.get('points'),
                'away_points': game.get('o:points'),
                'total_points': (game.get('points') or 0) + (game.get('o:points') or 0),
                'total_margin': game.get('margin'),
                'home_line': game.get('line'),
                'away_line': game.get('o:line'),
                'home_quarter_scores': home_q_json,
                'away_quarter_scores': away_q_json,
                'home_first_half_points': home_first_half,
                'away_first_half_points': away_first_half,
                'home_second_half_points': home_second_half,
                'away_second_half_points': away_second_half,
                'home_overtime_points': home_ot,
                'away_overtime_points': away_ot,
                'home_money_line': game.get('money line'),
                'away_money_line': game.get('o:money line'),
                'playoffs': bool(game.get('playoffs', 0)),
                'total': game.get('total'),
                'start_time': start_time_val
            })

        # brief pause between team requests to avoid triggering SDQL rate limits
        try:
            time.sleep(REQUEST_PAUSE_SECONDS)
        except Exception:
            pass


def downgrade() -> None:
    pass
