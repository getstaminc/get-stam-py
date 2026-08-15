"""
MLB Trend Video Screenshot Capturer

Step 2 of the trend-video pipeline (after mlb_generate_trend_video_scripts.py).
For every script JSON in output/scripts/<date>/, renders that game's
game-details page on YOUR OWN local/staging build and captures screenshots
to use as visual scenes in the generated video.

Requires a local instance of the site running and reachable (defaults to the
CRA dev server at http://localhost:3000 — override with SCREENSHOT_BASE_URL).
This intentionally never touches production or any third-party site: we own
this page, so screenshotting it is just an internal rendering step, not scraping.

Setup (one-time):
    pip install playwright
    playwright install chromium

Usage:
    # in another terminal: cd getstam-react && npm start
    venv/bin/python jobs/mlb_generate_trend_video_screenshots.py [YYYY-MM-DD]

Output:
    output/screenshots/<date>/<game_id>/hero.png   (first-fold shot — used for
                                                      the animated opening scene)
    output/screenshots/<date>/<game_id>/full.png   (full scrollable page)
"""

import os
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from api.utils.team_slugs import team_slug

SCRIPTS_ROOT = Path(__file__).resolve().parent.parent / "output" / "scripts"
SCREENSHOTS_ROOT = Path(__file__).resolve().parent.parent / "output" / "screenshots"
BASE_URL = os.getenv("SCREENSHOT_BASE_URL", "http://localhost:3000")

# Vertical, TikTok/Reels/Shorts-friendly viewport. "hero" is just the first fold
# at this size; "full" scrolls the whole page for extra b-roll scenes if wanted.
VIEWPORT = {"width": 1080, "height": 1920}

# Give the SPA time to fetch odds/trends/history and finish rendering before
# we screenshot — these panels load asynchronously after route mount.
RENDER_WAIT_MS = 3500

# The "hero" shot is clipped to start at this heading so the site nav/logo
# bar doesn't end up as the video's opening frame — every game-details page
# renders a TrendAnalysisSection with this exact text right below the nav.
HERO_CROP_ANCHOR_TEXT = "Trend Analysis"
HERO_CROP_TOP_PADDING = 16  # px of breathing room above the heading


def slug_for_game(matchup, date_str):
    away = team_slug(matchup["away_team"])
    home = team_slug(matchup["home_team"])
    return f"{away}-vs-{home}-{date_str}"


def load_games(date_str):
    date_dir = SCRIPTS_ROOT / date_str
    if not date_dir.exists():
        return []
    games = []
    for path in sorted(date_dir.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        if not data.get("matchup"):
            print(f"  [SKIP] {path.name}: no matchup data (likely a failed script run)")
            continue
        games.append(data)
    return games


def capture_game(page, game, date_str):
    game_id = game["game_id"]
    url = f"{BASE_URL}/game-details/mlb/{slug_for_game(game['matchup'], date_str)}"
    out_dir = SCREENSHOTS_ROOT / date_str / game_id
    out_dir.mkdir(parents=True, exist_ok=True)

    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(RENDER_WAIT_MS)

    hero_path = out_dir / "hero.png"
    anchor_locator = page.get_by_text(HERO_CROP_ANCHOR_TEXT, exact=True)
    box = anchor_locator.first.bounding_box() if anchor_locator.count() else None
    if box:
        top = max(box["y"] - HERO_CROP_TOP_PADDING, 0)
        page.screenshot(
            path=str(hero_path),
            clip={"x": 0, "y": top, "width": VIEWPORT["width"], "height": VIEWPORT["height"] - top},
        )
    else:
        # Fallback: anchor text not found (unexpected page state) — take the
        # full viewport rather than fail the whole game.
        page.screenshot(path=str(hero_path))

    full_path = out_dir / "full.png"
    page.screenshot(path=str(full_path), full_page=True)

    return url, hero_path, full_path


def run(date_str=None):
    from datetime import datetime
    import pytz

    if not date_str:
        date_str = datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d")

    games = load_games(date_str)
    print(f"Found {len(games)} script(s) for {date_str} in {SCRIPTS_ROOT / date_str}")
    if not games:
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed. Run:\n  pip install playwright\n  playwright install chromium")
        return

    ok, failed = 0, 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)
        for game in games:
            label = f"{game['matchup']['away_team']} @ {game['matchup']['home_team']}"
            try:
                url, hero_path, full_path = capture_game(page, game, date_str)
                ok += 1
                print(f"  [OK] {label} -> {hero_path.relative_to(SCREENSHOTS_ROOT.parent.parent)}")
            except Exception as e:
                failed += 1
                print(f"  [FAILED] {label}: {e}")
        browser.close()

    print(f"\nDone. captured={ok} failed={failed}")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(date_arg)
