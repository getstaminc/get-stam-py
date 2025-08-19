# odds_api.py
import requests
import datetime
import pytz  # Import pytz for timezone handling

api_key = 'e143ef401675904470a5b72e6145091a'

def get_odds_data(sport_key, date):
    try:
        # Ensure date is in Eastern timezone
        eastern_tz = pytz.timezone('US/Eastern')
        if date.tzinfo is None:
            date = eastern_tz.localize(date)  # Localize to Eastern if naive

        date_str = date.strftime('%Y-%m-%d')
        scores_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/?apiKey={api_key}&date={date_str}&dateFormat=iso"
        # Define a list of all known soccer sport keys (customize as needed)
        soccer_sports = [
            'soccer_epl',
            'soccer_france_ligue_one',
            'soccer_germany_bundesliga',
            'soccer_italy_serie_a',
            'soccer_spain_la_liga',
            'soccer_uefa_champs_league',
            'soccer_uefa_europa_league'
        ]

        # Adjust odds URL based on sport type
        if sport_key in soccer_sports:
            odds_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&bookmakers=bovada&markets=h2h,spreads,totals&oddsFormat=american"
        else:
            odds_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&bookmakers=draftkings&markets=h2h,spreads,totals&oddsFormat=american"

        # Make requests
        scores_response = requests.get(scores_url)
        odds_response = requests.get(odds_url)

        scores_response.raise_for_status()
        odds_response.raise_for_status()

        scores = scores_response.json()
        odds = odds_response.json()

        return scores, odds
    except requests.exceptions.RequestException as e:
        print(f"Error fetching odds data: {str(e)}")
        print(f"Error fetching odds data: {e.status_code} {e.reason}")
        return None, None

def get_sports():
    try:
        api_url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print('Error fetching sports:', str(e))
        return None
