#!/usr/bin/python3
"""
MLB Player Team Assignment Job (Simple Version)

This script populates the team_id field in the mlb_players table by fetching MLB rosters from ESPN and matching espn_player_id to your database records.
This is the simple version that exactly matches the NBA approach.
Designed to be scheduled daily (e.g., via Heroku Scheduler) to keep player-team assignments up to date.
"""

import os
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

engine = create_engine(DATABASE_URL)

ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/{team_id}/roster"

def main():
    print("=" * 80)
    print("MLB Player Team Assignment Job (Simple)")
    print("=" * 80)
    with engine.connect() as conn:
        # 1. Get all MLB teams with espn_team_id
        teams = conn.execute(text("SELECT team_id, team_name, espn_team_id FROM teams WHERE sport = 'MLB' AND espn_team_id IS NOT NULL")).fetchall()
        print(f"Found {len(teams)} MLB teams with ESPN IDs.")
        total_updates = 0
        for team in teams:
            team_id, team_name, espn_team_id = team
            url = ESPN_ROSTER_URL.format(team_id=espn_team_id)
            print(f"Fetching roster for {team_name} (team_id={team_id}, espn_team_id={espn_team_id})...")
            try:
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                data = resp.json()
                athletes = data.get("athletes", [])
                print(f"  Found {len(athletes)} athletes.")
                for athlete in athletes:
                    athlete_id = athlete.get("id")
                    if athlete_id:
                        result = conn.execute(
                            text("UPDATE mlb_players SET team_id = :team_id WHERE espn_player_id = :athlete_id"),
                            {"team_id": team_id, "athlete_id": str(athlete_id)}
                        )
                        if result.rowcount:
                            total_updates += result.rowcount
                            print(f"    Updated player espn_player_id={athlete_id} with team_id={team_id}")
            except Exception as e:
                print(f"  Error fetching or updating for team {team_name}: {e}")
        conn.commit()
        print(f"\nTotal player records updated: {total_updates}")
    print("\nDone.")

if __name__ == "__main__":
    main()
