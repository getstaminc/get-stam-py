#!/bin/bash
# Daily trend video pipeline (MLB + NFL + NCAAF) — runs the full chain end to end:
#   1. Generate scripts (Claude) for the day's best-trending games, per sport
#   2. Screenshot each game's page (needs the local React + Flask servers)
#   3. Assemble videos (voiceover + Ken Burns/slide effects)
#   4. Upload to YouTube (per YOUTUBE_PRIVACY_STATUS, currently public)
#   5. Email a recap to DAILY_VIDEO_EMAIL_TO
#
# NFL and NCAAF generate on every run: a real matchup slate when games exist
# for the day, or (on off days) a preview of the upcoming Sunday/Saturday
# slate instead — see nfl_generate_trend_video_scripts.py /
# ncaaf_generate_trend_video_scripts.py.
#
# Meant to run unattended via launchd (see scripts/com.getstam.mlbtrendvideos.plist,
# which wraps this in `caffeinate -i` so the Mac can't fall back asleep
# mid-render). If running manually, do the same:
#   caffeinate -i ./scripts/run_daily_trend_video_pipeline.sh [YYYY-MM-DD]
#
# launchd runs with a minimal PATH/environment (just /usr/bin:/bin:/usr/sbin:/sbin),
# so this script uses full paths for its own direct calls, AND exports a
# richer PATH so subprocess.run(["ffmpeg", ...]) / ["ffprobe", ...]) inside
# the Python jobs (which rely on PATH lookup, not full paths) can find
# Homebrew's binaries too.
set -uo pipefail

export PATH="/opt/homebrew/bin:$PATH"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="$REPO_ROOT/venv/bin/python"
NPM="/opt/homebrew/bin/npm"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"

DATE_ARG="${1:-}"
RUN_STAMP="$(date +%Y-%m-%d_%H%M%S)"
LOG_FILE="$LOG_DIR/daily_trend_video_pipeline_${RUN_STAMP}.log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Daily trend video pipeline starting at $(date) ==="

FLASK_PID=""
REACT_PID=""
STARTED_FLASK=0
STARTED_REACT=0

cleanup() {
  if [ "$STARTED_FLASK" = "1" ] && [ -n "$FLASK_PID" ]; then
    echo "Stopping Flask (pid $FLASK_PID)..."
    kill "$FLASK_PID" 2>/dev/null
  fi
  if [ "$STARTED_REACT" = "1" ] && [ -n "$REACT_PID" ]; then
    echo "Stopping React dev server (pid $REACT_PID)..."
    kill "$REACT_PID" 2>/dev/null
  fi
}
trap cleanup EXIT

wait_for_http() {
  local url="$1"
  local label="$2"
  for i in $(seq 1 60); do
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200"; then
      echo "$label is up."
      return 0
    fi
    sleep 2
  done
  echo "ERROR: $label did not come up in time."
  return 1
}

# --- Start local Flask backend if not already running ---
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000 2>/dev/null | grep -q "200\|30[0-9]"; then
  echo "Flask already running on :5000, reusing it."
else
  echo "Starting Flask backend..."
  FLASK_ENV=development "$PYTHON" "$REPO_ROOT/app.py" > "$LOG_DIR/flask_${RUN_STAMP}.log" 2>&1 &
  FLASK_PID=$!
  STARTED_FLASK=1
  wait_for_http "http://127.0.0.1:5000/" "Flask" || { echo "Aborting: Flask backend unavailable."; exit 1; }
fi

# --- Start local React dev server if not already running ---
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null | grep -q "200"; then
  echo "React dev server already running on :3000, reusing it."
else
  echo "Starting React dev server..."
  (cd "$REPO_ROOT/getstam-react" && BROWSER=none "$NPM" start > "$LOG_DIR/react_${RUN_STAMP}.log" 2>&1) &
  STARTED_REACT=1
  wait_for_http "http://localhost:3000" "React dev server" || { echo "Aborting: React dev server unavailable."; exit 1; }
  # $! above is the subshell's PID, not the actual node process CRA spawns
  # underneath npm — look up whoever's actually listening on :3000 instead,
  # so cleanup() can reliably stop it later.
  REACT_PID="$(lsof -ti:3000 -sTCP:LISTEN | head -1)"
  sleep 5  # let the first compile fully settle
fi

# Retries on a nonzero exit (max 2 attempts by default) — no hard wall-clock
# timeout here. An earlier attempt at this wrapped every step in `gtimeout`
# to also catch true hangs, but inserting that extra binary into the exec
# chain broke Python's own venv resolution under launchd in a way that was
# never fully explained (worked fine invoked directly, failed only via
# launchd) — reverted rather than risk repeating it. So this only covers
# "ran and failed" (screenshot nav timeouts, transient API errors, etc.),
# not "hung forever with no timeout" — that's a known gap, not a design win.
# run_step takes an explicit date (rather than always reading the global
# DATE_ARG) because NFL's script generator can file its output under a
# fallback date different from today's (see below) — the shared
# screenshots/video/upload/email steps need to be pointed at whichever date
# actually has content.
run_step() {
  local script="$1"
  local date_val="$2"
  local max_attempts="${3:-2}"
  local attempt=1
  while [ "$attempt" -le "$max_attempts" ]; do
    echo "--- Running $script $date_val (attempt $attempt/$max_attempts) ---"
    "$PYTHON" "$REPO_ROOT/jobs/$script" $date_val
    local status=$?
    if [ $status -eq 0 ]; then
      return 0
    fi
    echo "ERROR: $script exited with status $status (attempt $attempt/$max_attempts)"
    attempt=$((attempt + 1))
  done
  return 1
}

# Resolve "today" the same way the Python jobs do (US/Eastern) so it matches
# exactly what mlb_generate_trend_video_scripts.py used when DATE_ARG is empty.
if [ -n "$DATE_ARG" ]; then
  MLB_DATE="$DATE_ARG"
else
  MLB_DATE="$("$PYTHON" -c "from datetime import datetime; import pytz; print(datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d'))")"
fi

NFL_MARKER="$REPO_ROOT/output/.nfl_last_run_date"
NCAAF_MARKER="$REPO_ROOT/output/.ncaaf_last_run_date"
rm -f "$NFL_MARKER" "$NCAAF_MARKER"   # avoid reprocessing a stale date if a sport generates nothing this run

run_step "mlb_generate_trend_video_scripts.py" "$DATE_ARG" 2 || exit 1
run_step "nfl_generate_trend_video_scripts.py" "$DATE_ARG" 2     # don't abort MLB publishing over an NFL issue
run_step "ncaaf_generate_trend_video_scripts.py" "$DATE_ARG" 2   # don't abort MLB publishing over an NCAAF issue

run_step "mlb_generate_trend_video_screenshots.py" "$MLB_DATE" 2 || exit 1
run_step "mlb_generate_trend_videos.py" "$MLB_DATE" 2 || exit 1
run_step "mlb_upload_youtube_videos.py" "$MLB_DATE" 2   # don't abort the email step if YouTube upload has an issue
run_step "mlb_email_daily_videos.py" "$MLB_DATE" 2

# NFL/NCAAF preview themselves on off days by pulling the upcoming Sunday/
# Saturday slate, filing scripts under that future date instead of today's
# (see nfl_generate_trend_video_scripts.py / ncaaf_generate_trend_video_scripts.py).
# When that happens, run the shared pipeline again for that date so those
# scripts actually get screenshotted/rendered/published instead of sitting
# untouched. Track which dates are already covered so two sports landing on
# the same fallback date don't get double-processed.
PROCESSED_DATES=("$MLB_DATE")

for marker_and_label in "$NFL_MARKER:NFL" "$NCAAF_MARKER:NCAAF"; do
  marker_file="${marker_and_label%%:*}"
  label="${marker_and_label##*:}"
  [ -f "$marker_file" ] || continue
  this_date="$(cat "$marker_file")"
  [ -z "$this_date" ] && continue

  already_done=0
  for d in "${PROCESSED_DATES[@]}"; do
    [ "$d" = "$this_date" ] && already_done=1
  done
  if [ "$already_done" -eq 0 ]; then
    echo "--- $label filed scripts under $this_date — running the shared pipeline again for that date ---"
    run_step "mlb_generate_trend_video_screenshots.py" "$this_date" 2
    run_step "mlb_generate_trend_videos.py" "$this_date" 2
    run_step "mlb_upload_youtube_videos.py" "$this_date" 2
    run_step "mlb_email_daily_videos.py" "$this_date" 2
    PROCESSED_DATES+=("$this_date")
  fi
done

echo "=== Daily trend video pipeline finished at $(date) ==="
