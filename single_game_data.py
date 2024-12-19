import requests
from datetime import datetime
from sdql_queries import get_last_5_games
from utils import convert_sport_key

api_key = '25312c698369617bc17f1f2634dd3996'

def get_game_details(sport_key, date, game_id):
    try:
        date_str = date.strftime('%Y-%m-%d')
        scores_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/?apiKey={api_key}&date={date_str}&dateFormat=iso"
        odds_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&bookmakers=draftkings&markets=h2h,spreads,totals&oddsFormat=american"

        scores_response = requests.get(scores_url)
        odds_response = requests.get(odds_url)

        scores_response.raise_for_status()
        odds_response.raise_for_status()

        scores = scores_response.json()
        odds = odds_response.json()

        game_details = {}
        for game in scores:
            if game['id'] == game_id:
                game_details['homeTeam'] = game['home_team']
                game_details['awayTeam'] = game['away_team']

                if game.get('scores') and game['scores'][0]:
                    game_details['homeScore'] = game['scores'][0].get('score', 'N/A')
                else:
                    game_details['homeScore'] = 'N/A'

                if game.get('scores') and game['scores'][1]:
                    game_details['awayScore'] = game['scores'][1].get('score', 'N/A')
                else:
                    game_details['awayScore'] = 'N/A'

                 # Fetch last 5 games for both teams, passing both arguments
                game_details['homeTeamLast5'] = get_last_5_games(game['home_team'], date, sport_key)
                game_details['awayTeamLast5'] = get_last_5_games(game['away_team'], date, sport_key)

                break

        if not game_details:
            return None

        for game in odds:
            if game['id'] == game_id:
                odds_text_list = []
                for bookmaker in game['bookmakers']:
                    for market in bookmaker['markets']:
                        market_key = market['key']
                        for outcome in market['outcomes']:
                            outcome_text = f"{market_key}: {outcome['name']}"
                            if market_key in ['spreads', 'totals'] and 'point' in outcome:
                                outcome_text += f" - {outcome['point']}"
                            outcome_text += f" - {outcome['price']}"
                            odds_text_list.append(outcome_text)
                game_details['oddsText'] = ', '.join(odds_text_list)
                break

        return game_details if game_details else None

    except requests.RequestException as e:
        print(f"Error fetching game details: {e}")
        return None
