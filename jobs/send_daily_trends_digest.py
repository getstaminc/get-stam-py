"""
Daily Trends Email Digest
Runs every morning via cron:
  0 8 * * *  cd /path/to/get-stam-py && ./venv/bin/python jobs/send_daily_trends_digest.py >> logs/daily_digest.log 2>&1
"""

import os
import sys
import base64
import binascii
import json
import urllib.parse
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
from api.services.historical.mlb_player_trends_service import MLBPlayerTrendsService
from api.services.blog_service import BlogService
from api.services.email_service import EmailService
from api.services.historical.trend_context_service import get_streak_context

eastern_tz = pytz.timezone('US/Eastern')

SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://www.getstam.com")

SPORTS_CONFIG = [
    {"sport": "mlb", "sport_key": "baseball_mlb", "display": "MLB", "trends_cls": MLBTrendsService, "min_trend_length": 5},
    {"sport": "nhl", "sport_key": "icehockey_nhl", "display": "NHL", "trends_cls": NHLTrendsService, "min_trend_length": 3},
    {"sport": "nba", "sport_key": "basketball_nba", "display": "NBA", "trends_cls": NBATrendsService, "min_trend_length": 3},
]


def _extract_ml(odds_game: dict, home_full: str) -> tuple:
    """
    Pull (home_ml, away_ml) from an Odds API game dict.
    Returns (None, None) if h2h market isn't available.
    """
    for bookmaker in odds_game.get('bookmakers', []):
        for market in bookmaker.get('markets', []):
            if market.get('key') == 'h2h':
                home_ml = away_ml = None
                for outcome in market.get('outcomes', []):
                    if outcome.get('name') == home_full:
                        home_ml = outcome.get('price')
                    else:
                        away_ml = outcome.get('price')
                return home_ml, away_ml
    return None, None


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


def _enrich_desc(t: dict, team: str, venue: str) -> str:
    """Build a descriptive trend sentence with team name and optional venue context."""
    tt, n = t['type'], t['count']
    venue_suffix = f" {venue}" if venue else ""
    if tt == 'win_streak':
        return f"{team} won {n} straight{venue_suffix}"
    if tt == 'loss_streak':
        return f"{team} lost {n} straight{venue_suffix}"
    if tt in ('over_streak', 'under_streak'):
        direction = 'OVER' if tt == 'over_streak' else 'UNDER'
        if venue:
            return f"Total went {direction} {n} straight {venue} ({team})"
        return f"Total went {direction} {n} straight ({team})"
    if tt == 'cover_streak':
        return f"{team} covered {n} straight spreads{venue_suffix}"
    if tt == 'no_cover_streak':
        return f"{team} failed to cover {n} straight spreads{venue_suffix}"
    return t['description']


def _build_markdown(today_str, sport_results, player_streaks_by_team=None):
    """Build Markdown content for the blog post."""
    lines = [
        f"# Daily Trends Digest — {today_str}",
        "",
        "Today's strongest betting trends.",
        "",
    ]
    for sport_display, sport_key_lower, game_trends_list in sport_results:
        lines.append(f"## {sport_display}")
        lines.append("")
        for entry in game_trends_list:
            game = entry["game"]
            home = game.get("home_team_name", "")
            away = game.get("away_team_name", "")
            # (trend_key, label, h2h_mode, focal_team, focal_ml_key, venue)
            trend_keys = [
                ("homeTeamTrends",      home,                  None,         home, "home_ml",  ""),
                ("awayTeamTrends",      away,                  None,         away, "away_ml",  ""),
                ("homeTeamHomeTrends",  f"{home} (at home)",   None,         home, "home_ml",  "at home"),
                ("awayTeamAwayTrends",  f"{away} (away)",      None,         away, "away_ml",  "away"),
                ("headToHeadTrends",    "H2H",                 "gen_h2h",    None, None,       None),
                ("homeAtHomeH2HTrends", f"{home} (home H2H)",  "home_h2h",   home, "home_ml",  None),
            ]
            # Skip games that have no renderable trends
            if not any(entry.get(key) for key, _, _, _, _, _ in trend_keys):
                continue
            lines.append(f"### {away} @ {home}")
            lines.append("")
            game_id = game.get("game_id", "")
            sport_route_key = game.get("sport", "")
            if game_id and sport_route_key:
                lines.append(f"[View Game →](/game-details/{sport_route_key}?game_id={game_id})")
                lines.append("")
            for trend_key, label, h2h_mode, focal_team, focal_ml_key, venue in trend_keys:
                trends = entry.get(trend_key, [])
                if trends:
                    lines.append(f"**{label}**:")
                    for t in trends:
                        # H2H descriptions are already built with team/venue by base_service
                        # Non-H2H descriptions need enriching since services emit generic text
                        desc = t['description'] if h2h_mode else _enrich_desc(t, focal_team, venue)
                        if h2h_mode:
                            if h2h_mode == "home_h2h":
                                today_ml_ctx = game.get("home_ml")
                                today_team_ctx = home
                            else:
                                # gen_h2h: identify today's favorite to name them
                                hml = game.get("home_ml")
                                aml = game.get("away_ml")
                                if hml is not None and hml < 0:
                                    today_ml_ctx, today_team_ctx = hml, home
                                elif aml is not None and aml < 0:
                                    today_ml_ctx, today_team_ctx = aml, away
                                else:
                                    today_ml_ctx, today_team_ctx = hml, home
                            context = get_streak_context(
                                sport_key_lower, t['type'], t['count'], h2h_mode,
                                today_ml=today_ml_ctx,
                                today_team=today_team_ctx,
                            )
                        else:
                            # Team streak context — look across all historical games
                            today_ml_ctx = game.get(focal_ml_key) if focal_ml_key else None
                            context = get_streak_context(
                                sport_key_lower, t['type'], t['count'], 'team',
                                today_ml=today_ml_ctx,
                                today_team=focal_team,
                            )
                        if context:
                            desc = f"{desc} — {context}"
                        lines.append(f"- {desc}")
                    lines.append("")

            # Per-game player streaks (MLB only), embedded as a JSON comment so the
            # frontend can render them with the same PlayerStreaksStrip used on the
            # game-details page (grouped by team, one shown + expandable).
            if player_streaks_by_team:
                game_streaks = []
                for team_name in (home, away):
                    team_streaks = player_streaks_by_team.get(team_name, [])
                    if team_streaks:
                        game_streaks.append({"team": team_name, "streaks": team_streaks})
                if game_streaks:
                    lines.append(f"<!--PLAYER_STREAKS:{json.dumps(game_streaks)}-->")
                    lines.append("")
        lines.append("")

    return "\n".join(lines)


def _build_html_email(today_str, highest_trend, highest_team, sport_results, post_slug, recipient_email=""):
    """Build inline-styled HTML for the email digest."""
    blog_url = f"{SITE_BASE_URL}/blog/{post_slug}?ref=email"
    encoded_email = base64.urlsafe_b64encode(recipient_email.encode()).rstrip(b"=").decode("ascii")
    unsubscribe_url = f"{SITE_BASE_URL}/api/unsubscribe?e={urllib.parse.quote(encoded_email)}"

    sports_with_trends = [display for display, _sk, entries in sport_results if entries]
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
                All odds and betting information are for entertainment purposes only.<br><br>
                <a href="{unsubscribe_url}" style="color: #999; text-decoration: underline;">Unsubscribe</a>
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
    sport_results = []     # list of (sport_display, sport_key, game_trends_list)

    for cfg in SPORTS_CONFIG:
        sport = cfg["sport"]
        sport_key = cfg["sport_key"]
        display = cfg["display"]

        try:
            scores, odds_data = get_odds_data(sport, None)
            if not scores:
                print(f"[digest] {display}: no scores data, skipping")
                continue

            today_games_raw = _get_todays_games_from_scores(scores)
            if not today_games_raw:
                print(f"[digest] {display}: no games today, skipping")
                continue

            print(f"[digest] {display}: {len(today_games_raw)} games today")

            # Build a lookup from game ID → odds game dict for ML extraction
            odds_by_id = {g['id']: g for g in (odds_data or []) if g.get('id')}

            # Convert full team names → short DB names for trends service
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
                print(f"[digest] {display} trends error: {err}")
                continue

            # Filter to games with trends
            games_with_trends = [r for r in (results or []) if r.get("hasTrends")]
            if not games_with_trends:
                print(f"[digest] {display}: no qualifying trends found")
                continue

            print(f"[digest] {display}: {len(games_with_trends)} games with trends")
            sport_results.append((display, sport, games_with_trends))

            # Flatten all trends for highest-trend selection
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
            print(f"[digest] {display} error (non-fatal): {e}")
            continue

    if not all_trends_flat:
        print("[digest] No trends found across any sport. Exiting without creating post or sending email.")
        return

    # --- Step 1b: Fetch MLB player streaks ---
    player_streaks_by_team = {}
    # Collect all MLB team names from today's games
    all_mlb_team_names = []
    for display, sport_key_lower, game_trends_list in sport_results:
        if sport_key_lower == "mlb":
            for entry in game_trends_list:
                game = entry["game"]
                # game dict has short names (DB names); we need Odds API full names
                # player_team_name in batter_props uses Odds API full names, so
                # we re-collect them from the raw scores processed earlier.
                pass  # handled below using stored full names

    # Re-collect Odds API full team names for MLB
    try:
        mlb_cfg = next((c for c in SPORTS_CONFIG if c["sport"] == "mlb"), None)
        if mlb_cfg:
            mlb_scores, _ = get_odds_data(mlb_cfg["sport"], None)
            mlb_today = _get_todays_games_from_scores(mlb_scores or [])
            all_mlb_team_names = []
            for g in mlb_today:
                all_mlb_team_names.append(g.get("home_team", ""))
                all_mlb_team_names.append(g.get("away_team", ""))
            all_mlb_team_names = [t for t in all_mlb_team_names if t]

        if all_mlb_team_names:
            raw_streaks_by_team = MLBPlayerTrendsService().get_batter_streaks(
                team_names=all_mlb_team_names, min_streak=5
            )
            # Re-key from Odds API full team names to short DB names so games
            # (which use short names) can look streaks up per-team.
            player_streaks_by_team = {
                convert_team_name(full_name): streaks
                for full_name, streaks in raw_streaks_by_team.items()
            }
            total_streaks = sum(len(v) for v in player_streaks_by_team.values())
            print(f"[digest] MLB player streaks: {total_streaks} streaks across {len(player_streaks_by_team)} teams")
    except Exception as e:
        print(f"[digest] MLB player streaks error (non-fatal): {e}")

    # --- Step 2: Find highest trend ---
    best_entry = max(all_trends_flat, key=lambda x: x["trend"]["count"])
    highest_trend = best_entry["trend"]
    highest_team = best_entry["label"]
    team_prefix = f"{highest_team}: " if highest_team else ""
    subject = f"GetSTAM trends of the day: {team_prefix}{highest_trend['description']}"
    print(f"[digest] Highest trend: {highest_team} — {highest_trend['description']} (count={highest_trend['count']})")

    # --- Step 3: Create + publish blog post ---
    existing = _check_existing_post(post_slug)
    if existing:
        post_id = existing["id"]
        print(f"[digest] Post already exists (id={post_id}, status={existing['status']}), skipping creation")
    else:
        content_md = _build_markdown(today_str, sport_results, player_streaks_by_team)
        excerpt = f"Today's strongest trends: {team_prefix}{highest_trend['description']} and more."
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
    subscribers, err = EmailService.get_all_subscribers()
    if err:
        print(f"[digest] Failed to get subscribers: {err}")
        return
    if not subscribers:
        print("[digest] No subscribers found. Skipping email send.")
        return

    print(f"[digest] Sending to {len(subscribers)} subscribers individually")
    sent_count = 0
    error_count = 0
    for email in subscribers:
        html = _build_html_email(today_str, highest_trend, highest_team, sport_results, post_slug, email)
        ok, err = EmailService.send_digest_to_one(email, subject, html)
        if ok:
            sent_count += 1
        else:
            print(f"[digest] Send error for {email}: {err}")
            error_count += 1

    print(f"[digest] Done. Sent: {sent_count}, Errors: {error_count}")


if __name__ == "__main__":
    run()
