#!/bin/bash
#
# MLB daily player-props import, run from this laptop.
#
# Why local: ESPN's edge (Akamai) 403s datacenter IPs, so the actuals step (which
# hits site.api.espn.com) fails on Heroku. This stopped Aug 3 2026. Odds come from
# the Odds API and are fine on Heroku, but we do the whole pipeline here.
#
# Scheduled by ~/Library/LaunchAgents/com.getstam.mlb-daily-import.plist (6:15 AM
# local). If the Mac is asleep at 6:15, launchd runs it once on the next wake.
#
# - Orchestrator (odds + actuals): yesterday only  (Odds API credits)
# - Extra actuals-only catch-up:    last 3 days     (ESPN is free)
#
# Each step is hard-killed after STEP_CAP seconds. If the Mac sleeps mid-run the
# DB socket can go stale and psycopg2 blocks forever with no statement timeout
# (this happened 2026-09-09, hung 3h+). A killed step is recovered by the next
# run's 3-day catch-up window.

set -u

PROJECT_DIR="/Users/stephaniegillen/Projects/get-stam-py"
PY="$PROJECT_DIR/venv/bin/python"
LOG_DIR="$PROJECT_DIR/logs"
STEP_CAP=2700   # 45 min

YESTERDAY="$(/bin/date -v-1d +%Y-%m-%d)"
THREE_DAYS_AGO="$(/bin/date -v-3d +%Y-%m-%d)"
LOG="$LOG_DIR/mlb_daily_import_${YESTERDAY}.log"

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
  echo "mlb_daily_import  run=$(/bin/date +%Y-%m-%dT%H:%M:%S%z)"
  echo "  orchestrator: $YESTERDAY   (odds + actuals)"
  echo "  actuals catch-up: $THREE_DAYS_AGO .. $YESTERDAY"
  echo "================================================================"

  echo "--- orchestrator ($YESTERDAY) ---"
  run_capped "$STEP_CAP" /usr/bin/caffeinate -i "$PY" -u jobs/mlb_historical_import_orchestrator_reverse.py "$YESTERDAY"
  echo "  orchestrator exit: $?"

  echo "--- actuals catch-up ($THREE_DAYS_AGO .. $YESTERDAY) ---"
  run_capped "$STEP_CAP" /usr/bin/caffeinate -i "$PY" -u jobs/mlb_historical_player_actuals_import_reverse.py "$THREE_DAYS_AGO" "$YESTERDAY"
  echo "  actuals catch-up exit: $?"

  echo "=== done $(/bin/date +%Y-%m-%dT%H:%M:%S%z) ==="
} >> "$LOG" 2>&1
