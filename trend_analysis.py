import requests
import pandas as pd
from datetime import datetime
from utils import convert_team_name, convert_sport_key
from sdql_queries import get_last_5_games, get_last_5_games_vs_opponent




def get_last_5_games_for_team(team_name, selected_date):
    """Fetch last 5 games for a team."""
    try:
        sdql_query = f"team='{team_name}' and date<'{selected_date.strftime('%Y%m%d')}'"
        response = get_last_5_games(sdql_query)
        if response:
            games = response.get('groups', [{}])[0].get('columns', [])
            return games[:5]  # Return only the last 5 games
    except Exception as e:
        print(f"Error fetching last 5 games for {team_name}: {e}")
    return []

def calculate_trends(last_5_games, home_team, away_team):
    """Calculate trends for home and away teams."""
    trends = {}
    data = pd.DataFrame(last_5_games)

    if data.empty:
        return {home_team: "Insufficient data", away_team: "Insufficient data"}

    for team in [home_team, away_team]:
        team_data = data[data['team'] == team]

        if team_data.shape[0] < 5:
            trends[team] = f"{team} has insufficient data for trends"
            continue

        # Calculate losses
        team_data['loss'] = team_data['points'] < team_data['o:points']
        loss_count = team_data['loss'].sum()

        trends[team] = f"{team} has lost {loss_count}/5 games"

    return trends

def analyze_trends_for_games(scores, selected_date):
    """Analyze trends for all games."""
    trends = {}

    for game in scores:
        home_team = game.get('home_team')
        away_team = game.get('away_team')

        if not home_team or not away_team:
            continue

        # Fetch last 5 games for both teams
        home_last_5 = get_last_5_games_for_team(home_team, selected_date)
        away_last_5 = get_last_5_games_for_team(away_team, selected_date)

        # Combine data for trend calculation
        last_5_games = home_last_5 + away_last_5
        game_trends = calculate_trends(last_5_games, home_team, away_team)

        trends[f"{home_team} vs {away_team}"] = game_trends

    return trends
