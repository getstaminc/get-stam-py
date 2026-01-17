"""Seed yesterday's NCAAB games into the ncaab_games table."""

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import json
import os
import time

# Load environment variables from .env file
load_dotenv()

# Load the DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

# SDQL credentials
SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

def get_yesterdays_games(retries=3, delay=1):
    """Fetch all games from the last two days from the SDQL API."""
    sdql_url = f"https://s3.sportsdatabase.com/NCAABB/query"
    print(f"Connecting to database: {DATABASE_URL}")
    
    # Calculate today and two days ago in the required format (YYYYMMDD)
    today = datetime.today().strftime('%Y%m%d')
    two_days_ago = (datetime.today() - timedelta(days=2)).strftime('%Y%m%d')
    
    sdql_query = f"date,site,team,o:team,points,o:points,total,margin,line,o:line,playoffs,money line,o:money line,_t,start time@(site='home' or site='neutral') and date<{today} and date>={two_days_ago}"

    headers = {
        'user': SDQL_USERNAME,
        'token': SDQL_TOKEN
    }

    data = {
        'sdql': sdql_query
    } 
    
    for i in range(retries):
        try:
            response = requests.get(sdql_url, headers=headers, params=data)
            response.raise_for_status()
            result = response.json()

            if result.get('headers') and result.get('groups'):
                headers = result['headers']
                rows = result['groups'][0]['columns']
                formatted_result = [dict(zip(headers, row)) for row in zip(*rows)]

                # Convert game_date to YYYY-MM-DD format and cast quarter scores to JSON
                for game in formatted_result:
                    game['date'] = datetime.strptime(str(game['date']), '%Y%m%d').strftime('%Y-%m-%d')

                print(f"Successfully fetched {len(formatted_result)} games from the last two days.")
                return formatted_result
            else:
                print("No games found for the last two days.")
                return []
        except requests.exceptions.RequestException as e:
            print(f"SDQL request failed: {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise
        except ValueError as e:
            print(f"Error parsing SDQL response JSON: {e}")
            return []

def seed_yesterdays_games():
    """Seed yesterday's NCAAB games into the ncaab_games table."""
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    # Fetch all games for yesterday
    games = get_yesterdays_games()
    print(f"Processing {len(games)} games.")

    for game in games:
        # Skip games with missing points
        if game['points'] is None or game['o:points'] is None:
            print(f"Skipping game due to missing points: {game}")
            continue

        # Handle missing fields with default values
        game['money line'] = game.get('money line', 0)
        game['o:money line'] = game.get('o:money line', 0)
        game['playoffs'] = bool(game.get('playoffs', 0))

        print(f"Inserting game: {game['team']} vs {game['o:team']} on {game['date']}")

        # Resolve team IDs explicitly and restrict to NCAAB to avoid duplicates
        home_team_row = conn.execute(text("""
            SELECT team_id FROM teams WHERE team_name = :home_team AND sport = 'NCAAB'
        """), {'home_team': game['team']}).fetchone()

        away_team_row = conn.execute(text("""
            SELECT team_id FROM teams WHERE team_name = :away_team AND sport = 'NCAAB'
        """), {'away_team': game['o:team']}).fetchone()

        home_team_id = home_team_row[0] if home_team_row else None
        away_team_id = away_team_row[0] if away_team_row else None

        if not home_team_id or not away_team_id:
            print(f"Team not found: Home - {game['team']}, Away - {game['o:team']}")
            continue

        # Skip duplicate matchups: same two teams on the same date (order-insensitive)
        exists = conn.execute(text("""
            SELECT 1 FROM ncaab_games
            WHERE game_date = :game_date
              AND (
                (home_team_id = :home_team_id AND away_team_id = :away_team_id)
                OR
                (home_team_id = :away_team_id AND away_team_id = :home_team_id)
              )
            LIMIT 1
        """), {
            'game_date': game['date'],
            'home_team_id': home_team_id,
            'away_team_id': away_team_id
        }).fetchone()

        if exists:
            print(f"Skipping duplicate matchup for {game['date']}: {game['team']} vs {game['o:team']}")
            continue

        # Insert data into ncaab table
        result = conn.execute(text("""
            INSERT INTO ncaab_games (
                game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name, home_points, away_points,
                total_points, total_margin, home_line, away_line,
                home_money_line, away_money_line, playoffs, total
            ) VALUES (
                :game_date, :game_site, 
                :home_team_id,
                :away_team_id,
                :home_team_name, :away_team_name,  -- Add these
                :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                :home_money_line, :away_money_line, :playoffs, :total
            )
        """), {
            'game_date': game['date'],
            'game_site': game['site'],
            'home_team': game['team'],
            'away_team': game['o:team'],
            'home_team_id': home_team_id,
            'away_team_id': away_team_id,
            'home_team_name': game['team'],  # Add this
            'away_team_name': game['o:team'],  # Add this
            'home_points': game['points'],
            'away_points': game['o:points'],
            'total_points': game['points'] + game['o:points'],
            'total_margin': game['margin'],
            'home_line': game['line'],
            'away_line': game['o:line'],
            'home_money_line': game['money line'],
            'away_money_line': game['o:money line'],
            'playoffs': game['playoffs'],
            'total': game['total']
        })

        # Log the response from the database
        print(f"Rows affected: {result.rowcount}")

    # Commit the transaction
    conn.commit()
    print("Transaction committed successfully.")
    conn.close()
    print("Seeding completed successfully.")

if __name__ == "__main__":
    seed_yesterdays_games()