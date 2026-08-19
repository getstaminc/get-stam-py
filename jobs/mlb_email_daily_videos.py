"""
MLB Trend Video Daily Recap Email

Step 5 (final step) of the trend-video pipeline (after
mlb_upload_youtube_videos.py). Sends one email per game — matchup, hook
line, the hero screenshot as a small inline attachment, the unlisted
YouTube link, and the local path to the raw video files (both the standard
and TikTok-sanitized cuts) for manually posting to TikTok/Instagram/X/Reddit.

Videos themselves are NOT attached — they're 30-40MB each, well past
Brevo's 4MB-per-file / 20MB-per-email attachment cap, so email is a
notification + hand-off point, not a file-transfer channel.

Usage:
    venv/bin/python jobs/mlb_email_daily_videos.py [YYYY-MM-DD]
"""

import os
import sys
import json
import base64
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from api.services.email_service import EmailService

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "output" / "scripts"
SCREENSHOTS_ROOT = REPO_ROOT / "output" / "screenshots"
VIDEOS_ROOT = REPO_ROOT / "output" / "videos"
UPLOADS_ROOT = REPO_ROOT / "output" / "youtube_uploads"

RECIPIENT = os.getenv("DAILY_VIDEO_EMAIL_TO", "getstaminc@gmail.com")

# Brevo's attachment cap is 4MB/file — the hero screenshot is a few hundred
# KB so it's always safe, but guard anyway rather than fail the send.
MAX_ATTACHMENT_BYTES = 4 * 1024 * 1024


def load_games(date_str):
    date_dir = SCRIPTS_ROOT / date_str
    if not date_dir.exists():
        return []
    games = []
    for path in sorted(date_dir.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        if not data.get("matchup") or not (data.get("script") or {}).get("script"):
            continue
        games.append(data)
    return games


def load_youtube_uploads(date_str):
    path = UPLOADS_ROOT / f"{date_str}.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def build_html(game, date_str, youtube_url, standard_path, tiktok_path, has_thumbnail):
    away = game["matchup"]["away_team"]
    home = game["matchup"]["home_team"]
    hook = (game.get("script") or {}).get("hook", "")

    youtube_line = f'<p><a href="{youtube_url}">Watch on YouTube (unlisted)</a></p>' if youtube_url else "<p>(YouTube upload not found for this game.)</p>"
    # Brevo's simple attachment API doesn't support Content-ID inline
    # embedding, so the thumbnail rides along as a regular attachment
    # (visible in the email client's attachment list) rather than inline.
    thumb_line = "<p><em>Thumbnail attached.</em></p>" if has_thumbnail else ""

    return f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 600px;">
      <h2>{away} @ {home}</h2>
      <p><em>{hook}</em></p>
      {thumb_line}
      {youtube_line}
      <p style="color:#555;">Local files (for manual posting to TikTok/Instagram/X/Reddit):</p>
      <ul style="color:#555; font-size: 0.9em;">
        <li>Standard: {standard_path}</li>
        <li>TikTok-safe: {tiktok_path}</li>
      </ul>
      <p style="color:#999; font-size: 0.8em;">GetSTAM daily trend videos — {date_str}</p>
    </div>
    """


def send_game_email(game, date_str, youtube_uploads):
    game_id = game["game_id"]
    away = game["matchup"]["away_team"]
    home = game["matchup"]["home_team"]

    upload = youtube_uploads.get(game_id) or {}
    youtube_url = upload.get("url")

    standard_path = VIDEOS_ROOT / date_str / f"{game_id}.mp4"
    tiktok_path = VIDEOS_ROOT / date_str / f"{game_id}_tiktok.mp4"
    thumb_path = SCREENSHOTS_ROOT / date_str / game_id / "hero.png"

    attachments = []
    has_thumbnail = False
    if thumb_path.exists() and thumb_path.stat().st_size <= MAX_ATTACHMENT_BYTES:
        content_b64 = base64.b64encode(thumb_path.read_bytes()).decode("ascii")
        attachments.append({"name": "thumbnail.png", "content_b64": content_b64})
        has_thumbnail = True

    subject = f"[GetSTAM] {away} @ {home} — video ready"
    html = build_html(game, date_str, youtube_url, standard_path, tiktok_path, has_thumbnail)

    return EmailService.send_with_attachments(RECIPIENT, subject, html, attachments=attachments)


def run(date_str=None):
    from datetime import datetime
    import pytz

    if not date_str:
        date_str = datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d")

    games = load_games(date_str)
    print(f"Found {len(games)} game(s) with a script for {date_str}")
    if not games:
        return

    youtube_uploads = load_youtube_uploads(date_str)

    ok, failed, skipped = 0, 0, 0
    for game in games:
        label = f"{game['matchup']['away_team']} @ {game['matchup']['home_team']}"

        # Only email games that actually got a video rendered — a game can
        # have a script (and even a TikTok script) without reaching this
        # stage, e.g. it wasn't in the top-N picked for the full pipeline.
        video_path = VIDEOS_ROOT / date_str / f"{game['game_id']}.mp4"
        if not video_path.exists():
            skipped += 1
            print(f"  [SKIP] {label}: no video at {video_path}")
            continue

        success, err = send_game_email(game, date_str, youtube_uploads)
        if success:
            ok += 1
            print(f"  [OK] {label} -> emailed {RECIPIENT}")
        else:
            failed += 1
            print(f"  [FAILED] {label}: {err}")

    print(f"\nDone. emailed={ok} failed={failed} skipped={skipped}")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(date_arg)
