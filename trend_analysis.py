import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser  # Add this import
import pytz  # Add this import if needed
from utils import convert_team_name, convert_sport_key
from sdql_queries import get_last_5_games, get_last_5_games_vs_opponent


def get_last_5_games_for_team(team_name, selected_date, sport_key):
    """Fetch last 5 games for a team."""
    try:
        # Format the selected date for SDQL
        formatted_date = selected_date.strftime('%Y%m%d')
        
        # Build the SDQL query
        sdql_query = f"date,team,site,points,total,o:team,o:line,o:points,line@team='{team_name}' and date<{formatted_date} and (_tNNNNN is None or N5:date>{formatted_date})"
        
        # Fetch data using get_last_5_games
        response = get_last_5_games(team_name, formatted_date, sport_key)
        
        if response:
            games = response.get('groups', [{}])[0].get('columns', [])
            return games  # Return the parsed games data
            
    except Exception as e:
        print(f"Error fetching last 5 games for {team_name}: {e}")
    
    return []


def get_last_5_matchups_between_teams(home_team, away_team, selected_date, sport_key):
    """Fetch last 5 matchups between two teams."""
    try:
        return get_last_5_games_vs_opponent(
            team=home_team,
            opponent=away_team,
            today_date=selected_date,
            sport_key=sport_key
        )
    except Exception as e:
        print(f"Error fetching last 5 matchups between {home_team} and {away_team}: {e}")
    return []


def calculate_team_trends(last_5_games, team):
    """Calculate trends for a team."""
    trends = []
    data = pd.DataFrame(last_5_games)

    if data.empty or data.shape[0] < 5:
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


def analyze_trends_for_games(filtered_scores, selected_date, sport_key):
    """Analyze trends for pre-filtered games on a specific date."""
    print(f"Analyzing trends for {selected_date.strftime('%Y-%m-%d')}")
    trends = {}

    for game in filtered_scores:
        try:
            commence_time = parser.parse(game.get('commence_time', '')).astimezone(pytz.timezone('America/New_York'))
            print(f"Commence time for game: {commence_time}")

            # Ensure the game falls within the selected date range
            if commence_time.date() != selected_date.date():
                continue
        except Exception as e:
            print(f"Error parsing commence_time for game: {game}. Error: {e}")
            continue

        home_team = game.get('home_team')
        away_team = game.get('away_team')

        if not home_team or not away_team:
            print(f"Missing team information for game: {game}")
            continue

        # Fetch last 5 games and matchups
        home_last_5 = get_last_5_games_for_team(home_team, selected_date, sport_key)
        away_last_5 = get_last_5_games_for_team(away_team, selected_date, sport_key)
        last_5_matchups = get_last_5_matchups_between_teams(home_team, away_team, selected_date, sport_key)

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

    # Log final trends
    if not trends:
        print("No trends found for games on this date.")
    print(f"Final trends: {trends}")
    return trends