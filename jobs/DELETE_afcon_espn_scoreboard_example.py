#!/usr/bin/python3

import requests
import json
from datetime import datetime, date

def get_afcon_games_from_espn(target_date=None):
    """
    Get AFCON game results from ESPN API.
    
    Args:
        target_date: Date string in format 'YYYYMMDD' or date object. 
                    If None, gets all recent games.
    """
    
    base_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/caf.nations/scoreboard"
    
    params = {}
    if target_date:
        if isinstance(target_date, date):
            date_str = target_date.strftime('%Y%m%d')
        else:
            date_str = target_date
        params['dates'] = date_str
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"🏆 AFCON Tournament: {data.get('leagues', [{}])[0].get('name', 'Africa Cup of Nations')}")
        print(f"📅 Season: {data.get('leagues', [{}])[0].get('season', {}).get('displayName', 'N/A')}")
        print()
        
        games = data.get('events', [])
        
        if not games:
            print("No games found for the specified date")
            return []
        
        completed_games = []
        
        for game in games:
            game_info = parse_espn_afcon_game(game)
            completed_games.append(game_info)
            print_game_result(game_info)
        
        return completed_games
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching AFCON data: {e}")
        return []

def parse_espn_afcon_game(game_data):
    """Parse ESPN AFCON game data into a structured format."""
    
    competition = game_data.get('competitions', [{}])[0]
    competitors = competition.get('competitors', [])
    
    if len(competitors) != 2:
        return None
    
    home_team = competitors[0]
    away_team = competitors[1]
    
    # Determine winner based on advance status or score
    home_advanced = home_team.get('advance', False)
    away_advanced = away_team.get('advance', False)
    
    # Get scores (regular time and shootout if applicable)
    home_score = int(home_team.get('score', 0))
    away_score = int(away_team.get('score', 0))
    home_penalty_score = home_team.get('shootoutScore')
    away_penalty_score = away_team.get('shootoutScore')
    
    # Game status
    status = competition.get('status', {})
    is_completed = status.get('type', {}).get('completed', False)
    status_detail = status.get('type', {}).get('shortDetail', 'Unknown')
    
    return {
        'espn_game_id': game_data.get('id'),
        'date': game_data.get('date'),
        'home_team': {
            'name': home_team.get('team', {}).get('displayName'),
            'abbreviation': home_team.get('team', {}).get('abbreviation'),
            'score': home_score,
            'penalty_score': home_penalty_score,
            'advanced': home_advanced
        },
        'away_team': {
            'name': away_team.get('team', {}).get('displayName'), 
            'abbreviation': away_team.get('team', {}).get('abbreviation'),
            'score': away_score,
            'penalty_score': away_penalty_score,
            'advanced': away_advanced
        },
        'is_completed': is_completed,
        'status_detail': status_detail,
        'venue': competition.get('venue', {}).get('displayName'),
        'attendance': competition.get('attendance', 0),
        'round': game_data.get('season', {}).get('type', {}).get('name', 'Unknown')
    }

def print_game_result(game_info):
    """Print a formatted game result."""
    if not game_info:
        return
    
    home = game_info['home_team']
    away = game_info['away_team']
    
    # Format the score line
    if game_info['is_completed']:
        if home['penalty_score'] is not None and away['penalty_score'] is not None:
            # Game went to penalties
            score_line = f"{home['score']}-{away['score']} ({home['penalty_score']}-{away['penalty_score']} pens)"
            winner = "🏆" if home['advanced'] else ""
            loser = "🏆" if away['advanced'] else ""
            print(f"⚽ {away['name']} {away['score']} - {home['score']} {home['name']} {winner}")
            print(f"   Penalties: {away['penalty_score']}-{home['penalty_score']} {'✅' if away['advanced'] else '❌'} {'✅' if home['advanced'] else '❌'}")
        else:
            # Regular result
            winner_marker = ""
            if home['score'] > away['score']:
                winner_marker = " 🏆"
            elif away['score'] > home['score']:
                winner_marker = "🏆 "
            else:
                winner_marker = " 🤝 "
            
            print(f"⚽ {away['name']} {away['score']} - {home['score']} {home['name']}{winner_marker}")
    else:
        print(f"🔜 {away['name']} vs {home['name']} - {game_info['status_detail']}")
    
    print(f"   📍 {game_info['venue']} | 🎪 {game_info['round']}")
    if game_info['attendance'] > 0:
        print(f"   👥 {game_info['attendance']:,} attendance")
    print()

if __name__ == "__main__":
    print("=== ESPN AFCON Scoreboard ===\n")
    
    # Get recent AFCON games 
    recent_games = get_afcon_games_from_espn()
    
    # You can also get games for a specific date:
    # yesterday_games = get_afcon_games_from_espn("20260103")
    
    print(f"Found {len(recent_games)} games")