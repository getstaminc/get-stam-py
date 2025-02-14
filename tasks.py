from celery_app import celery
from odds_api import get_odds_data
from datetime import datetime
import pytz
from dateutil import parser
from utils import convert_to_eastern, check_for_trends
import logging

eastern_tz = pytz.timezone('US/Eastern')

@celery.task(name='app.show_trends_task')
def show_trends_task(sport_key, date):
    logging.info("In show trends task")
    selected_date_start = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=eastern_tz)
    scores, odds = get_odds_data(sport_key, selected_date_start)
    if scores is None or odds is None:
        return {'error': 'Error fetching odds data'}

    filtered_scores = []
    for score in scores:
        commence_time_str = score['commence_time']
        commence_date = parser.parse(commence_time_str).astimezone(pytz.utc)
        commence_date_eastern = convert_to_eastern(commence_date)

        if commence_date_eastern.date() == selected_date_start.date():
            filtered_scores.append(score)

    formatted_scores = []
    for match in filtered_scores:
        home_team = match.get('home_team', 'N/A')
        away_team = match.get('away_team', 'N/A')
        home_score = match['scores'][0]['score'] if match.get('scores') else 'N/A'
        away_score = match['scores'][1]['score'] if match.get('scores') else 'N/A'

        match_odds = next((odds_match for odds_match in odds if odds_match['id'] == match['id']), None)
        odds_data = {'h2h': [], 'spreads': [], 'totals': []}

        if match_odds:
            for bookmaker in match_odds['bookmakers']:
                for market in bookmaker['markets']:
                    market_key = market['key']
                    for outcome in market['outcomes']:
                        outcome_text = f"{outcome['name']}"
                        if market_key in ['spreads', 'totals'] and 'point' in outcome:
                            outcome_text += f": {outcome['point']}"
                        if market_key == 'h2h':
                            price = outcome['price']
                            if price > 0:
                                outcome_text += f": +{price}"
                            else:
                                outcome_text += f": {price}"
                        else:
                            price = outcome['price']
                            if price > 0:
                                outcome_text += f" +{price}"
                            else:
                                outcome_text += f" {price}"
                        odds_data[market_key].append(outcome_text)

        formatted_scores.append({
            'homeTeam': home_team,
            'awayTeam': away_team,
            'homeScore': home_score,
            'awayScore': away_score,
            'odds': odds_data,
            'game_id': match['id'],
        })

    # Filter the games to include only those with trends
    games_with_trends = [game for game in formatted_scores if check_for_trends(game, selected_date_start, sport_key)['trend_detected']]

    return {
        'result': games_with_trends,
        'sport_key': sport_key,
        'current_date': date
    }