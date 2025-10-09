"""Seed yesterday's NHL games into the nhl_games table."""

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import json
import os
import time

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")

SDQL_USERNAME = 'TimRoss'
SDQL_TOKEN = '3b88dcbtr97bb8e89b74r'

def get_yesterdays_nhl_games(retries=3, delay=1):
    sdql_url = "https://s3.sportsdatabase.com/NHL/query"

    # Calculate today and two days ago in the required format (YYYYMMDD)
    today = datetime.today().strftime('%Y%m%d')
    two_days_ago = (datetime.today() - timedelta(days=2)).strftime('%Y%m%d')

    # SDQL query to fetch all games from two days ago up to yesterday (not including today)
    sdql_query = f"date,site,team,line,goals,o:team,o:line,o:goals,total,period scores,o:period scores,goalie,o:goalie,playoffs,power play goals,o:power play goals,shoot out,overtime @(site='home' or site='neutral') and date<{today} and date>={two_days_ago}"


    headers = {'user': SDQL_USERNAME, 'token': SDQL_TOKEN}
    data = {'sdql': sdql_query}

    for i in range(retries):
        try:
            response = requests.get(sdql_url, headers=headers, params=data)
            response.raise_for_status()
            result = response.json()
            if result.get('headers') and result.get('groups'):
                headers = result['headers']
                rows = result['groups'][0]['columns']
                formatted_result = [dict(zip(headers, row)) for row in zip(*rows)]
                for game in formatted_result:
                    game['date'] = datetime.strptime(str(game['date']), '%Y%m%d').strftime('%Y-%m-%d')
                print(f"Fetched {len(formatted_result)} NHL games for the last two days.")
                return formatted_result
            else:
                print("No NHL games found for the last two days.")
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

def seed_yesterdays_nhl_games():
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()

    games = get_yesterdays_nhl_games()
    print(f"Processing {len(games)} NHL games.")

    teams_dict = {
        team['team_name']: team['team_id']
        for team in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NHL'")).mappings()
    }

    for game in games:
        # Skip games with missing goals
        if game['goals'] is None or game['o:goals'] is None:
            print(f"Skipping game due to missing goals: {game}")
            continue

        home_team_name = game['team']
        away_team_name = game['o:team']

        # Map "Hockey Club" to "Mammoth"
        if home_team_name == "Hockey Club":
            home_team_name = "Mammoth"
        if away_team_name == "Hockey Club":
            away_team_name = "Mammoth"

        home_team_id = teams_dict.get(home_team_name)
        away_team_id = teams_dict.get(away_team_name)

        if home_team_id is None or away_team_id is None:
            print(f"Skipping game due to missing team ID: Home: {home_team_name} (ID: {home_team_id}), Away: {away_team_name} (ID: {away_team_id})")
            continue


        # Check if either team has already played on this date (handles duplicates from neutral games)
        existing_game = conn.execute(text("""
            SELECT 1 FROM nhl_games
            WHERE game_date = :game_date
            AND (home_team_name = :team1 OR away_team_name = :team1 
                 OR home_team_name = :team2 OR away_team_name = :team2)
        """), {
            'game_date': game['date'],
            'team1': home_team_name,
            'team2': away_team_name
        }).fetchone()

        if existing_game:
            print(f"Skipping duplicate - one of these teams already played on {game['date']}: {home_team_name} vs {away_team_name}")
            continue

        home_period_goals = game.get('period scores', []) or []
        away_period_goals = game.get('o:period scores', []) or []

        print(f"Inserting NHL game: {home_team_name} vs {away_team_name} on {game['date']}")

        try:
            conn.execute(text("""
                INSERT INTO nhl_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_goals, away_goals, home_money_line, away_money_line, home_period_goals, away_period_goals,
                    home_starting_goalie, away_starting_goalie, home_powerplay_goals, away_powerplay_goals,
                    total, overtime, shoot_out, playoffs, sdql_game_id, created_date, modified_date
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_goals, :away_goals, :home_money_line, :away_money_line, :home_period_goals, :away_period_goals,
                    :home_starting_goalie, :away_starting_goalie, :home_powerplay_goals, :away_powerplay_goals,
                    :total, :overtime, :shoot_out, :playoffs, :sdql_game_id, :created_date, :modified_date
                )
            """), {
                'game_date': game['date'],
                'game_site': game['site'],
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'home_team_name': home_team_name,
                'away_team_name': away_team_name,
                'home_goals': game['goals'],
                'away_goals': game['o:goals'],
                'home_money_line': game.get('line'),
                'away_money_line': game.get('o:line'),
                'home_period_goals': home_period_goals,
                'away_period_goals': away_period_goals,
                'home_starting_goalie': game.get('goalie'),
                'away_starting_goalie': game.get('o:goalie'),
                'home_powerplay_goals': game.get('power play goals'),
                'away_powerplay_goals': game.get('o:power play goals'),
                'total': game.get('total'),
                'overtime': bool(game.get('overtime', 0)),
                'shoot_out': bool(game.get('shoot out', 0)),
                'playoffs': bool(game.get('playoffs', 0)),
                'sdql_game_id': game.get('sdql_game_id'),
                'created_date': datetime.now(),
                'modified_date': datetime.now()
            })
        except Exception as e:
            print(f"Database insert failed: {e}")
            continue

    conn.commit()
    print("Transaction committed successfully.")
    conn.close()
    print("Seeding completed successfully.")

if __name__ == "__main__":
    seed_yesterdays_nhl_games()