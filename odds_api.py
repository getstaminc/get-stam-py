# odds_api.py
import requests
import datetime

api_key = '25312c698369617bc17f1f2634dd3996'

def get_odds_data(sport_key, date):
    try:
        date_str = date.strftime('%Y-%m-%d')
        scores_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/?apiKey={api_key}&date={date_str}&dateFormat=iso"
        odds_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&bookmakers=bovada&markets=h2h,spreads,totals&oddsFormat=american"

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
