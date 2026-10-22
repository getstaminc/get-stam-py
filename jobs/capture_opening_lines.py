"""
Nightly job: capture each new NFL/NCAAF/MLB/NHL game's opening line by scanning
backward from kickoff with the Historical Odds API, stopping at the first snapshot
where the market has posted a price. Safe to re-run — already-captured games (and
games whose market hasn't opened yet) are skipped.

Run nightly via Heroku Scheduler:
  python jobs/capture_opening_lines.py
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from api.external_requests.odds_api import get_odds_data
from api.services.opening_lines_service import OpeningLinesService

ODDS_API_KEY = os.getenv("ODDS_API_KEY")

# Keys are the Odds-API sport key GameService already uses — stored verbatim as
# `sport` in game_opening_lines, see Task 1's note on why.
SPORT_CONFIGS = {
    "americanfootball_nfl": {"lookahead_days": 21, "scan_days_back": 21, "scan_step_hours": 24},
    "americanfootball_ncaaf": {"lookahead_days": 21, "scan_days_back": 21, "scan_step_hours": 24},
    "baseball_mlb": {"lookahead_days": 3, "scan_days_back": 3, "scan_step_hours": 12},
    "icehockey_nhl": {"lookahead_days": 3, "scan_days_back": 3, "scan_step_hours": 12},
}


def get_upcoming_games_and_current_odds(sport_key, lookahead_days):
    """Return (upcoming_games, odds_by_event_id) for games starting in the next
    `lookahead_days`. `odds_by_event_id` only contains entries for games that
    currently have posted draftkings odds (i.e. whose market has opened)."""
    scores, odds = get_odds_data(sport_key, None)
    if scores is None:
        return [], {}

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=lookahead_days)
    upcoming = []
    for game in scores:
        if game.get("completed"):
            continue
        commence = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
        if now <= commence <= horizon:
            upcoming.append(game)

    odds_by_event_id = {o["id"]: o for o in (odds or []) if o.get("bookmakers")}
    return upcoming, odds_by_event_id


def parse_draftkings_markets(odds_game):
    """Extract spread/total/moneyline values from an odds-api game's draftkings
    bookmaker entry. Returns None if draftkings hasn't posted any markets for it."""
    if not odds_game or not odds_game.get("bookmakers"):
        return None

    draftkings = next((b for b in odds_game["bookmakers"] if b["key"] == "draftkings"), None)
    if not draftkings or not draftkings.get("markets"):
        return None

    home_team = odds_game["home_team"]
    away_team = odds_game["away_team"]
    result = {
        "home_spread_point": None, "home_spread_price": None,
        "away_spread_point": None, "away_spread_price": None,
        "home_moneyline": None, "away_moneyline": None,
        "total_point": None, "over_price": None, "under_price": None,
    }

    for market in draftkings["markets"]:
        if market["key"] == "h2h":
            for outcome in market["outcomes"]:
                if outcome["name"] == home_team:
                    result["home_moneyline"] = outcome.get("price")
                elif outcome["name"] == away_team:
                    result["away_moneyline"] = outcome.get("price")
        elif market["key"] == "spreads":
            for outcome in market["outcomes"]:
                if outcome["name"] == home_team:
                    result["home_spread_point"] = outcome.get("point")
                    result["home_spread_price"] = outcome.get("price")
                elif outcome["name"] == away_team:
                    result["away_spread_point"] = outcome.get("point")
                    result["away_spread_price"] = outcome.get("price")
        elif market["key"] == "totals":
            for outcome in market["outcomes"]:
                if outcome["name"] == "Over":
                    result["total_point"] = outcome.get("point")
                    result["over_price"] = outcome.get("price")
                elif outcome["name"] == "Under":
                    result["under_price"] = outcome.get("price")

    if all(v is None for v in result.values()):
        return None
    return result


def get_historical_odds_at_time(sport_key, snapshot_time, retries=3, delay=1):
    """Fetch a historical odds snapshot for `sport_key` at or before `snapshot_time`
    (a UTC datetime). Returns (events, actual_snapshot_timestamp)."""
    time_str = snapshot_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = (
        f"https://api.the-odds-api.com/v4/historical/sports/{sport_key}/odds/"
        f"?apiKey={ODDS_API_KEY}&regions=us&bookmakers=draftkings"
        f"&markets=h2h,spreads,totals&oddsFormat=american&date={time_str}"
    )
    for attempt in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            payload = response.json()
            return payload.get("data", []), payload.get("timestamp", time_str)
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching historical odds (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    return [], None


def find_opening_snapshot(event_id, commence_time, scan_days_back, scan_step_hours,
                           fetch_historical_odds, now=None):
    """Scan forward from (commence_time - scan_days_back) toward commence_time in
    scan_step_hours increments. Returns (markets_dict, snapshot_time) for the first
    snapshot where this event has draftkings odds — i.e. the opening line. Returns
    (None, None) if no snapshot in the window has odds for this event.

    The scan never requests a timestamp later than `now` (defaults to the real
    current time): a snapshot request for a future timestamp can get clamped by
    the Historical Odds API to its latest available (i.e. current) snapshot,
    which would otherwise be mistaken for the opening line and, since opening
    lines are write-once, could never be corrected."""
    if now is None:
        now = datetime.now(timezone.utc)
    scan_upper_bound = min(commence_time, now)
    cursor = commence_time - timedelta(days=scan_days_back)
    while cursor < scan_upper_bound:
        data, actual_timestamp = fetch_historical_odds(cursor)
        game = next((g for g in data if g.get("id") == event_id), None)
        markets = parse_draftkings_markets(game) if game else None
        if markets:
            return markets, actual_timestamp
        cursor += timedelta(hours=scan_step_hours)
    return None, None


def capture_for_sport(sport_key, config, sleep_between_calls=0.5, snapshot_cache=None):
    """Capture opening lines for every not-yet-captured, already-open game in the
    given sport's lookahead window. Returns the count of games captured.

    `snapshot_cache` memoizes historical-odds fetches by (sport_key, snapshot_time)
    -> (data, actual_timestamp). Games sharing a kickoff time (e.g. a Sunday NFL
    slate) have identical scan grids, so without this every game would re-request
    the exact same snapshot the Historical Odds API already returns for all events
    at once. Defaults to a cache scoped to this single call; pass a shared dict to
    memoize across multiple capture_for_sport calls in the same run."""
    print(f"\n=== {sport_key} ===")
    upcoming_games, odds_by_event_id = get_upcoming_games_and_current_odds(
        sport_key, config["lookahead_days"]
    )
    print(f"{len(upcoming_games)} upcoming game(s) in the next {config['lookahead_days']} day(s)")

    if snapshot_cache is None:
        snapshot_cache = {}

    def fetch(snapshot_time, _sport_key=sport_key, _sleep=sleep_between_calls):
        cache_key = (_sport_key, snapshot_time)
        if cache_key in snapshot_cache:
            return snapshot_cache[cache_key]
        time.sleep(_sleep)
        result = get_historical_odds_at_time(_sport_key, snapshot_time)
        snapshot_cache[cache_key] = result
        return result

    captured = 0
    for game in upcoming_games:
        event_id = game["id"]
        try:
            if OpeningLinesService.has_opening_line(sport_key, event_id):
                continue
            if event_id not in odds_by_event_id:
                continue  # market hasn't opened yet — picked up on a future night

            commence_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))

            markets, snapshot_time_str = find_opening_snapshot(
                event_id, commence_time, config["scan_days_back"], config["scan_step_hours"], fetch
            )
            if not markets:
                print(f"  No historical snapshot found yet for {game['home_team']} vs {game['away_team']}")
                continue

            snapshot_time = (
                datetime.fromisoformat(snapshot_time_str.replace("Z", "+00:00"))
                if isinstance(snapshot_time_str, str) else commence_time
            )
            OpeningLinesService.save_opening_line(
                sport_key, event_id, game["home_team"], game["away_team"],
                commence_time, snapshot_time, markets,
            )
            captured += 1
            print(f"  Captured opening line: {game['home_team']} vs {game['away_team']} (opened {snapshot_time})")
        except Exception as e:
            print(f"  Error processing {game.get('home_team')} vs {game.get('away_team')} "
                  f"(event_id={event_id}): {e}")
            continue

    print(f"{sport_key}: captured {captured} new opening line(s)")
    return captured


def main():
    total = 0
    any_failed = False
    for sport_key, config in SPORT_CONFIGS.items():
        try:
            total += capture_for_sport(sport_key, config)
        except Exception as e:
            any_failed = True
            print(f"Error capturing opening lines for {sport_key}: {e}")
    print(f"\nDone. Captured {total} opening line(s) across all sports.")
    if any_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
