#!/bin/bash
#
# NFL daily player-props import, run from this laptop.
#
# Why local: ESPN's edge (Akamai) returns 403 for datacenter IPs, so the actuals
# steps (2 & 3, which hit site.api.espn.com) fail on Heroku. Odds (step 1) come
# from the Odds API and would run fine on Heroku, but we do them here too so the
# whole NFL pipeline lives in one place.
#
# Scheduled by ~/Library/LaunchAgents/com.getstam.nfl-daily-import.plist (6:00 AM
# local). If the Mac is asleep at 6:00, launchd runs it once on the next wake.
#
# - Odds:   yesterday only  (Odds API credits — keep the window tight)
# - Actuals/defense: last 3 days  (ESPN is free — wide window covers a missed run)
#
# Each step is hard-killed after STEP_CAP seconds (a slept-through DB socket can
# block psycopg2 forever). A killed step is recovered by the next run's 3-day
# actuals window.

set -u

PROJECT_DIR="/Users/stephaniegillen/Projects/get-stam-py"
PY="$PROJECT_DIR/venv/bin/python"
LOG_DIR="$PROJECT_DIR/logs"
STEP_CAP=2700   # 45 min

YESTERDAY="$(/bin/date -v-1d +%Y-%m-%d)"
THREE_DAYS_AGO="$(/bin/date -v-3d +%Y-%m-%d)"
LOG="$LOG_DIR/nfl_daily_import_${YESTERDAY}.log"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || { echo "cd $PROJECT_DIR failed"; exit 1; }

# run_capped SECS CMD...  -> run CMD, SIGKILL it if it exceeds SECS
run_capped() {
  local cap=$1; shift
  "$@" &
  local pid=$!
  ( sleep "$cap"; kill -9 "$pid" 2>/dev/null; pkill -9 -P "$pid" 2>/dev/null ) &
  local guard=$!
  wait "$pid"; local rc=$?
  kill "$guard" 2>/dev/null
  wait "$guard" 2>/dev/null
  [ "$rc" -gt 128 ] && echo "  (step killed after ${cap}s)"
  return "$rc"
}

{
  echo "================================================================"
  echo "nfl_daily_import  run=$(/bin/date +%Y-%m-%dT%H:%M:%S%z)"
  echo "  odds:    $YESTERDAY"
  echo "  actuals: $THREE_DAYS_AGO .. $YESTERDAY"
  echo "================================================================"

  echo "--- STEP 1: odds ($YESTERDAY) ---"
  run_capped "$STEP_CAP" /usr/bin/caffeinate -i "$PY" -u jobs/nfl_historical_player_odds_import.py "$YESTERDAY"
  echo "  step 1 exit: $?"

  echo "--- STEP 2: player actuals ($THREE_DAYS_AGO .. $YESTERDAY) ---"
  run_capped "$STEP_CAP" /usr/bin/caffeinate -i "$PY" -u jobs/nfl_historical_player_actuals_import_reverse.py "$THREE_DAYS_AGO" "$YESTERDAY"
  echo "  step 2 exit: $?"

  echo "--- STEP 3: defense (D/ST) actuals ($THREE_DAYS_AGO .. $YESTERDAY) ---"
  run_capped "$STEP_CAP" /usr/bin/caffeinate -i "$PY" -u jobs/nfl_historical_defense_actuals_import_reverse.py "$THREE_DAYS_AGO" "$YESTERDAY"
  echo "  step 3 exit: $?"

  echo "=== done $(/bin/date +%Y-%m-%dT%H:%M:%S%z) ==="
} >> "$LOG" 2>&1
