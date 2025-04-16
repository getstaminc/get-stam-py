"""Seed yesterday's NBA games into the nba_games table."""

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
    """Fetch all of yesterday's games from the SDQL API."""
    sdql_url = f"https://s3.sportsdatabase.com/NBA/query"
    print(f"Connecting to database: {DATABASE_URL}")
    
    # Calculate yesterday's date in the required format (YYYYMMDD)
    yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y%m%d')
    yesterday = '20250410'
    # SDQL query to fetch all games for yesterday
    sdql_query = f"date,site,team,o:team,points,o:points,total,margin,line,o:line,quarter scores,o:quarter scores,playoffs,money line,o:money line,_t@site='home' and date={yesterday}"

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
                    game['quarter scores'] = json.dumps(game['quarter scores'])  # Cast to JSON
                    game['o:quarter scores'] = json.dumps(game['o:quarter scores'])  # Cast to JSON

                print(f"Successfully fetched {len(formatted_result)} games for {yesterday}.")
                return formatted_result
            else:
                print("No games found for yesterday.")
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
    """Seed yesterday's NBA games into the nba_games table."""
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
        print(f"Inserting game: {game['team']} vs {game['o:team']} on {game['date']}")

        # Deserialize quarter scores back to lists
        home_quarter_scores = json.loads(game['quarter scores'])
        away_quarter_scores = json.loads(game['o:quarter scores'])

        home_team_id = conn.execute(text("""
            SELECT team_id FROM teams WHERE team_name = :home_team
        """), {'home_team': game['team']}).fetchone()

        away_team_id = conn.execute(text("""
            SELECT team_id FROM teams WHERE team_name = :away_team
        """), {'away_team': game['o:team']}).fetchone()

        if not home_team_id or not away_team_id:
            print(f"Team not found: Home - {game['team']}, Away - {game['o:team']}")
            continue

        # Insert data into nba_games table
        result = conn.execute(text("""
            INSERT INTO nba_games (
                game_date, game_site, home_team_id, away_team_id, home_points, away_points,
                total_points, total_margin, home_line, away_line, home_quarter_scores,
                away_quarter_scores, home_halftime_points, away_halftime_points,
                home_money_line, away_money_line, playoffs
            ) VALUES (
                :game_date, :game_site, 
                (SELECT team_id FROM teams WHERE team_name = :home_team),
                (SELECT team_id FROM teams WHERE team_name = :away_team),
                :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                :home_quarter_scores, :away_quarter_scores, :home_halftime_points, :away_halftime_points,
                :home_money_line, :away_money_line, :playoffs
            )
        """), {
            'game_date': game['date'],
            'game_site': game['site'],
            'home_team': game['team'],
            'away_team': game['o:team'],
            'home_points': game['points'],
            'away_points': game['o:points'],
            'total_points': game['points'] + game['o:points'],
            'total_margin': game['margin'],
            'home_line': game['line'],
            'away_line': game['o:line'],
            'home_quarter_scores': game['quarter scores'],
            'away_quarter_scores': game['o:quarter scores'],
            'home_halftime_points': sum(home_quarter_scores[:2]),
            'away_halftime_points': sum(away_quarter_scores[:2]),
            'home_money_line': game.get('money line'),
            'away_money_line': game.get('o:money line'),
            'playoffs': bool(game.get('playoffs', 0))  # Cast to boolean
        })

        # Log the response from the database
        print(f"Rows affected: {result.rowcount}")

    # Commit the transaction
    conn.commit()
    print("Transaction committed successfully.")
    conn.close()

if __name__ == "__main__":
    seed_yesterdays_games()