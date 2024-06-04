from flask import Flask, jsonify, request, render_template
import requests
import datetime
from dateutil import parser

app = Flask(__name__)
port = 3000
api_key = '489331b7e9ff5b17f6f37e664ba10c08'

@app.route('/api/sports')
def get_sports():
    try:
        api_url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
        response = requests.get(api_url)
        response.raise_for_status()

        sports = response.json()
        return jsonify(sports)
    except Exception as e:
        print('Error fetching sports:', str(e))
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/sports/<sport_key>')
def get_sport_scores(sport_key):
    try:
        current_date = request.args.get('date', None)
        if not current_date:
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')

        selected_date_start = datetime.datetime.strptime(current_date, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
        selected_date_end = selected_date_start + datetime.timedelta(hours=23, minutes=59, seconds=59)

        print(f"Selected Date Start (UTC): {selected_date_start}")
        print(f"Selected Date End (UTC): {selected_date_end}")

        scores_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/?apiKey={api_key}&daysFrom=1&dateFormat=iso"
        odds_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&bookmakers=bovada&markets=h2h,spreads,totals&oddsFormat=american"

        scores_response = requests.get(scores_url)
        odds_response = requests.get(odds_url)

        scores_response.raise_for_status()
        odds_response.raise_for_status()

        scores = scores_response.json()
        odds = odds_response.json()

        filtered_scores = []
        for score in scores:
            commence_time_str = score['commence_time']
            commence_date = parser.parse(commence_time_str).astimezone(datetime.timezone.utc).date()
            print(f"Commence Date (UTC): {commence_date}")

            if commence_date == selected_date_start.date():
                filtered_scores.append(score)

        formatted_scores = []
        for match in filtered_scores:
            home_team = match.get('home_team', 'N/A')
            away_team = match.get('away_team', 'N/A')
            home_score = match['scores'][0]['score'] if match.get('scores') else 'N/A'
            away_score = match['scores'][1]['score'] if match.get('scores') else 'N/A'
            
            match_odds = next((odds_match for odds_match in odds if odds_match['id'] == match['id']), None)
            odds_text = 'N/A'
            if match_odds:
                odds_text_list = []
                for bookmaker in match_odds['bookmakers']:
                    for market in bookmaker['markets']:
                        market_key = market['key']
                        for outcome in market['outcomes']:
                            outcome_text = f"{market_key}: {outcome['name']}"
                            if market_key in ['spreads', 'totals'] and 'point' in outcome:
                                outcome_text += f" - {outcome['point']}"
                            outcome_text += f" - {outcome['price']}"
                            odds_text_list.append(outcome_text)
                odds_text = ', '.join(odds_text_list)
            
            formatted_scores.append({
                'homeTeam': home_team,
                'awayTeam': away_team,
                'homeScore': home_score,
                'awayScore': away_score,
                'oddsText': odds_text
            })

        return jsonify(formatted_scores)
    except Exception as e:
        print('Error fetching scores:', str(e))
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(port=port)

