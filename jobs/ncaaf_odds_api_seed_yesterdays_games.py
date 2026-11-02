#!/usr/bin/env python3
"""Seed yesterday's NCAAF games from ESPN (schedule discovery + score/
enrichment fallback) and Odds API (score + lines where available).

ESPN drives discovery (groups=90 FBS + groups=81 broad -- the only
reliable division-aware source for this sport; /teams does not respect
groups the way /scoreboard does). A game is only processed if BOTH teams
resolve, via convert_team_name, to an existing row in
`teams WHERE sport='NCAAF'` -- our own 259-team roster is the scope filter,
not ESPN's division semantics (groups=81 also returns Division II/III/NAIA
noise we've never tracked).

Odds API enriches with real lines where it has the game (effectively all
FBS, occasional marquee FCS); ESPN's own competitor.score is the fallback
final score for games Odds API doesn't track at all (most FCS games).
A second, later-scheduled job (jobs/ncaaf_sdql_fallback_fill.py) fills
remaining gaps from SDQL -- this job never calls SDQL.
"""
import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text
import shared_utils

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ESPN_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_completed_ncaaf_games_for_date(target_date_str: str, retries=3, delay=2):
    """Odds API current (non-historical) scores for the last 3 days,
    filtered to games whose Eastern-converted commence date matches
    target_date_str. Returns the raw list of Odds API game dicts."""
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/scores/"
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
            print(f"Error fetching Odds API scores (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


def get_historical_odds_for_date(date_str: str, retries=3, delay=2):
    """Historical h2h/spreads/totals odds for a date. No bookmakers filter --
    parse_odds_data picks per-market."""
    url = "https://api.the-odds-api.com/v4/historical/sports/americanfootball_ncaaf/odds"
    params = {
        "apiKey": ODDS_API_KEY, "regions": "us",
        "markets": "h2h,spreads,totals", "oddsFormat": "american",
        "date": f"{date_str}T00:00:00Z",
    }
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Odds API odds (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


def get_espn_games_for_date(date_str: str, retries=3, delay=2):
    """ESPN scoreboard for date_str, groups=90 (FBS) + groups=81 (broad --
    includes real FCS plus Division II/III/NAIA noise filtered out later
    by the caller via the teams-roster check). Returns deduped raw event
    dicts (STATUS_FINAL only)."""
    date_compact = date_str.replace("-", "")
    all_events = []
    seen_ids = set()
    for group in (90, 81):
        for i in range(retries):
            try:
                resp = requests.get(
                    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
                    params={"dates": date_compact, "limit": 400, "groups": group},
                    headers=ESPN_HEADERS, timeout=30,
                )
                resp.raise_for_status()
                events = resp.json().get("events", [])
                break
            except requests.exceptions.RequestException as e:
                print(f"  ESPN scoreboard fetch failed (groups={group}, attempt {i+1}/{retries}): {e}")
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    events = []
        for e in events:
            if e.get("status", {}).get("type", {}).get("name") != "STATUS_FINAL":
                continue
            eid = e.get("id")
            if eid in seen_ids:
                continue
            seen_ids.add(eid)
            all_events.append(e)
    return all_events


def _market_from_preferred_bookmaker(bookmakers, market_key, preferred="draftkings"):
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
    sourced, DraftKings-preferred with fallback."""
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


def seed_yesterdays_ncaaf_games():
    print("Starting NCAAF game seeding (ESPN discovery + Odds API enrichment)...")
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

        espn_events = get_espn_games_for_date(yesterday)
        if not espn_events:
            print(f"No completed NCAAF games found on ESPN for {yesterday}")
            return

        odds_games = get_completed_ncaaf_games_for_date(yesterday)
        odds_lookup_by_teams = {}
        for g in odds_games:
            db_h = shared_utils.convert_team_name(g["home_team"])
            db_a = shared_utils.convert_team_name(g["away_team"])
            odds_lookup_by_teams[(db_h, db_a)] = g

        odds_data = get_historical_odds_for_date(yesterday)
        odds_info_by_event_id = {g["id"]: g for g in odds_data}

        teams_dict = {
            row["team_name"]: row["team_id"]
            for row in conn.execute(text("SELECT team_id, team_name FROM teams WHERE sport = 'NCAAF'")).mappings()
        }

        inserted = 0
        for event in espn_events:
            comp = event["competitions"][0]
            home_c = next((c for c in comp["competitors"] if c.get("homeAway") == "home"), {})
            away_c = next((c for c in comp["competitors"] if c.get("homeAway") == "away"), {})
            espn_home_name = home_c.get("team", {}).get("displayName", "")
            espn_away_name = away_c.get("team", {}).get("displayName", "")

            db_home = shared_utils.convert_team_name(espn_home_name)
            db_away = shared_utils.convert_team_name(espn_away_name)
            home_team_id = teams_dict.get(db_home)
            away_team_id = teams_dict.get(db_away)
            if home_team_id is None or away_team_id is None:
                continue  # out of our tracked scope (Division II/III/NAIA leakage) -- silently skip

            odds_game = odds_lookup_by_teams.get((db_home, db_away))
            odds_event_id = odds_game["id"] if odds_game else None

            if odds_game:
                home_points = away_points = None
                for score in odds_game["scores"]:
                    name = shared_utils.convert_team_name(score["name"])
                    if name == db_home:
                        home_points = int(score["score"])
                    elif name == db_away:
                        away_points = int(score["score"])
            else:
                home_points = int(home_c.get("score", 0)) if home_c.get("score") is not None else None
                away_points = int(away_c.get("score", 0)) if away_c.get("score") is not None else None

            if home_points is None or away_points is None:
                print(f"Skipping {espn_away_name} @ {espn_home_name} - no score from either source")
                continue

            existing = conn.execute(text("""
                SELECT 1 FROM ncaaf_games
                WHERE odds_event_id = :odds_event_id
                   OR (game_date = :game_date AND home_team_id = :home_team_id AND away_team_id = :away_team_id)
            """), {
                "odds_event_id": odds_event_id, "game_date": yesterday,
                "home_team_id": home_team_id, "away_team_id": away_team_id,
            }).fetchone()
            if existing:
                print(f"Already seeded: {db_away} @ {db_home} on {yesterday}")
                continue

            odds_info = parse_odds_data(odds_info_by_event_id.get(odds_event_id, {})) if odds_event_id else {
                "home_money_line": None, "away_money_line": None,
                "home_line": None, "away_line": None, "total": None,
            }

            season_type = event.get("season", {}).get("type")
            playoffs = (season_type == 3) if season_type is not None else None
            neutral_site = comp.get("neutralSite")
            # ncaaf_games.game_site is NOT NULL (confirmed via information_schema) -- both
            # False and an unknown/missing neutralSite must map to 'home', never None.
            # Writing SQL NULL here would crash the whole run (all games share one
            # transaction) on any event missing this field -- this exact bug was already
            # found and fixed once during the NFL migration; do not reintroduce it.
            game_site = "neutral" if neutral_site else "home"

            home_qs = [int(ls.get("displayValue", 0)) for ls in home_c.get("linescores", [])] or None
            away_qs = [int(ls.get("displayValue", 0)) for ls in away_c.get("linescores", [])] or None
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

            commence_time = event.get("date")
            start_time = None
            if commence_time:
                try:
                    commence_dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                    start_time = shared_utils.convert_to_eastern(commence_dt).time()
                except Exception:
                    start_time = None

            print(f"Inserting: {db_away} {away_points} @ {db_home} {home_points} on {yesterday}")

            conn.execute(text("""
                INSERT INTO ncaaf_games (
                    game_date, game_site, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_points, away_points, total_points, total_margin, home_line, away_line,
                    home_quarter_scores, away_quarter_scores, home_first_half_points, away_first_half_points,
                    home_second_half_points, away_second_half_points, home_overtime_points, away_overtime_points,
                    home_money_line, away_money_line, playoffs, start_time, total, odds_event_id
                ) VALUES (
                    :game_date, :game_site, :home_team_id, :away_team_id, :home_team_name, :away_team_name,
                    :home_points, :away_points, :total_points, :total_margin, :home_line, :away_line,
                    :home_quarter_scores, :away_quarter_scores, :home_first_half_points, :away_first_half_points,
                    :home_second_half_points, :away_second_half_points, :home_overtime_points, :away_overtime_points,
                    :home_money_line, :away_money_line, :playoffs, :start_time, :total, :odds_event_id
                )
            """), {
                "game_date": yesterday, "game_site": game_site,
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
                "playoffs": playoffs, "start_time": start_time,
                "total": odds_info["total"], "odds_event_id": odds_event_id,
            })
            inserted += 1

        conn.commit()
        print(f"Seeded {inserted} NCAAF game(s) for {yesterday}")
    except Exception as e:
        print(f"Error during seeding: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_yesterdays_ncaaf_games()
