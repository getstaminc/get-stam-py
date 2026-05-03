import os
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv("ODDS_API_KEY")

MLB_PLAYER_PROPS_MARKETS = (
    "batter_hits,batter_home_runs,batter_rbis,batter_runs_scored,"
    "batter_total_bases,pitcher_strikeouts,pitcher_earned_runs,"
    "pitcher_hits_allowed,pitcher_walks"
)


def get_mlb_player_props(event_id):
    for bookmaker in ["draftkings", "fanduel"]:
        url = (
            f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{event_id}/odds?"
            f"apiKey={api_key}&regions=us&markets={MLB_PLAYER_PROPS_MARKETS}"
            f"&oddsFormat=american&bookmakers={bookmaker}"
        )
        try:
            response = requests.get(url)
            if response.status_code in (404, 422):
                try:
                    data = response.json()
                    if isinstance(data, dict) and (
                        data.get("error_code") == "EVENT_NOT_FOUND"
                        or "event not found" in str(data.get("message", "")).lower()
                    ):
                        return {"error": "Player prop odds not available at this time."}
                except Exception:
                    pass
                return {"error": "Player prop odds not available at this time."}
            response.raise_for_status()
            data = response.json()
            if data.get("bookmakers") and any(b.get("markets") for b in data["bookmakers"]):
                return data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching MLB player props from {bookmaker}: {str(e)}")
            continue
    return {"error": "Player prop odds not available at this time."}


def combine_mlb_player_props(event_data):
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
            player_outcomes = {}
            for outcome in market.get("outcomes", []):
                player = outcome.get("description")
                if not player:
                    continue
                if player not in player_outcomes:
                    player_outcomes[player] = []
                player_outcomes[player].append(outcome)
            for player, outcomes in player_outcomes.items():
                if player not in combined_players:
                    combined_players[player] = {}
                over = next((o for o in outcomes if o.get("name") == "Over"), None)
                under = next((o for o in outcomes if o.get("name") == "Under"), None)
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
