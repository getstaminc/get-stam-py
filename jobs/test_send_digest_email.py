"""
Test script: send today's digest email to all subscribers in BREVO_LIST_ID.
Usage:
    python jobs/test_send_digest_email.py
"""

import os
import sys
from datetime import datetime
import pytz

_jobs_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_jobs_dir)
sys.path.insert(0, _root_dir)
sys.path.insert(0, _jobs_dir)

from dotenv import load_dotenv
load_dotenv(override=True)

from send_daily_trends_digest import (
    eastern_tz,
    SPORTS_CONFIG,
    _encode_game_id,
    _build_html_email,
)
from api.external_requests.odds_api import get_odds_data
from shared_utils import convert_team_name
from api.services.email_service import EmailService


def main():
    today_et = datetime.now(eastern_tz).date()
    today_str = str(today_et)
    post_slug = f"daily-trends-{today_str}"

    print(f"[test] Collecting trends for {today_str}...")

    all_trends_flat = []
    sport_results = []

    for cfg in SPORTS_CONFIG:
        sport = cfg["sport"]
        display = cfg["display"]
        try:
            scores, _ = get_odds_data(sport, None)
            if not scores:
                print(f"[test] {display}: no scores, skipping")
                continue

            today_games_raw = _filter_today(scores, today_et)
            if not today_games_raw:
                print(f"[test] {display}: no games today, skipping")
                continue

            games_for_trends = []
            for g in today_games_raw:
                home_short = convert_team_name(g.get("home_team", ""))
                away_short = convert_team_name(g.get("away_team", ""))
                games_for_trends.append({
                    "home_team_name": home_short,
                    "away_team_name": away_short,
                    "game_id": _encode_game_id(g.get("id", "")),
                    "sport": sport,
                })

            trends_cls = cfg["trends_cls"]
            results, err = trends_cls.analyze_multiple_games_trends(
                games_for_trends, limit=20, min_trend_length=cfg["min_trend_length"]
            )
            if err:
                print(f"[test] {display} trends error: {err}")
                continue

            games_with_trends = [r for r in (results or []) if r.get("hasTrends")]
            if not games_with_trends:
                print(f"[test] {display}: no qualifying trends")
                continue

            print(f"[test] {display}: {len(games_with_trends)} games with trends")
            sport_results.append((display, sport, games_with_trends))

            for entry in games_with_trends:
                game = entry["game"]
                home = game.get("home_team_name", "")
                away = game.get("away_team_name", "")
                for trend in entry.get("homeTeamTrends", []):
                    all_trends_flat.append({"team": home, "trend": trend})
                for trend in entry.get("awayTeamTrends", []):
                    all_trends_flat.append({"team": away, "trend": trend})

        except Exception as e:
            print(f"[test] {display} error: {e}")
            continue

    if not all_trends_flat:
        print("[test] No trends found. Cannot build email.")
        sys.exit(1)

    best_entry = max(all_trends_flat, key=lambda x: x["trend"]["count"])
    highest_trend = best_entry["trend"]
    highest_team = best_entry["team"]
    team_prefix = f"{highest_team}: " if highest_team else ""
    subject = f"[TEST] GetSTAM trends of the day: {team_prefix}{highest_trend['description']}"

    print(f"[test] Top trend: {highest_team} — {highest_trend['description']}")

    subscribers, err = EmailService.get_all_subscribers()
    if err:
        print(f"[test] Failed to get subscribers: {err}")
        sys.exit(1)
    if not subscribers:
        print("[test] No subscribers found.")
        sys.exit(1)

    print(f"[test] Sending to {len(subscribers)} subscribers...")
    sent, errors = 0, 0
    for email in subscribers:
        html = _build_html_email(today_str, highest_trend, highest_team, sport_results, post_slug, email)
        ok, err = EmailService.send_digest_to_one(email, subject, html)
        if ok:
            sent += 1
        else:
            print(f"[test] Error for {email}: {err}")
            errors += 1

    print(f"[test] Done. Sent: {sent}, Errors: {errors}")


def _filter_today(scores, today_et):
    eastern = pytz.timezone('US/Eastern')
    games = []
    for game in (scores or []):
        commence_time = game.get("commence_time")
        if not commence_time:
            continue
        try:
            dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
            if dt.astimezone(eastern).date() == today_et:
                games.append(game)
        except Exception:
            continue
    return games


if __name__ == "__main__":
    main()
