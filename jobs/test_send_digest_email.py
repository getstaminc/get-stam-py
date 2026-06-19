"""
Test script: build today's digest (with ML-aware streak context) and send to BREVO_LIST_ID.
No blog post is created. Prints full markdown to stdout so you can inspect streak context.

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
    SITE_BASE_URL,
    _encode_game_id,
    _extract_ml,
    _get_todays_games_from_scores,
    _build_markdown,
    _build_html_email,
)
from api.external_requests.odds_api import get_odds_data
from shared_utils import convert_team_name
from api.services.historical.mlb_trends_service import MLBTrendsService
from api.services.historical.nhl_trends_service import NHLTrendsService
from api.services.historical.nba_trends_service import NBATrendsService
from api.services.email_service import EmailService


def main():
    today_et = datetime.now(eastern_tz).date()
    today_str = str(today_et)
    post_slug = f"daily-trends-{today_str}"

    print(f"[test] Building digest for {today_str} (no blog post will be created)")
    print()

    all_trends_flat = []
    sport_results = []

    for cfg in SPORTS_CONFIG:
        sport = cfg["sport"]
        sport_key = cfg["sport_key"]
        display = cfg["display"]

        try:
            scores, odds_data = get_odds_data(sport, None)
            if not scores:
                print(f"[test] {display}: no scores, skipping")
                continue

            today_games_raw = _get_todays_games_from_scores(scores)
            if not today_games_raw:
                print(f"[test] {display}: no games today, skipping")
                continue

            print(f"[test] {display}: {len(today_games_raw)} games today")

            odds_by_id = {g['id']: g for g in (odds_data or []) if g.get('id')}

            games_for_trends = []
            for g in today_games_raw:
                home_full = g.get("home_team", "")
                away_full = g.get("away_team", "")
                home_short = convert_team_name(home_full)
                away_short = convert_team_name(away_full)
                odds_game = odds_by_id.get(g.get("id", ""))
                home_ml, away_ml = _extract_ml(odds_game, home_full) if odds_game else (None, None)
                games_for_trends.append({
                    "home_team_name": home_short,
                    "away_team_name": away_short,
                    "game_id": _encode_game_id(g.get("id", "")),
                    "sport": sport,
                    "home_ml": home_ml,
                    "away_ml": away_ml,
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
                    all_trends_flat.append({"label": home, "trend": trend, "sport": display})
                for trend in entry.get("awayTeamTrends", []):
                    all_trends_flat.append({"label": away, "trend": trend, "sport": display})
                for trend in entry.get("homeTeamHomeTrends", []):
                    all_trends_flat.append({"label": f"{home} (at home)", "trend": trend, "sport": display})
                for trend in entry.get("awayTeamAwayTrends", []):
                    all_trends_flat.append({"label": f"{away} (away)", "trend": trend, "sport": display})
                for trend in entry.get("headToHeadTrends", []):
                    all_trends_flat.append({"label": f"{home} vs {away}", "trend": trend, "sport": display})
                for trend in entry.get("homeAtHomeH2HTrends", []):
                    all_trends_flat.append({"label": f"{home} vs {away} (home)", "trend": trend, "sport": display})

        except Exception as e:
            import traceback
            print(f"[test] {display} error: {e}")
            traceback.print_exc()
            continue

    if not all_trends_flat:
        print("[test] No trends found. Cannot build email.")
        sys.exit(1)

    best_entry = max(all_trends_flat, key=lambda x: x["trend"]["count"])
    highest_trend = best_entry["trend"]
    highest_team = best_entry["label"]
    team_prefix = f"{highest_team}: " if highest_team else ""
    subject = f"[TEST] GetSTAM trends: {team_prefix}{highest_trend['description']}"

    print(f"\n[test] Top trend: {highest_team} — {highest_trend['description']}")

    # Build and print markdown so you can inspect streak context strings
    content_md = _build_markdown(today_str, sport_results)
    print("\n" + "=" * 60)
    print("MARKDOWN CONTENT (inspect streak context below):")
    print("=" * 60)
    print(content_md)
    print("=" * 60 + "\n")

    # Send to subscribers in BREVO_LIST_ID (currently list 4 = just you)
    subscribers, err = EmailService.get_all_subscribers()
    if err:
        print(f"[test] Failed to get subscribers: {err}")
        sys.exit(1)
    if not subscribers:
        print("[test] No subscribers found.")
        sys.exit(1)

    print(f"[test] Sending to {len(subscribers)} subscriber(s): {subscribers}")
    sent, errors = 0, 0
    for email in subscribers:
        html = _build_html_email(today_str, highest_trend, highest_team, sport_results, post_slug, email)
        ok, send_err = EmailService.send_digest_to_one(email, subject, html)
        if ok:
            sent += 1
            print(f"[test] Sent to {email}")
        else:
            print(f"[test] Error for {email}: {send_err}")
            errors += 1

    print(f"\n[test] Done. Sent: {sent}, Errors: {errors}")


if __name__ == "__main__":
    main()
