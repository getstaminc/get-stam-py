import os
from dotenv import load_dotenv
import requests
import datetime
import pytz

load_dotenv()  # Loads variables from .env into environment
api_key = os.getenv("ODDS_API_KEY")

SPORT_URL_TO_API_KEY = {
    "nfl": "americanfootball_nfl",
    "mlb": "baseball_mlb",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
    "ncaaf": "americanfootball_ncaaf",
    "ncaab": "basketball_ncaab",
    "epl": "soccer_epl",
    "nfl_preseason": "americanfootball_nfl_preseason",
}

def convert_sport_url_to_api_key(sport_url_key):
    return SPORT_URL_TO_API_KEY.get(sport_url_key, sport_url_key)

def get_odds_data(sport, date):
    eastern_tz = pytz.timezone('US/Eastern')
    sport_key = convert_sport_url_to_api_key(sport)
    if date and date.tzinfo is None:
        date = eastern_tz.localize(date)
    date_str = date.strftime('%Y-%m-%d') if date else ''
    scores_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/?daysFrom=2&apiKey={api_key}"
    print(f"Scores URL: {scores_url}")
    if date_str:
        scores_url += f"&date={date_str}&dateFormat=iso"
    # Use 'bovada' for soccer_epl, otherwise 'draftkings'
    bookmaker = "bovada" if sport_key == "soccer_epl" else "draftkings"
    odds_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&bookmakers={bookmaker}&markets=h2h,spreads,totals&oddsFormat=american"

    try:
        print(f"Making request to scores URL: {scores_url}")
        scores_response = requests.get(scores_url)
        print(f"Making request to odds URL: {odds_url}")
        odds_response = requests.get(odds_url)
        
        print(f"Scores response status: {scores_response.status_code}")
        print(f"Odds response status: {odds_response.status_code}")
        
        scores_response.raise_for_status()
        odds_response.raise_for_status()
        
        scores_data = scores_response.json()
        odds_data = odds_response.json()
        
        print(f"Scores data length: {len(scores_data)}")
        print(f"Odds data length: {len(odds_data)}")
        
        return scores_data, odds_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching odds data: {str(e)}")
        return None, None