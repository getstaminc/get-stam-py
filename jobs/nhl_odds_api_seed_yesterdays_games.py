#!/usr/bin/env python3
"""Seed yesterday's NHL games from the Odds API, enriched with ESPN data for
fields the Odds API doesn't provide (period goals, starting goalies,
powerplay goals, overtime/shootout, playoffs). Replaces the SDQL-based
jobs/nhl_seed_yesterdays_games.py.

game_site is hardcoded 'home' — home_team_id/away_team_id already disambiguate
home vs. away, so SDQL's 'neutral' distinction isn't carried forward.
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
from jobs.nhl_espn_enrichment import (
    extract_period_goals,
    detect_overtime_shootout,
    is_playoff_game,
    count_powerplay_goals,
    find_starting_goalie,
)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")


def get_completed_nhl_games_for_date(target_date_str: str, retries=3, delay=2):
    """Odds API current (non-historical) scores for the last 3 days, filtered
    to games whose Eastern-converted commence date matches target_date_str."""
    url = "https://api.the-odds-api.com/v4/sports/icehockey_nhl/scores/"
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
    """Historical h2h/totals odds for a date (yesterday's market has closed by
    the time this job runs, so the current-odds endpoint won't have it)."""
    url = "https://api.the-odds-api.com/v4/historical/sports/icehockey_nhl/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "bookmakers": "draftkings",
        "markets": "h2h,totals",
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


def parse_odds_data(odds_game: dict) -> dict:
    """Extract moneyline + total from a draftkings bookmaker entry."""
    odds_info = {"home_money_line": None, "away_money_line": None, "total": None}
    draftkings = next((bm for bm in odds_game.get("bookmakers", []) if bm["key"] == "draftkings"), None)
    if not draftkings:
        return odds_info
    home_team = odds_game["home_team"]
    away_team = odds_game["away_team"]
    for market in draftkings.get("markets", []):
        if market["key"] == "h2h":
            for outcome in market["outcomes"]:
                if outcome["name"] == home_team:
                    odds_info["home_money_line"] = outcome["price"]
                elif outcome["name"] == away_team:
                    odds_info["away_money_line"] = outcome["price"]
        elif market["key"] == "totals":
            points = market["outcomes"][0].get("point") if market.get("outcomes") else None
            odds_info["total"] = points
    return odds_info


def get_espn_enrichment(target_date_str: str, home_team: str, away_team: str) -> dict:
    """Fetch ESPN's NHL summary for the game matching home_team/away_team on
    target_date_str and return the fields the Odds API can't provide. Returns
    an all-None dict if the ESPN game can't be matched."""
    empty = {
        "home_period_goals": None, "away_period_goals": None,
        "home_starting_goalie": None, "away_starting_goalie": None,
        "home_powerplay_goals": None, "away_powerplay_goals": None,
        "overtime": None, "shoot_out": None, "playoffs": None,
    }
    date_compact = target_date_str.replace("-", "")
    try:
        resp = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
            params={"dates": date_compact}, timeout=30,
        )
        resp.raise_for_status()
        events = resp.json().get("events", [])
    except requests.exceptions.RequestException as e:
        print(f"  ESPN scoreboard fetch failed: {e}")
        return empty

    espn_game_id = None
    for event in events:
        comp = event.get("competitions", [{}])[0]
        competitors = {c.get("homeAway"): c.get("team", {}).get("displayName") for c in comp.get("competitors", [])}
        espn_home = shared_utils.convert_team_name(competitors.get("home", ""))
        espn_away = shared_utils.convert_team_name(competitors.get("away", ""))
        if espn_home == home_team and espn_away == away_team:
            espn_game_id = event.get("id")
            break

    if not espn_game_id:
        print(f"  Could not match ESPN event for {away_team} @ {home_team} on {target_date_str}")
        return empty

    try:
        resp = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary",
            params={"event": espn_game_id, "enable": "boxscore,plays"}, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"  ESPN summary fetch failed for event {espn_game_id}: {e}")
        return empty

    header = data.get("header", {})
    comp = header.get("competitions", [{}])[0]
    season_type = header.get("season", {}).get("type")
    status_detail = comp.get("status", {}).get("type", {}).get("detail", "")
    plays = data.get("plays", [])

    espn_home_id = espn_away_id = None
    home_linescore = away_linescore = {}
    for competitor in comp.get("competitors", []):
        if competitor.get("homeAway") == "home":
            espn_home_id = str(competitor.get("team", {}).get("id", ""))
            home_linescore = competitor
        elif competitor.get("homeAway") == "away":
            espn_away_id = str(competitor.get("team", {}).get("id", ""))
            away_linescore = competitor

    overtime, shoot_out = detect_overtime_shootout(status_detail)

    return {
        "home_period_goals": extract_period_goals(home_linescore),
        "away_period_goals": extract_period_goals(away_linescore),
        "home_starting_goalie": find_starting_goalie(plays, espn_away_id) if espn_away_id else None,
        "away_starting_goalie": find_starting_goalie(plays, espn_home_id) if espn_home_id else None,
        "home_powerplay_goals": count_powerplay_goals(plays, espn_home_id) if espn_home_id else None,
        "away_powerplay_goals": count_powerplay_goals(plays, espn_away_id) if espn_away_id else None,
        "overtime": overtime,
        "shoot_out": shoot_out,
        "playoffs": is_playoff_game(season_type) if season_type is not None else None,
    }


def seed_yesterdays_nhl_games():
    print("Starting NHL game seeding (Odds API + ESPN)...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        games = get_completed_nhl_games_for_date(yesterday)
        if not games:
            print(f"No completed NHL games found for {yesterday}")
            return

        odds_data = get_historical_odds_for_date(yesterday)
        odds_lookup = {}
        for game in odds_data:
            odds_lookup[f"{game['home_team']}_{game['away_team']}"] = game

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NHL'")).mappings()
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

            home_goals = away_goals = None
            for score in game["scores"]:
                db_name = shared_utils.convert_team_name(score["name"])
                if db_name == db_home:
                    home_goals = int(score["score"])
                elif db_name == db_away:
                    away_goals = int(score["score"])
            if home_goals is None or away_goals is None:
                print(f"Skipping {game['away_team']} @ {game['home_team']} - missing score")
                continue

            existing = conn.execute(text("""
                SELECT 1 FROM nhl_games
                WHERE odds_event_id = :odds_event_id
                   OR (game_date = :game_date AND home_team_name = :home AND away_team_name = :away)
            """), {
                "odds_event_id": game["id"], "game_date": yesterday,
                "home": db_home, "away": db_away,
            }).fetchone()
            if existing:
                print(f"Already seeded: {db_away} @ {db_home} on {yesterday}")
                continue

            odds_info = parse_odds_data(odds_lookup.get(f"{game['home_team']}_{game['away_team']}", {}))
            enrichment = get_espn_enrichment(yesterday, db_home, db_away)

            conn.execute(text("""
                INSERT INTO nhl_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_goals, away_goals, home_money_line, away_money_line,
                    home_period_goals, away_period_goals, home_starting_goalie, away_starting_goalie,
                    home_powerplay_goals, away_powerplay_goals, total, overtime, shoot_out, playoffs,
                    odds_event_id
                ) VALUES (
                    :game_date, 'home', :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_goals, :away_goals, :home_money_line, :away_money_line,
                    :home_period_goals, :away_period_goals, :home_starting_goalie, :away_starting_goalie,
                    :home_powerplay_goals, :away_powerplay_goals, :total, :overtime, :shoot_out, :playoffs,
                    :odds_event_id
                )
            """), {
                "game_date": yesterday, "home_team_id": home_team_id, "away_team_id": away_team_id,
                "home_team_name": db_home, "away_team_name": db_away,
                "home_goals": home_goals, "away_goals": away_goals,
                "home_money_line": odds_info["home_money_line"], "away_money_line": odds_info["away_money_line"],
                "home_period_goals": enrichment["home_period_goals"], "away_period_goals": enrichment["away_period_goals"],
                "home_starting_goalie": enrichment["home_starting_goalie"], "away_starting_goalie": enrichment["away_starting_goalie"],
                "home_powerplay_goals": enrichment["home_powerplay_goals"], "away_powerplay_goals": enrichment["away_powerplay_goals"],
                "total": odds_info["total"], "overtime": enrichment["overtime"],
                "shoot_out": enrichment["shoot_out"], "playoffs": enrichment["playoffs"],
                "odds_event_id": game["id"],
            })
            inserted += 1
            print(f"Inserted: {db_away} {away_goals} @ {db_home} {home_goals}")

        conn.commit()
        print(f"Seeded {inserted} NHL games for {yesterday}")
    except Exception as e:
        print(f"Error during seeding: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_yesterdays_nhl_games()
