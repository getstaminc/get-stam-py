# single_game_data.py
import requests
from flask import render_template_string
from odds_api import api_key

def get_game_details(sport_key, date, game_id):
    try:
        date_str = date
        scores_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/?apiKey={api_key}&date={date_str}&dateFormat=iso"
        odds_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&bookmakers=bovada&markets=h2h,spreads,totals&oddsFormat=american"

        scores_response = requests.get(scores_url)
        odds_response = requests.get(odds_url)

        scores_response.raise_for_status()
        odds_response.raise_for_status()

        scores = scores_response.json()
        odds = odds_response.json()

        # Find the game based on the game_id
        game_details = next((game for game in scores if game['id'] == game_id), None)
        odds_details = next((odds_match for odds_match in odds if odds_match['id'] == game_id), None)

        if game_details and odds_details:
            home_team = game_details.get('home_team', 'N/A')
            away_team = game_details.get('away_team', 'N/A')
            home_score = game_details['scores'][0]['score'] if game_details.get('scores') else 'N/A'
            away_score = game_details['scores'][1]['score'] if game_details.get('scores') else 'N/A'

            odds_text_list = []
            for bookmaker in odds_details['bookmakers']:
                for market in bookmaker['markets']:
                    market_key = market['key']
                    for outcome in market['outcomes']:
                        outcome_text = f"{market_key}: {outcome['name']}"
                        if market_key in ['spreads', 'totals'] and 'point' in outcome:
                            outcome_text += f" - {outcome['point']}"
                        outcome_text += f" - {outcome['price']}"
                        odds_text_list.append(outcome_text)
            odds_text = ', '.join(odds_text_list)

            result = {
                'homeTeam': home_team,
                'awayTeam': away_team,
                'homeScore': home_score,
                'awayScore': away_score,
                'oddsText': odds_text
            }

            return render_template_string("""
                <html>
                <head>
                    <title>Game Details</title>
                    <style>
                        table {
                            width: 50%;
                            border-collapse: collapse;
                        }
                        table, th, td {
                            border: 1px solid black;
                        }
                        th, td {
                            padding: 8px;
                            text-align: left;
                        }
                        th {
                            background-color: #f2f2f2;
                        }
                    </style>
                </head>
                <body>
                    <h1>Game Details</h1>
                    {% if result %}
                        <table>
                            <thead>
                                <tr>
                                    <th>Home Team</th>
                                    <th>Away Team</th>
                                    <th>Home Score</th>
                                    <th>Away Score</th>
                                    <th>Odds</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>{{ result.homeTeam }}</td>
                                    <td>{{ result.awayTeam }}</td>
                                    <td>{{ result.homeScore }}</td>
                                    <td>{{ result.awayScore }}</td>
                                    <td>{{ result.oddsText }}</td>
                                </tr>
                            </tbody>
                        </table>
                    {% else %}
                        <p>No data available</p>
                    {% endif %}
                </body>
                </html>
            """, result=result)
        else:
            return render_template_string("<p>Game details not found</p>")

    except requests.exceptions.RequestException as e:
        print('Request error:', str(e))
        return render_template_string("<p>Error fetching game details</p>")
    except Exception as e:
        print('Error fetching game details:', str(e))
        return render_template_string("<p>Internal Server Error</p>")
