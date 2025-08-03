"""
Date utility functions for handling timezone conversions and date operations
"""
from datetime import datetime, timedelta, date
import pytz
from dateutil import parser

eastern_tz = pytz.timezone('US/Eastern')

def convert_to_eastern(dt):
    """Convert datetime to Eastern timezone"""
    return dt.astimezone(eastern_tz)

def get_next_game_date_within_7_days(scores, selected_date_start):
    """Find the next game date within 7 days"""
    today = datetime.now(pytz.utc)
    eastern = pytz.timezone('US/Eastern')
    
    for score in scores:
        commence_time_str = score['commence_time']
        commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
        commence_date_eastern = commence_date.astimezone(eastern)
        
        if (commence_date_eastern.date() > selected_date_start.date() and 
            commence_date_eastern.date() <= (today + timedelta(days=7)).date()):
            return commence_date_eastern.strftime('%Y-%m-%d')
    
    return None

def filter_games_by_date(scores, selected_date_start):
    """Filter games by selected date"""
    if not selected_date_start:
        return scores
    
    filtered_scores = []
    for score in scores:
        commence_time_str = score['commence_time']
        commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
        if convert_to_eastern(commence_date).date() == selected_date_start.date():
            filtered_scores.append(score)
    
    return filtered_scores

def format_commence_time(commence_time_str):
    """Format commence time to ISO string"""
    if not commence_time_str:
        return None
    
    commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
    return commence_date.isoformat()

def is_today(commence_time_str, selected_date_start=None):
    """Check if game is today"""
    if selected_date_start:
        return selected_date_start.date() == date.today()
    
    if commence_time_str:
        commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
        return commence_date.date() == datetime.now(pytz.utc).date()
    
    return False
