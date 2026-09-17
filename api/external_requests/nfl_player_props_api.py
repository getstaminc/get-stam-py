import os
import re
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv("ODDS_API_KEY")

NFL_PLAYER_PROPS_MARKETS = (
    "player_pass_yds,player_pass_tds,player_rush_yds,"
    "player_reception_yds,player_receptions,player_anytime_td"
)

# The player_anytime_td market lists team D/ST entries (e.g. "Arizona Cardinals
# D/ST") alongside skill-position players. Those aren't nfl_players rows.
_DEFENSE_SUFFIX_RE = re.compile(r"\s+D/ST$", re.IGNORECASE)


def _is_defense_entry(description: str) -> bool:
    return bool(description) and bool(_DEFENSE_SUFFIX_RE.search(description))


def get_nfl_player_props(event_id):
    for bookmaker in ["draftkings", "fanduel"]:
        url = (
            f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events/{event_id}/odds?"
            f"apiKey={api_key}&regions=us&markets={NFL_PLAYER_PROPS_MARKETS}"
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
            print(f"Error fetching NFL player props from {bookmaker}: {str(e)}")
            continue
    return {"error": "Player prop odds not available at this time."}


def combine_nfl_player_props(event_data):
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
                if not player or _is_defense_entry(player):
                    continue
                player_outcomes.setdefault(player, []).append(outcome)
            for player, outcomes in player_outcomes.items():
                combined_players.setdefault(player, {})
                if market_key == "player_anytime_td":
                    # Yes/No market — no point. Normalize to a 0.5 line so the
                    # table can treat it like the Over/Under markets.
                    yes = next((o for o in outcomes if (o.get("name") or "").lower() == "yes"), None)
                    combined_players[player][market_key] = {
                        "point": 0.5,
                        "over_price": yes.get("price") if yes else None,
                        "under_price": None,
                    }
                    continue
                over = next((o for o in outcomes if o.get("name") == "Over"), None)
                under = next((o for o in outcomes if o.get("name") == "Under"), None)
                point = over.get("point") if over else (under.get("point") if under else None)
                combined_players[player][market_key] = {
                    "point": point,
                    "over_price": over.get("price") if over else None,
                    "under_price": under.get("price") if under else None,
                }
        result["bookmakers"].append({
            "key": bookmaker.get("key"),
            "title": bookmaker.get("title"),
            "players": combined_players
        })
    return result
