"""
Daily Trends Email Digest
Runs every morning via cron:
  0 8 * * *  cd /path/to/get-stam-py && ./venv/bin/python jobs/send_daily_trends_digest.py >> logs/daily_digest.log 2>&1
"""

import os
import sys
import base64
import binascii
from datetime import datetime
import pytz

# Add project root to path so we can import api.* modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(override=True)

from api.external_requests.odds_api import get_odds_data
from shared_utils import convert_team_name
from api.services.historical.mlb_trends_service import MLBTrendsService
from api.services.historical.nhl_trends_service import NHLTrendsService
from api.services.historical.nba_trends_service import NBATrendsService
from api.services.blog_service import BlogService
from api.services.email_service import EmailService

eastern_tz = pytz.timezone('US/Eastern')

SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://www.getstam.com")

SPORTS_CONFIG = [
    {"sport": "mlb", "sport_key": "baseball_mlb", "display": "MLB", "trends_cls": MLBTrendsService, "min_trend_length": 5},
    {"sport": "nhl", "sport_key": "icehockey_nhl", "display": "NHL", "trends_cls": NHLTrendsService, "min_trend_length": 3},
    {"sport": "nba", "sport_key": "basketball_nba", "display": "NBA", "trends_cls": NBATrendsService, "min_trend_length": 3},
]


def _encode_game_id(hex_id):
    """Convert Odds API hex game ID to URL-safe base64, matching encodeGameId() in the frontend."""
    try:
        raw_bytes = binascii.unhexlify(hex_id)
        return base64.urlsafe_b64encode(raw_bytes).rstrip(b'=').decode('ascii')
    except Exception:
        return hex_id


def _get_todays_games_from_scores(scores):
    """Filter Odds API scores list to games starting today ET."""
    today_et = datetime.now(eastern_tz).date()
    games = []
    for game in (scores or []):
        commence_time = game.get("commence_time")
        if not commence_time:
            continue
        try:
            dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
            if dt.astimezone(eastern_tz).date() == today_et:
                games.append(game)
        except Exception:
            continue
    return games


def _check_existing_post(slug):
    """Return post dict if a post with this slug exists (any status), else None."""
    try:
        import psycopg2
        import psycopg2.extras
        database_url = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
        with psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, status FROM blog_posts WHERE slug = %s", (slug,))
                row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[check_existing_post] error: {e}")
        return None


def _build_markdown(today_str, sport_results):
    """Build Markdown content for the blog post."""
    lines = [
        f"# Daily Trends Digest — {today_str}",
        "",
        "Today's strongest trends across MLB, NHL, and NBA.",
        "",
    ]
    for sport_display, game_trends_list in sport_results:
        lines.append(f"## {sport_display}")
        lines.append("")
        for entry in game_trends_list:
            game = entry["game"]
            home = game.get("home_team_name", "")
            away = game.get("away_team_name", "")
            trend_keys = [
                ("homeTeamTrends", home),
                ("awayTeamTrends", away),
                ("homeTeamHomeTrends", f"{home} (at home)"),
                ("awayTeamAwayTrends", f"{away} (away)"),
                ("headToHeadTrends", "H2H"),
                ("homeAtHomeH2HTrends", f"{home} (home H2H)"),
            ]
            # Skip games that have no renderable trends
            if not any(entry.get(key) for key, _ in trend_keys):
                continue
            lines.append(f"### {away} @ {home}")
            lines.append("")
            game_id = game.get("game_id", "")
            sport_key = game.get("sport", "")
            if game_id and sport_key:
                lines.append(f"[View Game →](/game-details/{sport_key}?game_id={game_id})")
                lines.append("")
            for trend_key, label in trend_keys:
                trends = entry.get(trend_key, [])
                if trends:
                    lines.append(f"**{label}**:")
                    for t in trends:
                        lines.append(f"- {t['description']}")
                    lines.append("")
        lines.append("")
    return "\n".join(lines)


def _build_html_email(today_str, highest_trend, highest_team, sport_results, post_slug):
    """Build inline-styled HTML for the email digest."""
    blog_url = f"{SITE_BASE_URL}/blog/{post_slug}"

    sports_with_trends = [display for display, entries in sport_results if entries]
    sports_line = ", ".join(sports_with_trends) if sports_with_trends else "MLB, NHL, NBA"

    hero_text = f"<strong>{highest_team}</strong>: {highest_trend['description']}" if highest_team else highest_trend['description']

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
    <tr>
      <td align="center" style="padding: 24px 16px;">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #1976d2, #42a5f5); padding: 40px 24px; text-align: center;">
              <p style="margin: 0 0 8px; font-family: Arial, sans-serif; color: rgba(255,255,255,0.85); font-size: 13px; letter-spacing: 1px; text-transform: uppercase;">GetSTAM Daily Trends — {today_str}</p>
              <h1 style="margin: 0 0 24px; font-family: Arial, sans-serif; color: #ffffff; font-size: 28px; font-weight: 700; line-height: 1.3;">
                Today's Top Trend
              </h1>
              <p style="margin: 0; font-family: Arial, sans-serif; color: #ffffff; font-size: 20px; font-weight: 600; background: rgba(255,255,255,0.15); padding: 14px 24px; border-radius: 8px; display: inline-block;">
                🔥 {hero_text}
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 32px 24px; text-align: center;">
              <p style="margin: 0 0 24px; font-family: Arial, sans-serif; font-size: 16px; color: #555; line-height: 1.6;">
                Today's trends are in for <strong>{sports_line}</strong>.<br>
                Click below to see all the streaks and make your picks.
              </p>
              <a href="{blog_url}"
                 style="display: inline-block; background: #1976d2; color: #ffffff; font-family: Arial, sans-serif; font-size: 16px; font-weight: 700; text-decoration: none; padding: 14px 40px; border-radius: 6px;">
                View Today's Trends →
              </a>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 16px 24px; text-align: center; background: #f9f9f9; border-top: 1px solid #eee;">
              <p style="margin: 0; font-family: Arial, sans-serif; font-size: 12px; color: #999;">
                You're receiving this because you subscribed to GetSTAM daily trends.<br>
                All odds and betting information are for entertainment purposes only.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def run():
    today_et = datetime.now(eastern_tz).date()
    today_str = str(today_et)
    post_slug = f"daily-trends-{today_str}"

    print(f"[digest] Starting daily trends digest for {today_str}")

    # --- Step 1: Collect trends for each sport ---
    all_trends_flat = []   # list of {team, trend, sport_display}
    sport_results = []     # list of (sport_display, game_trends_list)

    for cfg in SPORTS_CONFIG:
        sport = cfg["sport"]
        sport_key = cfg["sport_key"]
        display = cfg["display"]

        try:
            scores, _ = get_odds_data(sport, None)
            if not scores:
                print(f"[digest] {display}: no scores data, skipping")
                continue

            today_games_raw = _get_todays_games_from_scores(scores)
            if not today_games_raw:
                print(f"[digest] {display}: no games today, skipping")
                continue

            print(f"[digest] {display}: {len(today_games_raw)} games today")

            # Convert full team names → short DB names for trends service
            games_for_trends = []
            for g in today_games_raw:
                home_full = g.get("home_team", "")
                away_full = g.get("away_team", "")
                home_short = convert_team_name(home_full)
                away_short = convert_team_name(away_full)
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
                print(f"[digest] {display} trends error: {err}")
                continue

            # Filter to games with trends
            games_with_trends = [r for r in (results or []) if r.get("hasTrends")]
            if not games_with_trends:
                print(f"[digest] {display}: no qualifying trends found")
                continue

            print(f"[digest] {display}: {len(games_with_trends)} games with trends")
            sport_results.append((display, games_with_trends))

            # Flatten all trends for highest-trend selection
            for entry in games_with_trends:
                game = entry["game"]
                home = game.get("home_team_name", "")
                away = game.get("away_team_name", "")
                for trend in entry.get("homeTeamTrends", []):
                    all_trends_flat.append({"team": home, "trend": trend, "sport": display})
                for trend in entry.get("awayTeamTrends", []):
                    all_trends_flat.append({"team": away, "trend": trend, "sport": display})
                for trend in entry.get("homeTeamHomeTrends", []):
                    all_trends_flat.append({"team": home, "trend": trend, "sport": display})
                for trend in entry.get("awayTeamAwayTrends", []):
                    all_trends_flat.append({"team": away, "trend": trend, "sport": display})
                for trend in entry.get("headToHeadTrends", []):
                    all_trends_flat.append({"team": "", "trend": trend, "sport": display})
                for trend in entry.get("homeAtHomeH2HTrends", []):
                    all_trends_flat.append({"team": "", "trend": trend, "sport": display})

        except Exception as e:
            print(f"[digest] {display} error (non-fatal): {e}")
            continue

    if not all_trends_flat:
        print("[digest] No trends found across any sport. Exiting without creating post or sending email.")
        return

    # --- Step 2: Find highest trend ---
    best_entry = max(all_trends_flat, key=lambda x: x["trend"]["count"])
    highest_trend = best_entry["trend"]
    highest_team = best_entry["team"]
    team_prefix = f"{highest_team}: " if highest_team else ""
    subject = f"GetSTAM trends of the day: {team_prefix}{highest_trend['description']}"
    print(f"[digest] Highest trend: {highest_team} — {highest_trend['description']} (count={highest_trend['count']})")

    # --- Step 3: Create + publish blog post ---
    existing = _check_existing_post(post_slug)
    if existing:
        post_id = existing["id"]
        print(f"[digest] Post already exists (id={post_id}, status={existing['status']}), skipping creation")
    else:
        content_md = _build_markdown(today_str, sport_results)
        excerpt = f"Today's strongest trends: {highest_team} {highest_trend['description'].lower()} and more across MLB, NHL, and NBA."
        post_data = {
            "title": f"Daily Trends Digest — {today_str}",
            "slug": post_slug,
            "meta_description": excerpt[:200],
            "excerpt": excerpt,
            "content": content_md,
            "tags": ["daily trends", "mlb", "nhl", "nba", "betting trends"],
            "reading_time_minutes": 3,
            "status": "draft",
            "category": "daily_trends",
        }
        post_id, err = BlogService.create_post(post_data)
        if err:
            print(f"[digest] Failed to create blog post: {err}")
            return
        print(f"[digest] Created blog post id={post_id}")

        ok, err = BlogService.publish_post(post_id)
        if err:
            print(f"[digest] Failed to publish post: {err}")
        else:
            print(f"[digest] Published post id={post_id}")

    # --- Step 4: Build email and send ---
    html = _build_html_email(today_str, highest_trend, highest_team, sport_results, post_slug)

    subscribers, err = EmailService.get_all_subscribers()
    if err:
        print(f"[digest] Failed to get subscribers: {err}")
        return
    if not subscribers:
        print("[digest] No subscribers found. Skipping email send.")
        return

    print(f"[digest] Sending to {len(subscribers)} subscribers in batches of 50")
    batch_size = 50
    sent_count = 0
    error_count = 0
    for i in range(0, len(subscribers), batch_size):
        batch = subscribers[i:i + batch_size]
        ok, err = EmailService.send_digest(batch, subject, html)
        if ok:
            sent_count += len(batch)
        else:
            print(f"[digest] Batch {i//batch_size + 1} send error: {err}")
            error_count += len(batch)

    print(f"[digest] Done. Sent: {sent_count}, Errors: {error_count}")


if __name__ == "__main__":
    run()
