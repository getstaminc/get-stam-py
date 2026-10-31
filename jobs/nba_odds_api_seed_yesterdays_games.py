#!/usr/bin/env python3
"""Seed yesterday's NBA games from the Odds API, enriched with ESPN data for
fields the Odds API doesn't provide (quarter scores, playoffs, overtime).
Replaces the SDQL-based jobs/nba_seed_yesterdays_games.py.

game_site is hardcoded 'home' -- this data has never recorded a neutral-site
NBA game (the old SDQL job's own query only ever selected site='home'), same
precedent as the NHL migration.
"""
import os
import sys
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text
import shared_utils
import json

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ESPN_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_completed_nba_games_for_date(target_date_str: str, retries=3, delay=2):
    """Odds API current (non-historical) scores for the last 3 days, filtered
    to games whose Eastern-converted commence date matches target_date_str."""
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/scores/"
    params = {"apiKey": ODDS_API_KEY, "daysFrom": 3, "dateFormat": "iso"}

    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            games = response.json()
            matched = []
            for game in games:
                if not game.get("completed") or not game.get("scores"):
                    continue
                commence_utc = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
                commence_et = shared_utils.convert_to_eastern(commence_utc)
                if str(commence_et.date()) == target_date_str:
                    matched.append(game)
            return matched
        except requests.exceptions.RequestException as e:
            print(f"Error fetching scores (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise
    return []


def get_historical_odds_for_date(date_str: str, retries=3, delay=2):
    """Historical h2h/spreads/totals odds for a date (yesterday's market has
    closed by the time this job runs, so the current-odds endpoint won't
    have it). No bookmakers filter here -- parse_odds_data picks per-market."""
    url = "https://api.the-odds-api.com/v4/historical/sports/basketball_nba/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "date": f"{date_str}T00:00:00Z",
    }
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


def _market_from_preferred_bookmaker(bookmakers, market_key, preferred="draftkings"):
    """Return the named market dict from the preferred bookmaker if it has
    one, else from the first bookmaker (response order) that does."""
    preferred_bm = next((bm for bm in bookmakers if bm["key"] == preferred), None)
    if preferred_bm:
        market = next((m for m in preferred_bm.get("markets", []) if m["key"] == market_key), None)
        if market:
            return market
    for bm in bookmakers:
        market = next((m for m in bm.get("markets", []) if m["key"] == market_key), None)
        if market:
            return market
    return None


def parse_odds_data(odds_game: dict) -> dict:
    """Extract moneyline, spread, and total -- each market independently
    sourced per _market_from_preferred_bookmaker's fallback rule."""
    result = {
        "home_money_line": None, "away_money_line": None,
        "home_line": None, "away_line": None, "total": None,
    }
    bookmakers = odds_game.get("bookmakers", [])
    if not bookmakers:
        return result

    home_team = odds_game["home_team"]
    away_team = odds_game["away_team"]

    h2h = _market_from_preferred_bookmaker(bookmakers, "h2h")
    if h2h:
        for outcome in h2h["outcomes"]:
            if outcome["name"] == home_team:
                result["home_money_line"] = outcome["price"]
            elif outcome["name"] == away_team:
                result["away_money_line"] = outcome["price"]

    spreads = _market_from_preferred_bookmaker(bookmakers, "spreads")
    if spreads:
        for outcome in spreads["outcomes"]:
            if outcome["name"] == home_team:
                result["home_line"] = outcome.get("point")
            elif outcome["name"] == away_team:
                result["away_line"] = outcome.get("point")

    totals = _market_from_preferred_bookmaker(bookmakers, "totals")
    if totals:
        over = next((o for o in totals["outcomes"] if o["name"] == "Over"), None)
        if over:
            result["total"] = over.get("point")

    return result


def get_espn_enrichment(target_date_str: str, home_team: str, away_team: str) -> dict:
    """Fetch ESPN's NBA summary for the game matching home_team/away_team on
    target_date_str. Returns an all-None dict if the ESPN game can't be
    matched or any request fails -- enrichment is never allowed to drop the
    game itself, only to be missing."""
    empty = {
        "home_quarter_scores": None, "away_quarter_scores": None,
        "playoffs": None,
    }
    date_compact = target_date_str.replace("-", "")
    try:
        resp = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
            params={"dates": date_compact, "limit": 50}, headers=ESPN_HEADERS, timeout=30,
        )
        resp.raise_for_status()
        events = resp.json().get("events", [])
    except requests.exceptions.RequestException as e:
        print(f"  ESPN scoreboard fetch failed: {e}")
        return empty

    espn_event_id = None
    for event in events:
        comp = event.get("competitions", [{}])[0]
        competitors = {c.get("homeAway"): c.get("team", {}).get("displayName") for c in comp.get("competitors", [])}
        espn_home = shared_utils.convert_team_name(competitors.get("home", ""))
        espn_away = shared_utils.convert_team_name(competitors.get("away", ""))
        if espn_home == home_team and espn_away == away_team:
            espn_event_id = event.get("id")
            break

    if not espn_event_id:
        print(f"  Could not match ESPN event for {away_team} @ {home_team} on {target_date_str}")
        return empty

    try:
        resp = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary",
            params={"event": espn_event_id, "enable": "boxscore"}, headers=ESPN_HEADERS, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"  ESPN summary fetch failed for event {espn_event_id}: {e}")
        return empty

    try:
        header = data.get("header", {})
        comp = header.get("competitions", [{}])[0]
        season_type = header.get("season", {}).get("type")

        home_quarter_scores = away_quarter_scores = None
        for competitor in comp.get("competitors", []):
            scores = [int(ls.get("displayValue", 0)) for ls in competitor.get("linescores", [])]
            if competitor.get("homeAway") == "home":
                home_quarter_scores = scores
            elif competitor.get("homeAway") == "away":
                away_quarter_scores = scores

        return {
            "home_quarter_scores": home_quarter_scores,
            "away_quarter_scores": away_quarter_scores,
            "playoffs": (season_type == 3) if season_type is not None else None,
        }
    except (KeyError, ValueError, TypeError) as e:
        print(f"  ESPN summary parse failed for event {espn_event_id}: {e}")
        return empty


def seed_yesterdays_nba_games():
    print("Starting NBA game seeding (Odds API + ESPN)...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        games = get_completed_nba_games_for_date(yesterday)
        if not games:
            print(f"No completed NBA games found for {yesterday}")
            return

        odds_data = get_historical_odds_for_date(yesterday)
        odds_lookup = {g["id"]: g for g in odds_data}

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NBA'")).mappings()
        }

        inserted = 0
        for game in games:
            db_home = shared_utils.convert_team_name(game["home_team"])
            db_away = shared_utils.convert_team_name(game["away_team"])
            home_team_id = teams_dict.get(db_home)
            away_team_id = teams_dict.get(db_away)
            if home_team_id is None or away_team_id is None:
                print(f"Skipping {game['away_team']} @ {game['home_team']} - unresolved team id")
                continue

            home_points = away_points = None
            for score in game["scores"]:
                db_name = shared_utils.convert_team_name(score["name"])
                if db_name == db_home:
                    home_points = int(score["score"])
                elif db_name == db_away:
                    away_points = int(score["score"])
            if home_points is None or away_points is None:
                print(f"Skipping {game['away_team']} @ {game['home_team']} - missing score")
                continue

            existing = conn.execute(text("""
                SELECT 1 FROM nba_games_1
                WHERE odds_event_id = :odds_event_id
                   OR (game_date = :game_date AND home_team_id = :home_team_id AND away_team_id = :away_team_id)
            """), {
                "odds_event_id": game["id"], "game_date": yesterday,
                "home_team_id": home_team_id, "away_team_id": away_team_id,
            }).fetchone()
            if existing:
                print(f"Already seeded: {db_away} @ {db_home} on {yesterday}")
                continue

            odds_info = parse_odds_data(odds_lookup.get(game["id"], {}))
            enrichment = get_espn_enrichment(yesterday, db_home, db_away)

            home_qs = enrichment["home_quarter_scores"]
            away_qs = enrichment["away_quarter_scores"]
            if home_qs and away_qs:
                home_first_half = sum(home_qs[:2])
                away_first_half = sum(away_qs[:2])
                home_second_half = sum(home_qs[2:4])
                away_second_half = sum(away_qs[2:4])
                home_overtime = home_qs[4] if len(home_qs) > 4 else None
                away_overtime = away_qs[4] if len(away_qs) > 4 else None
            else:
                home_first_half = away_first_half = None
                home_second_half = away_second_half = None
                home_overtime = away_overtime = None

            print(f"Inserting: {db_away} {away_points} @ {db_home} {home_points} on {yesterday}")

            conn.execute(text("""
                INSERT INTO nba_games_1 (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_points, away_points, total_points, total_margin, home_line, away_line,
                    home_quarter_scores, away_quarter_scores, home_first_half_points, away_first_half_points,
                    home_second_half_points, away_second_half_points, home_overtime_points, away_overtime_points,
                    home_money_line, away_money_line, playoffs, total, odds_event_id
                ) VALUES (
                    :game_date, 'home', :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                    :home_quarter_scores, :away_quarter_scores, :home_first_half_points, :away_first_half_points,
                    :home_second_half_points, :away_second_half_points, :home_overtime_points, :away_overtime_points,
                    :home_money_line, :away_money_line, :playoffs, :total, :odds_event_id
                )
            """), {
                "game_date": yesterday,
                "home_team_id": home_team_id, "away_team_id": away_team_id,
                "home_team_name": db_home, "away_team_name": db_away,
                "home_points": home_points, "away_points": away_points,
                "total_points": home_points + away_points, "total_margin": home_points - away_points,
                "home_line": odds_info["home_line"], "away_line": odds_info["away_line"],
                "home_quarter_scores": json.dumps(home_qs) if home_qs is not None else None,
                "away_quarter_scores": json.dumps(away_qs) if away_qs is not None else None,
                "home_first_half_points": home_first_half, "away_first_half_points": away_first_half,
                "home_second_half_points": home_second_half, "away_second_half_points": away_second_half,
                "home_overtime_points": home_overtime, "away_overtime_points": away_overtime,
                "home_money_line": odds_info["home_money_line"], "away_money_line": odds_info["away_money_line"],
                "playoffs": enrichment["playoffs"],
                "total": odds_info["total"], "odds_event_id": game["id"],
            })
            inserted += 1

        conn.commit()
        print(f"Seeded {inserted} NBA game(s) for {yesterday}")
    except Exception as e:
        print(f"Error during seeding: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_yesterdays_nba_games()
