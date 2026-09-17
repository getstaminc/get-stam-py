#!/usr/bin/python3
"""
NFL Player Team Assignment Job

Populates `nfl_players.team_id` so player props can be bucketed onto the right
current team (otherwise a player who changed teams shows under last season's).

The ONLY column this job writes is `nfl_players.team_id`, and only on rows that
already exist. No espn_player_id backfill, no position, no inserts.

Two passes:
  1. From each player's most recent nfl_player_props row (covers players not on a
     current 53-man roster — practice squad, just-cut, etc.)
  2. From ESPN's current team rosters (authoritative; overwrites pass 1).

Run locally — site.api.espn.com 403s Heroku's datacenter IPs. No args.
"""

import os
import sys

import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.player_name_utils import normalize_name

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

engine = create_engine(DATABASE_URL)

ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/roster"
# A bare "python-requests" UA gets a 403 from ESPN's edge even from a residential IP.
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def assign_from_recent_props(conn):
    """team_id for NULL-team_id players, from their most recent prop row."""
    print("\n=== Step 1: assignment from recent prop records ===")
    rows = conn.execute(text("""
        WITH most_recent AS (
            SELECT player_id,
                   player_team_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY player_id
                       ORDER BY game_date DESC, created_at DESC
                   ) AS rn
            FROM nfl_player_props
            WHERE player_team_id IS NOT NULL
        )
        SELECT p.id, p.player_name, mr.player_team_id, t.team_name
        FROM nfl_players p
        JOIN most_recent mr ON mr.player_id = p.id AND mr.rn = 1
        JOIN teams t ON t.team_id = mr.player_team_id
        WHERE p.team_id IS NULL
        ORDER BY p.player_name
    """)).fetchall()

    if not rows:
        print("  No unassigned players with prop history.")
        return 0

    print(f"  {len(rows)} unassigned players have a prop-derived team")
    updated = 0
    for player_id, player_name, team_id, team_name in rows:
        try:
            conn.execute(
                text("UPDATE nfl_players SET team_id = :team_id WHERE id = :player_id"),
                {"team_id": team_id, "player_id": player_id},
            )
            updated += 1
            print(f"    \U0001F4CD {player_name} -> {team_name}")
        except Exception as e:
            print(f"    ❌ {player_name}: {e}")
    return updated


def assign_from_espn_rosters(conn):
    """team_id from each team's current ESPN roster (overwrites step 1)."""
    print("\n=== Step 2: ESPN roster assignment ===")
    teams = conn.execute(text("""
        SELECT team_id, team_name, espn_team_id
        FROM teams
        WHERE sport = 'NFL' AND espn_team_id IS NOT NULL
        ORDER BY team_name
    """)).fetchall()
    print(f"  {len(teams)} NFL teams with an ESPN id")

    by_espn_id = 0
    by_name = 0
    no_match = 0

    for team_id, team_name, espn_team_id in teams:
        url = ESPN_ROSTER_URL.format(team_id=espn_team_id)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ❌ {team_name}: {e}")
            continue

        athletes = []
        for group in data.get("athletes", []):
            athletes.extend(group.get("items", []))
        print(f"  {team_name}: {len(athletes)} athletes")

        for athlete in athletes:
            athlete_id = athlete.get("id")
            athlete_name = athlete.get("displayName") or athlete.get("fullName") or ""
            if not athlete_id or not athlete_name:
                continue

            result = conn.execute(
                text("UPDATE nfl_players SET team_id = :team_id WHERE espn_player_id = :athlete_id"),
                {"team_id": team_id, "athlete_id": str(athlete_id)},
            )
            if result.rowcount:
                by_espn_id += result.rowcount
                continue

            match = conn.execute(text("""
                SELECT id FROM nfl_players WHERE normalized_name = :name
            """), {"name": normalize_name(athlete_name)}).fetchall()

            if len(match) == 1:
                conn.execute(
                    text("UPDATE nfl_players SET team_id = :team_id WHERE id = :id"),
                    {"team_id": team_id, "id": match[0][0]},
                )
                by_name += 1
            elif len(match) > 1:
                no_match += 1
                print(f"    ⚠️  ambiguous name, skipped: {athlete_name}")
            else:
                no_match += 1

    print(f"\n  matched by ESPN id: {by_espn_id}")
    print(f"  matched by name:     {by_name}")
    print(f"  no match / skipped:  {no_match}")
    return by_espn_id + by_name


def main():
    print("=" * 80)
    print("NFL Player Team Assignment Job")
    print("=" * 80)

    with engine.connect() as conn:
        step1 = assign_from_recent_props(conn)
        step2 = assign_from_espn_rosters(conn)
        conn.commit()

        total = conn.execute(text("""
            SELECT COUNT(*) FILTER (WHERE team_id IS NOT NULL), COUNT(*)
            FROM nfl_players
        """)).fetchone()

    print("\n" + "=" * 80)
    print(f"Step 1 (prop-derived): {step1}")
    print(f"Step 2 (ESPN roster):  {step2}")
    print(f"nfl_players with team_id: {total[0]} / {total[1]}")
    print("Done.")


if __name__ == "__main__":
    main()
