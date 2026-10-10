#!/usr/bin/python3
"""
Backfill did_not_play for Already-Identified, Never-Boxscored Players

Catches rows where player_team_id is NULL not because the player is
unidentified, but because they're so far down the bench that ESPN's boxscore
never mentions them in that specific game at all (the actuals-import jobs
already know this case -- it used to just print "likely DNP" and skip the
row with no DB write). Needs zero new ESPN calls: everything required (the
player's own confirmed espn_player_id + team, and the game's two teams) is
already stored on the row and on nfl_players/mlb_players.

Only touches a row when the player already has a confirmed espn_player_id
AND their own team_id is one of the two teams in that specific game -- an
unidentified player (espn_player_id IS NULL) is structurally excluded, and a
team mismatch is left alone rather than guessed at.

Also requires actuals_unavailable_reason IS NULL, so this never overwrites a
row backfill_postponed_game_reason.py already correctly labeled -- a rostered
player with a confirmed team can satisfy this query's other conditions even
when the real reason their row has no actuals is that the whole game was
postponed/canceled, not that they personally sat out.

Usage:
    python jobs/backfill_did_not_play.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(override=True)

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")

TARGETS = [
    {"table": "nfl_player_props", "players_table": "nfl_players"},
    {"table": "mlb_batter_props", "players_table": "mlb_players"},
    {"table": "mlb_pitcher_props", "players_table": "mlb_players"},
]


def _get_engine():
    return create_engine(DATABASE_URL)


def run():
    engine = _get_engine()
    for target in TARGETS:
        table = target["table"]
        players_table = target["players_table"]

        with engine.connect() as conn:
            count = conn.execute(text(f"""
                SELECT COUNT(*)
                FROM {table} pp
                JOIN {players_table} p ON pp.player_id = p.id
                WHERE pp.player_team_id IS NULL
                  AND pp.actuals_unavailable_reason IS NULL
                  AND p.espn_player_id IS NOT NULL
                  AND p.team_id IN (pp.odds_home_team_id, pp.odds_away_team_id)
            """)).scalar()
            print(f"[dnp-backfill] {table}: {count} row(s) eligible")

            result = conn.execute(text(f"""
                WITH candidates AS (
                    SELECT pp.id AS props_id,
                           p.team_id AS player_team_id,
                           CASE WHEN pp.odds_home_team_id = p.team_id
                                THEN pp.odds_away_team_id ELSE pp.odds_home_team_id END AS opponent_team_id
                    FROM {table} pp
                    JOIN {players_table} p ON pp.player_id = p.id
                    WHERE pp.player_team_id IS NULL
                      AND pp.actuals_unavailable_reason IS NULL
                      AND p.espn_player_id IS NOT NULL
                      AND p.team_id IN (pp.odds_home_team_id, pp.odds_away_team_id)
                )
                UPDATE {table} pp
                SET player_team_id = c.player_team_id,
                    player_team_name = t1.team_name,
                    opponent_team_id = c.opponent_team_id,
                    opponent_team_name = t2.team_name,
                    did_not_play = true,
                    actuals_unavailable_reason = 'did_not_play',
                    updated_at = CURRENT_TIMESTAMP
                FROM candidates c
                JOIN teams t1 ON t1.team_id = c.player_team_id
                JOIN teams t2 ON t2.team_id = c.opponent_team_id
                WHERE pp.id = c.props_id
            """))
            conn.commit()
            print(f"[dnp-backfill] {table}: {result.rowcount} row(s) labeled did_not_play")


if __name__ == "__main__":
    run()
