"""
MLB Trend Video YouTube Uploader

Step 4 of the trend-video pipeline (after mlb_generate_trend_videos.py).
Uploads each game's standard (non-TikTok) video to YouTube as an unlisted
video, and writes the resulting video URLs to
output/youtube_uploads/<date>.json so mlb_email_daily_videos.py can include
them in the recap email.

Only the standard "script" variant is uploaded — the "_tiktok" variant exists
specifically to dodge TikTok's gambling-language restrictions, which don't
apply on YouTube.

--- One-time setup ---
1. In Google Cloud Console (console.cloud.google.com), create/select a
   project, enable the "YouTube Data API v3", then under
   "APIs & Services -> Credentials" create an OAuth client ID of type
   "Desktop app". Download the JSON and save it as youtube_client_secret.json
   in the repo root (gitignored).
2. Run this script once (`venv/bin/python jobs/mlb_upload_youtube_videos.py`)
   — it'll open a browser for you to sign in with the Google account that
   owns the YouTube channel and grant upload access. This saves a refresh
   token to youtube_token.json (also gitignored) so future runs are fully
   unattended.

Usage:
    venv/bin/python jobs/mlb_upload_youtube_videos.py [YYYY-MM-DD]

Output:
    output/youtube_uploads/<date>.json
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "output" / "scripts"
VIDEOS_ROOT = REPO_ROOT / "output" / "videos"
UPLOADS_ROOT = REPO_ROOT / "output" / "youtube_uploads"

CLIENT_SECRETS_FILE = Path(os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", REPO_ROOT / "youtube_client_secret.json"))
TOKEN_FILE = Path(os.getenv("YOUTUBE_TOKEN_FILE", REPO_ROOT / "youtube_token.json"))

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "unlisted")
CATEGORY_ID = "17"  # Sports

TITLE_MAX_LEN = 100


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


def get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS_FILE.exists():
                raise RuntimeError(
                    f"No {CLIENT_SECRETS_FILE.name} found at {CLIENT_SECRETS_FILE}. "
                    "See the setup instructions at the top of this file."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return creds


def build_title(game):
    away = game["matchup"]["away_team"]
    home = game["matchup"]["home_team"]
    title = f"{away} @ {home} — Betting Trends & Predictions"
    return title[:TITLE_MAX_LEN]


def build_description(game):
    hook = (game.get("script") or {}).get("hook", "")
    script_text = (game.get("script") or {}).get("script", "")
    away = game["matchup"]["away_team"]
    home = game["matchup"]["home_team"]
    return (
        f"{hook}\n\n"
        f"{script_text}\n\n"
        f"More {away} vs {home} trends, odds, and history at https://www.getstam.com\n\n"
        "GetSTAM — stats that actually matter. For entertainment purposes only. "
        "Not affiliated with any sportsbook. Must be 18+ (21+ in some jurisdictions). "
        "Gambling problem? Call 1-800-GAMBLER.\n\n"
        "#MLB #SportsBetting #BettingTrends"
    )


def build_tags(game):
    away = game["matchup"]["away_team"]
    home = game["matchup"]["home_team"]
    return ["MLB", "baseball", "sports betting", "betting trends", "sports picks", away, home]


def upload_video(youtube, video_path, game):
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": build_title(game),
            "description": build_description(game),
            "tags": build_tags(game),
            "categoryId": CATEGORY_ID,
        },
        "status": {
            "privacyStatus": PRIVACY_STATUS,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
    return response["id"]


def run(date_str=None):
    from datetime import datetime
    import pytz

    if not date_str:
        date_str = datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d")

    games = load_games(date_str)
    print(f"Found {len(games)} game(s) with a script for {date_str}")
    if not games:
        return

    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("Missing deps. Run: pip install google-auth-oauthlib google-api-python-client")
        return

    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    results = {}
    ok, failed = 0, 0
    for game in games:
        game_id = game["game_id"]
        label = f"{game['matchup']['away_team']} @ {game['matchup']['home_team']}"
        video_path = VIDEOS_ROOT / date_str / f"{game_id}.mp4"
        if not video_path.exists():
            failed += 1
            print(f"  [SKIP] {label}: no video at {video_path}")
            continue
        try:
            video_id = upload_video(youtube, video_path, game)
            url = f"https://youtu.be/{video_id}"
            results[game_id] = {
                "video_id": video_id,
                "url": url,
                "matchup": game["matchup"],
                "hook": (game.get("script") or {}).get("hook"),
            }
            ok += 1
            print(f"  [OK] {label} -> {url}")
        except Exception as e:
            failed += 1
            print(f"  [FAILED] {label}: {e}")

    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = UPLOADS_ROOT / f"{date_str}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDone. uploaded={ok} failed={failed} -> {out_path}")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(date_arg)
