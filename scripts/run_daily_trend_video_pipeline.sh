#!/bin/bash
# Daily MLB trend video pipeline — runs the full chain end to end:
#   1. Generate scripts (Claude) for the day's best-trending games
#   2. Screenshot each game's page (needs the local React + Flask servers)
#   3. Assemble videos (voiceover + Ken Burns/slide effects)
#   4. Upload to YouTube (unlisted)
#   5. Email a recap to DAILY_VIDEO_EMAIL_TO
#
# Meant to run unattended via launchd (see scripts/com.getstam.mlbtrendvideos.plist)
# or manually: ./scripts/run_daily_trend_video_pipeline.sh [YYYY-MM-DD]
#
# launchd runs with a minimal PATH/environment, so this script uses full
# paths throughout rather than relying on what's on PATH.

set -uo pipefail

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

run_step() {
  local script="$1"
  echo "--- Running $script $DATE_ARG ---"
  "$PYTHON" "$REPO_ROOT/jobs/$script" $DATE_ARG
  local status=$?
  if [ $status -ne 0 ]; then
    echo "ERROR: $script exited with status $status"
  fi
  return $status
}

run_step "mlb_generate_trend_video_scripts.py" || exit 1
run_step "mlb_generate_trend_video_screenshots.py" || exit 1
run_step "mlb_generate_trend_videos.py" || exit 1
run_step "mlb_upload_youtube_videos.py"   # don't abort the email step if YouTube upload has an issue
run_step "mlb_email_daily_videos.py"

echo "=== Daily trend video pipeline finished at $(date) ==="
