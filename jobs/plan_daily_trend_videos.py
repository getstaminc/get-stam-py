"""
Daily Trend Video Scheduler

Decides, for a given day, which sports get script-generated and for which
date(s) — including "look ahead" previews of a future slate — per the
weekly plan below. This replaces each sport generator's old reactive
auto-fallback logic (silently previewing "the next Sat/Sun" whenever today
was empty); scheduling is now explicit here and each generator's run() just
does what it's told.

Weekly plan (python's date.weekday(): Monday=0 ... Sunday=6). Every
max/preference below is a soft tiebreak around trend score, not a hard
filter — see trend_video_common.select_top_games.

  Monday    — MLB today (max 3); NFL today (max 3, Monday night game)
  Tuesday   — MLB today (max 3) only
  Wednesday — MLB today (max 3) only
  Thursday  — MLB today (max 3); NFL today (max 3, Thursday night game);
              NCAAF today (max 3)
  Friday    — MLB today (max 3); NCAAF today (max 3); NCAAF look-ahead to
              Saturday (max 3, prefer earlier kickoffs)
  Saturday  — NCAAF today (max 3, prefer later kickoffs — not noon/1pm ET);
              NFL look-ahead to Sunday (max 2, prefer the early game block)
  Sunday    — MLB today (max 3); NFL today (max 3, prefer the afternoon
              block or later)

Usage:
  venv/bin/python jobs/plan_daily_trend_videos.py [YYYY-MM-DD]

Writes output/.trend_video_dates.json — a JSON list of every date_str that
received at least one script this run — for the orchestrator
(scripts/run_daily_trend_video_pipeline.sh) to run the shared
screenshots/video/upload/email steps against.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import jobs.mlb_generate_trend_video_scripts as mlb_job
import jobs.nfl_generate_trend_video_scripts as nfl_job
import jobs.ncaaf_generate_trend_video_scripts as ncaaf_job
from jobs.trend_video_common import next_weekday

eastern_tz = pytz.timezone("US/Eastern")
DATES_MARKER = Path(__file__).resolve().parent.parent / "output" / ".trend_video_dates.json"

MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = range(7)


def build_plan(date_str):
    """Return a list of (sport_name, module, target_date, run_kwargs) for date_str's weekday."""
    weekday = datetime.strptime(date_str, "%Y-%m-%d").date().weekday()
    saturday = next_weekday(date_str, SATURDAY)
    sunday = next_weekday(date_str, SUNDAY)

    plan = [("mlb", mlb_job, date_str, {"max_games": 3})]

    if weekday in (MONDAY, THURSDAY):
        # That night's NFL game.
        plan.append(("nfl", nfl_job, date_str, {"max_games": 3}))
    elif weekday == SUNDAY:
        plan.append(("nfl", nfl_job, date_str, {"max_games": 3, "time_pref": "afternoon_or_later"}))
    elif weekday == SATURDAY:
        plan.append(("nfl", nfl_job, sunday, {"max_games": 2, "lookahead": True, "time_pref": "early_block"}))

    if weekday in (THURSDAY, FRIDAY, SATURDAY):
        time_pref = "not_noon_or_1pm" if weekday == SATURDAY else None
        plan.append(("ncaaf", ncaaf_job, date_str, {"max_games": 3, "time_pref": time_pref}))
    if weekday == FRIDAY:
        plan.append(("ncaaf", ncaaf_job, saturday, {"max_games": 3, "lookahead": True, "time_pref": "earlier_in_day"}))

    return plan


def run(date_str=None):
    if not date_str:
        date_str = datetime.now(eastern_tz).strftime("%Y-%m-%d")

    plan = build_plan(date_str)
    weekday_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
    print(f"=== Trend video plan for {date_str} ({weekday_name}) ===")
    for sport, _, target_date, opts in plan:
        tag = " [LOOKAHEAD]" if opts.get("lookahead") else ""
        print(f"  {sport.upper()} -> {target_date}{tag} {opts}")

    dates_with_content = set()
    for sport, module, target_date, opts in plan:
        print(f"\n--- {sport.upper()} for {target_date} ---")
        try:
            result_date, scripts_generated = module.run(target_date, **opts)
        except Exception as e:
            print(f"  [ERROR] {sport} run failed: {e}")
            continue
        if scripts_generated:
            dates_with_content.add(result_date or target_date)

    dates_with_content = sorted(dates_with_content)
    DATES_MARKER.parent.mkdir(parents=True, exist_ok=True)
    DATES_MARKER.write_text(json.dumps(dates_with_content))
    print(f"\n=== Plan complete. Dates with content: {dates_with_content} ===")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(date_arg)
