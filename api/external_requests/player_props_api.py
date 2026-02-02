import os
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv("ODDS_API_KEY")

PLAYER_PROPS_MARKETS = "player_points,player_rebounds,player_assists,player_threes"
BOOKMAKERS = "draftkings"


def get_player_props(event_id):
    url = (
        f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds?"
        f"apiKey={api_key}&date=2026-01-26T02:45:00Z&regions=us&markets={PLAYER_PROPS_MARKETS}&oddsFormat=american&bookmakers={BOOKMAKERS}"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching player props: {str(e)}")
        return None


def combine_player_props(event_data):
    # event_data is the full response from the API
    # Extract commence_time, home_team, away_team, and combine player props by player
    result = {
        "commence_time": event_data.get("commence_time"),
        "home_team": event_data.get("home_team"),
        "away_team": event_data.get("away_team"),
        "bookmakers": []
    }
    for bookmaker in event_data.get("bookmakers", []):
        combined_players = {}
        for market in bookmaker.get("markets", []):
            market_key = market.get("key")
            for outcome in market.get("outcomes", []):
                player = outcome.get("description")
                if not player:
                    continue
                if player not in combined_players:
                    combined_players[player] = {}
                if market_key not in combined_players[player]:
                    combined_players[player][market_key] = []
                combined_players[player][market_key].append({
                    "name": outcome.get("name"),
                    "price": outcome.get("price"),
                    "point": outcome.get("point")
                })
        result["bookmakers"].append({
            "key": bookmaker.get("key"),
            "title": bookmaker.get("title"),
            "players": combined_players
        })
    return result
