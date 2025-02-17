# utils.py

# import sys
# import os

# # Add the directory containing sdql_queries.py to the Python path
# sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import pytz
from datetime import datetime
from shared_utils import convert_to_eastern, convert_team_name, convert_sport_key
from sdql_queries import get_last_5_games, get_last_5_games_vs_opponent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def mlb_totals(runs, opponent_runs, total):
    return (runs + opponent_runs) > total

def other_totals(points, opponent_points, total):
            combined_score = points + opponent_points
            return combined_score < total

eastern_tz = pytz.timezone('US/Eastern')

def convert_to_eastern(utc_time):
    if utc_time is None:
        return None
    utc_time = utc_time.replace(tzinfo=pytz.utc)
    eastern_time = utc_time.astimezone(eastern_tz)
    return eastern_time

def check_for_trends(game, selected_date_start, sport_key):


    home_team_last_5 = get_last_5_games(game['homeTeam'], selected_date_start, sport_key) or []
    away_team_last_5 = get_last_5_games(game['awayTeam'], selected_date_start, sport_key) or []
    last_5_vs_opponent = get_last_5_games_vs_opponent(
        team=game['homeTeam'],
        opponent=game['awayTeam'],
        today_date=selected_date_start,
        sport_key=sport_key
    ) or []

    home_trend = detect_trends(home_team_last_5, sport_key)
    away_trend = detect_trends(away_team_last_5, sport_key)
    vs_opponent_trend = detect_trends(last_5_vs_opponent, sport_key)

    trend_detected = home_trend or away_trend or vs_opponent_trend

    return {
        'home_trend': home_trend,
        'away_trend': away_trend,
        'vs_opponent_trend': vs_opponent_trend,
        'trend_detected': trend_detected
    }

def detect_trends(games, sport_key):
    def is_winner(points, o_points):
        if points is None or o_points is None:
            return None
        return points > o_points

    def calculate_line_result(points, line, o_points):
        if points is None or line is None or o_points is None:
            return None, ''
        
        # Check for invalid values
        if points == '-' or line == '-' or o_points == '-':
            return None, ''
        
        points = float(points)
        line = float(line)
        o_points = float(o_points)

        if points + line > o_points:
            return True, 'green-bg'
        elif points + line < o_points:
            return False, 'red-bg'
        else:
            return None, ''

    def other_totals(points, o_points, total):
        if points is None or o_points is None or total is None:
            logger.error("One of the values is None: points={}, o_points={}, total={}".format(points, o_points, total))
            return None, ''
        
        # Check for invalid values
        if points == '-' or o_points == '-' or total == '-':
            logger.error("One of the values is invalid: points={}, o_points={}, total={}".format(points, o_points, total))
            return None, ''
        
        try:
            points = float(points)
            o_points = float(o_points)
            total = float(total)
        except ValueError as e:
            logger.error(f"Error converting values to float: {e}")
            return None, ''

        total_score = points + o_points
        if total_score > total:
            return True, 'green-bg'
        elif total_score < total:
            return False, 'red-bg'
        else:
            return None, ''

    if sport_key == 'icehockey_nhl':
        points_key = 'goals'
    else:
        points_key = 'points'

    # Check for trends in the 'team' column
    team_colors = []
    for game in games:
        result = is_winner(game[points_key], game[f'o:{points_key}'])
        if result is not None:
            color = 'green-bg' if result else 'red-bg'
            team_colors.append(color)
    if team_colors.count('green-bg') == 5 or team_colors.count('red-bg') == 5:
        return True

    # Check for trends in the 'points' column
    points_colors = []
    for game in games:
        result = is_winner(game[points_key], game[f'o:{points_key}'])
        if result is not None:
            color = 'green-bg' if result else 'red-bg'
            points_colors.append(color)
    if points_colors.count('green-bg') == 5 or points_colors.count('red-bg') == 5:
        return True

    # Skip line trend check for NHL
    if sport_key != 'icehockey_nhl':
        # Check for trends in the 'line' column
        line_colors = []
        for game in games:
            result, color = calculate_line_result(game[points_key], game['line'], game[f'o:{points_key}'])
            if result is not None:
                line_colors.append(color)
        if line_colors.count('green-bg') == 5 or line_colors.count('red-bg') == 5:
            return True

    # Check for trends in the 'total' column
    total_colors = []
    for game in games:
        result, color = other_totals(game[points_key], game[f'o:{points_key}'], game['total'])
        if result is not None:
            total_colors.append(color)
    if total_colors.count('green-bg') == 5 or total_colors.count('red-bg') == 5:
        return True

    return False