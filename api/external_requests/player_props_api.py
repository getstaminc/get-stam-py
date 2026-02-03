import os
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv("ODDS_API_KEY")

PLAYER_PROPS_MARKETS = "player_points,player_rebounds,player_assists,player_threes"
BOOKMAKERS = "draftkings"


def get_player_props(event_id):
    # Try DraftKings first, then Fanduel if DraftKings has no player props
    for bookmaker in ["draftkings", "fanduel"]:
        url = (
            f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds?"
            f"apiKey={api_key}&regions=us&markets={PLAYER_PROPS_MARKETS}&oddsFormat=american&bookmakers={bookmaker}"
        )
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            # If there are player props for this bookmaker, return the data
            if data.get("bookmakers") and any(b.get("markets") for b in data["bookmakers"]):
                return data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching player props from {bookmaker}: {str(e)}")
            continue
    # If neither bookmaker has data, return None
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
            # Group outcomes by player
            player_outcomes = {}
            for outcome in market.get("outcomes", []):
                player = outcome.get("description")
                if not player:
                    continue
                if player not in player_outcomes:
                    player_outcomes[player] = []
                player_outcomes[player].append(outcome)
            # For each player, aggregate market data
            for player, outcomes in player_outcomes.items():
                if player not in combined_players:
                    combined_players[player] = {}
                # Find Over and Under outcomes
                over = next((o for o in outcomes if o.get("name") == "Over"), None)
                under = next((o for o in outcomes if o.get("name") == "Under"), None)
                # Use Over point as the main point
                point = over.get("point") if over else (under.get("point") if under else None)
                combined_players[player][market_key] = {
                    "point": point,
                    "over_price": over.get("price") if over else None,
                    "under_price": under.get("price") if under else None
                }
        result["bookmakers"].append({
            "key": bookmaker.get("key"),
            "title": bookmaker.get("title"),
            "players": combined_players
        })
    return result
