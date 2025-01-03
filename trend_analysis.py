import requests
import pandas as pd
from datetime import datetime, timedelta  # Add timedelta here
from dateutil import parser
import pytz
from utils import convert_team_name, convert_sport_key
from sdql_queries import get_last_5_games, get_last_5_games_vs_opponent

def get_last_5_games_for_team(team_name, selected_date, sport_key):
    """Fetch last 5 games for a team."""
    try:
        sdql_query = f"team='{team_name}' and date<'{selected_date.strftime('%Y%m%d')}'"
        response = get_last_5_games(sdql_query, sport_key)  # Pass sport_key
        if response:
            # Parse SDQL response to extract columns
            games = response.get('groups', [{}])[0].get('columns', [])
            # Transform columns to dict rows for easier handling with pandas
            return [dict(zip(response['headers'], col)) for col in zip(*games)][:5]
    except Exception as e:
        print(f"Error fetching last 5 games for {team_name}: {e}")
    return []

def get_last_5_matchups_between_teams(home_team, away_team, selected_date, sport_key):
    """Fetch last 5 matchups between two teams."""
    try:
        response = get_last_5_games_vs_opponent(
            team=home_team,
            opponent=away_team,
            today_date=selected_date,
            sport_key=sport_key
        )
        if response:
            # Parse SDQL response
            games = response.get('groups', [{}])[0].get('columns', [])
            return [dict(zip(response['headers'], col)) for col in zip(*games)][:5]
    except Exception as e:
        print(f"Error fetching last 5 matchups between {home_team} and {away_team}: {e}")
    return []

def calculate_team_trends(last_5_games, team):
    """Calculate trends for a team."""
    trends = []
    data = pd.DataFrame(last_5_games)

    if data.empty or len(data) < 5:
        return [f"{team} has insufficient data for trends"]

    # Winning trends
    data['is_winner'] = data['points'] > data['o:points']
    if data['is_winner'].sum() == 5:
        trends.append(f"{team} has won 5 games in a row")
    elif (~data['is_winner']).sum() == 5:
        trends.append(f"{team} has lost 5 games in a row")

    # Spread trends
    data['covered_spread'] = (data['points'] + data['line']) > data['o:points']
    if data['covered_spread'].sum() == 5:
        trends.append(f"{team} has covered the spread in 5 games in a row")
    elif (~data['covered_spread']).sum() == 5:
        trends.append(f"{team} has failed to cover the spread in 5 games in a row")

    # Total trends
    data['total_result'] = data['points'] + data['o:points']
    data['over'] = data['total_result'] > data['total']
    data['under'] = data['total_result'] < data['total']
    if data['over'].sum() == 5:
        trends.append(f"{team} games have gone over the total 5 times in a row")
    elif data['under'].sum() == 5:
        trends.append(f"{team} games have gone under the total 5 times in a row")

    return trends if trends else [f"No trends found for {team}"]

def analyze_trends_for_games(scores, selected_date, sport_key):
    """Analyze trends for all games on a specific date."""
    print(f"Scores received for analysis: {scores}")
    trends = {}

    # Define the start and end of the selected date in UTC
    selected_date_start = selected_date.astimezone(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    selected_date_end = selected_date_start + timedelta(days=1)

    for game in scores:
        try:
            # Parse the commence_time and ensure it's in UTC
            commence_time = parser.parse(game.get('commence_time', '')).astimezone(pytz.utc)
            print(f"Commence time for game: {commence_time}")

            # Check if the game's commence_time falls within the UTC range of the selected date
            if not (selected_date_start <= commence_time < selected_date_end):
                print(f"Skipping game with commence_time: {commence_time}")
                continue
        except Exception as e:
            print(f"Error parsing commence_time for game: {game}. Error: {e}")
            continue

        home_team = game.get('home_team')
        away_team = game.get('away_team')

        if not home_team or not away_team:
            print(f"Missing team information for game: {game}")
            continue  # Skip games with missing team info

        # Fetch last 5 games for home and away teams
        try:
            home_last_5 = get_last_5_games_for_team(home_team, selected_date, sport_key)
            away_last_5 = get_last_5_games_for_team(away_team, selected_date, sport_key)
        except Exception as e:
            print(f"Error fetching last 5 games: {e}")
            continue

        # Fetch last 5 matchups between the two teams
        try:
            last_5_matchups = get_last_5_matchups_between_teams(home_team, away_team, selected_date, sport_key)
        except Exception as e:
            print(f"Error fetching last 5 matchups: {e}")
            last_5_matchups = []

        # Calculate trends
        home_trends = calculate_team_trends(home_last_5, home_team)
        away_trends = calculate_team_trends(away_last_5, away_team)
        matchup_trends = calculate_team_trends(last_5_matchups, f"{home_team} vs {away_team}")

        # Combine trends
        trends[f"{home_team} vs {away_team}"] = {
            "home_team": home_trends,
            "away_team": away_trends,
            "matchup": matchup_trends
        }

    # If no trends are found, log it
    if not trends:
        print("No trends found for games on this date.")
    print(f"Final trends: {trends}")  # Debug log
    return trends