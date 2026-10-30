# Daily Data Integrity Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new daily job, `jobs/send_data_integrity_report.py`, that compares yesterday's final games (per sport, from ESPN) against our DB's row counts, flags player-prop completeness gaps for the sports that have a props pipeline, and emails the result to the admin inbox.

**Architecture:** Single job file, following the exact structural precedent of `jobs/send_player_mismatch_report.py` — a list of per-sport config dicts, one `_check_*` function per concern, an `_build_html` function, and a `run()` that loops sports non-fatally and sends one email via `EmailService.send_digest_to_one`. No new tables, no new models, no changes to any existing ingestion job.

**Tech Stack:** Python, `requests` (ESPN calls), `sqlalchemy` (`create_engine`/`text`, matching `send_player_mismatch_report.py`'s connection style), `api.services.email_service.EmailService`.

**Spec:** `docs/superpowers/specs/2026-10-30-data-integrity-report-design.md`

## Global Constraints

- ESPN requests must send `User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"` — a bare `python-requests` UA gets blocked on at least one ESPN endpoint (per spec).
- Email goes to a single admin recipient via `EmailService.send_digest_to_one`, never the Brevo subscriber list — reuse `REPORT_RECIPIENT = "getstaminc@gmail.com"` convention from `jobs/send_player_mismatch_report.py:36`.
- Every per-sport check must be wrapped so one sport's failure (network error, bad response shape) does not stop the other sports from being checked or the email from being sent — same non-fatal pattern as `jobs/send_daily_trends_digest.py`'s per-sport `try/except`.
- No new DB tables, columns, or migrations — this job only reads.
- `DATABASE_URL` env var needs the same `postgres://` → `postgresql://` replacement used everywhere else in `jobs/`.

---

### Task 1: Games-count check (ESPN vs. DB) for all 12 sport/league entries, with a dry-run email

**Files:**
- Create: `jobs/send_data_integrity_report.py`

**Interfaces:**
- Produces: `SPORTS_CONFIG` (list of dicts, one per sport/league — consumed by Task 2 to add prop-check config), `_fetch_espn_final_games(slug, date_str, extra_params=None) -> list[dict]`, `_get_db_game_count(engine, table, date_obj, league_filter=None) -> int`, `_check_games_count(engine, sport_cfg, target_date) -> dict`, `run()`.

- [ ] **Step 1: Write the job skeleton with ESPN fetch + DB count functions**

```python
#!/usr/bin/python3
"""
Daily Data Integrity Report
Compares yesterday's final games (ESPN) against our DB row counts, and
flags player-prop completeness gaps for NBA/NFL/MLB/NHL.
Runs every morning via Heroku Scheduler, after the nightly seed jobs:
  python jobs/send_data_integrity_report.py
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(override=True)

import requests
from sqlalchemy import create_engine, text

from api.services.email_service import EmailService

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
REPORT_RECIPIENT = "getstaminc@gmail.com"
ESPN_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Each entry: espn_slug + espn_final_statuses identify how to ask ESPN "what
# finished yesterday"; table/date_col/league_filter identify how to count
# our own rows for the same day. prop_tables is added in Task 2 — sports
# without a props pipeline simply never get that key.
SPORTS_CONFIG = [
    {"key": "nba", "display": "NBA", "espn_slug": "basketball/nba",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "nba_games_1", "date_col": "game_date", "league_filter": None},
    {"key": "nfl", "display": "NFL", "espn_slug": "football/nfl",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "nfl_games", "date_col": "game_date", "league_filter": None},
    {"key": "mlb", "display": "MLB", "espn_slug": "baseball/mlb",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "mlb_games", "date_col": "game_date", "league_filter": None},
    {"key": "nhl", "display": "NHL", "espn_slug": "hockey/nhl",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "nhl_games", "date_col": "game_date", "league_filter": None},
    {"key": "ncaaf", "display": "NCAAF", "espn_slug": "football/college-football",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {},
     "table": "ncaaf_games", "date_col": "game_date", "league_filter": None},
    {"key": "ncaab", "display": "NCAAB", "espn_slug": "basketball/mens-college-basketball",
     "espn_final_statuses": {"STATUS_FINAL"}, "espn_extra_params": {"groups": 50},
     "table": "ncaab_games", "date_col": "game_date", "league_filter": None},
    {"key": "epl", "display": "EPL", "espn_slug": "soccer/eng.1",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "EPL"},
    {"key": "laliga", "display": "La Liga", "espn_slug": "soccer/esp.1",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "LA LIGA"},
    {"key": "bundesliga", "display": "Bundesliga", "espn_slug": "soccer/ger.1",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "BUNDESLIGA"},
    {"key": "ligue1", "display": "Ligue 1", "espn_slug": "soccer/fra.1",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "LIGUE 1"},
    {"key": "seriea", "display": "Serie A", "espn_slug": "soccer/ita.1",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "SERIE A"},
    {"key": "ucl", "display": "UCL", "espn_slug": "soccer/uefa.champions",
     "espn_final_statuses": {"STATUS_FULL_TIME"}, "espn_extra_params": {},
     "table": "soccer_games", "date_col": "game_date", "league_filter": "UCL"},
]


def _get_engine():
    return create_engine(DATABASE_URL)


def _fetch_espn_final_games(slug, date_str, final_statuses, extra_params=None):
    """Return list of {'espn_id','home','away','status'} for events ESPN
    reports as finished on date_str (YYYYMMDD) for the given sport slug."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{slug}/scoreboard"
    params = {"dates": date_str, "limit": 100}
    if extra_params:
        params.update(extra_params)
    resp = requests.get(url, headers=ESPN_HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    events = resp.json().get("events", [])

    finals = []
    for event in events:
        status = event.get("status", {}).get("type", {}).get("name", "")
        if status not in final_statuses:
            continue
        competitors = event.get("competitions", [{}])[0].get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})
        finals.append({
            "espn_id": event.get("id"),
            "home": home.get("team", {}).get("displayName", "?"),
            "away": away.get("team", {}).get("displayName", "?"),
            "status": status,
        })
    return finals


def _get_db_game_count(engine, table, date_col, date_obj, league_filter=None):
    sql = f"SELECT COUNT(*) FROM {table} WHERE {date_col} = :d"
    params = {"d": date_obj}
    if league_filter is not None:
        sql += " AND league = :league"
        params["league"] = league_filter
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar()


def _check_games_count(engine, cfg, target_date, date_str):
    espn_games = _fetch_espn_final_games(
        cfg["espn_slug"], date_str, cfg["espn_final_statuses"], cfg["espn_extra_params"]
    )
    db_count = _get_db_game_count(engine, cfg["table"], cfg["date_col"], target_date, cfg["league_filter"])
    return {
        "sport": cfg["display"],
        "espn_count": len(espn_games),
        "db_count": db_count,
        "mismatch": len(espn_games) != db_count,
        "espn_games": espn_games,
    }


def run():
    target_date = date.today() - timedelta(days=1)
    date_str = target_date.strftime("%Y%m%d")
    print(f"[integrity-report] Checking games for {target_date}")

    engine = _get_engine()
    games_results = []
    for cfg in SPORTS_CONFIG:
        try:
            result = _check_games_count(engine, cfg, target_date, date_str)
            games_results.append(result)
            print(f"[integrity-report] {cfg['display']}: ESPN={result['espn_count']} DB={result['db_count']} "
                  f"{'MISMATCH' if result['mismatch'] else 'ok'}")
        except Exception as e:
            print(f"[integrity-report] {cfg['display']} error (non-fatal): {e}")
            games_results.append({
                "sport": cfg["display"], "espn_count": None, "db_count": None,
                "mismatch": True, "espn_games": [], "error": str(e),
            })

    total_mismatches = sum(1 for r in games_results if r["mismatch"])
    print(f"[integrity-report] {total_mismatches} sport(s) with a games-count mismatch")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Run it against real data for a known date to sanity-check counts**

Run: `cd /Users/stephaniegillen/Projects/get-stam-py && python jobs/send_data_integrity_report.py`

Expected: one `[integrity-report] <Sport>: ESPN=<n> DB=<n> ok|MISMATCH` line per sport in `SPORTS_CONFIG`, no unhandled exceptions. A mismatch here is *useful signal*, not necessarily a bug — but if every sport shows a mismatch, that's a sign the query or ESPN call itself is wrong, not that every ingestion job failed; double check the date math and a couple of table/column names against the spec before moving on.

- [ ] **Step 3: Commit**

```bash
git add jobs/send_data_integrity_report.py
git commit -m "feat: add games-count integrity check (ESPN vs DB) for all tracked sports"
```

---

### Task 2: Player-prop completeness check for NBA/NFL/MLB/NHL + HTML email + wire into `run()`

**Files:**
- Modify: `jobs/send_data_integrity_report.py`

**Interfaces:**
- Consumes: `SPORTS_CONFIG`, `_get_engine()`, `_check_games_count()`, `games_results` shape from Task 1.
- Produces: `_check_prop_completeness(engine, cfg, target_date) -> dict`, `_build_html(games_results, prop_results, target_date) -> str`, updated `run()` that sends the email.

- [ ] **Step 1: Add prop-table config to the four sports that have one**

Add a `prop_check` key to the `nba`, `nfl`, `mlb`, `nhl` entries in `SPORTS_CONFIG` (the other 8 entries get no `prop_check` key — `.get("prop_check")` in Step 2 handles that):

```python
# nba entry gets:
"prop_check": {"mode": "team_id_join", "games_table": "nba_games_1",
               "prop_tables": ["nba_player_props"]},
# nfl entry gets:
"prop_check": {"mode": "event_id_join", "games_table": "nfl_games",
               "prop_tables": ["nfl_player_props"]},
# mlb entry gets:
"prop_check": {"mode": "event_id_join", "games_table": "mlb_games",
               "prop_tables": ["mlb_batter_props", "mlb_pitcher_props"]},
# nhl entry gets:
"prop_check": {"mode": "event_id_join", "games_table": "nhl_games",
               "prop_tables": ["nhl_player_props"]},
```

- [ ] **Step 2: Add the prop-completeness check function**

```python
def _check_prop_completeness(engine, cfg, target_date):
    """For each DB game on target_date, check whether ANY row exists in
    every configured prop table for that game. Returns games with zero
    prop rows in at least one required table."""
    prop_cfg = cfg.get("prop_check")
    if not prop_cfg:
        return {"sport": cfg["display"], "applicable": False, "missing_games": []}

    missing_games = []
    with engine.connect() as conn:
        if prop_cfg["mode"] == "event_id_join":
            rows = conn.execute(text(f"""
                SELECT odds_event_id, home_team_name, away_team_name
                FROM {prop_cfg['games_table']}
                WHERE game_date = :d AND odds_event_id IS NOT NULL
            """), {"d": target_date}).fetchall()
            for event_id, home, away in rows:
                for prop_table in prop_cfg["prop_tables"]:
                    count = conn.execute(text(
                        f"SELECT COUNT(*) FROM {prop_table} WHERE odds_event_id = :eid"
                    ), {"eid": event_id}).scalar()
                    if count == 0:
                        missing_games.append({
                            "home": home, "away": away, "missing_table": prop_table,
                        })

        elif prop_cfg["mode"] == "team_id_join":
            rows = conn.execute(text(f"""
                SELECT home_team_id, away_team_id, home_team_name, away_team_name
                FROM {prop_cfg['games_table']}
                WHERE game_date = :d
            """), {"d": target_date}).fetchall()
            for home_id, away_id, home_name, away_name in rows:
                for prop_table in prop_cfg["prop_tables"]:
                    count = conn.execute(text(f"""
                        SELECT COUNT(*) FROM {prop_table}
                        WHERE game_date = :d AND odds_home_team_id = :hid AND odds_away_team_id = :aid
                    """), {"d": target_date, "hid": home_id, "aid": away_id}).scalar()
                    if count == 0:
                        missing_games.append({
                            "home": home_name, "away": away_name, "missing_table": prop_table,
                        })

    return {"sport": cfg["display"], "applicable": True, "missing_games": missing_games}
```

- [ ] **Step 3: Add the HTML builder**

```python
def _build_html(games_results, prop_results, target_date):
    games_rows = "".join(
        f"<tr><td>{r['sport']}</td>"
        f"<td>{r['espn_count'] if r['espn_count'] is not None else 'ERROR'}</td>"
        f"<td>{r['db_count'] if r['db_count'] is not None else 'ERROR'}</td>"
        f"<td style=\"color:{'#d93025' if r['mismatch'] else '#188038'}\">"
        f"{'MISMATCH' if r['mismatch'] else 'ok'}</td></tr>"
        for r in games_results
    )

    mismatch_detail_sections = []
    for r in games_results:
        if not r["mismatch"] or not r.get("espn_games"):
            continue
        game_rows = "".join(
            f"<li>{g['away']} @ {g['home']} (ESPN id {g['espn_id']}, status {g['status']})</li>"
            for g in r["espn_games"]
        )
        mismatch_detail_sections.append(f"""
            <h4>{r['sport']} — ESPN's finished games for {target_date}</h4>
            <ul>{game_rows}</ul>
        """)

    prop_sections = []
    total_missing = 0
    for r in prop_results:
        if not r["applicable"]:
            continue
        missing = r["missing_games"]
        total_missing += len(missing)
        if not missing:
            prop_sections.append(f"<h4>{r['sport']}</h4><p>All games have prop rows in every required table.</p>")
            continue
        rows = "".join(
            f"<tr><td>{m['away']} @ {m['home']}</td><td>{m['missing_table']}</td></tr>"
            for m in missing
        )
        prop_sections.append(f"""
            <h4>{r['sport']} ({len(missing)} gap(s))</h4>
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>Game</th><th>Missing from</th></tr>
                {rows}
            </table>
        """)

    return f"""
        <div style="font-family: sans-serif;">
            <h2>Data Integrity Report — {target_date}</h2>

            <h3>Games Count (ESPN vs. DB)</h3>
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>Sport</th><th>ESPN finished</th><th>In our DB</th><th>Status</th></tr>
                {games_rows}
            </table>
            {''.join(mismatch_detail_sections)}

            <h3>Player Props Completeness ({total_missing} gap(s) across NBA/NFL/MLB/NHL)</h3>
            {''.join(prop_sections)}
        </div>
    """
```

- [ ] **Step 4: Wire prop checks and email sending into `run()`**

Replace the end of `run()` (from `total_mismatches = ...` onward) with:

```python
    total_mismatches = sum(1 for r in games_results if r["mismatch"])
    print(f"[integrity-report] {total_mismatches} sport(s) with a games-count mismatch")

    prop_results = []
    for cfg in SPORTS_CONFIG:
        try:
            result = _check_prop_completeness(engine, cfg, target_date)
            prop_results.append(result)
            if result["applicable"]:
                print(f"[integrity-report] {cfg['display']} props: {len(result['missing_games'])} gap(s)")
        except Exception as e:
            print(f"[integrity-report] {cfg['display']} prop-check error (non-fatal): {e}")
            prop_results.append({"sport": cfg["display"], "applicable": True, "missing_games": [],
                                  "error": str(e)})

    total_prop_gaps = sum(len(r["missing_games"]) for r in prop_results if r["applicable"])
    subject_prefix = "🚨 " if (total_mismatches or total_prop_gaps) else ""
    subject = (f"{subject_prefix}Data Integrity Report {target_date} — "
               f"{total_mismatches} games mismatch(es), {total_prop_gaps} prop gap(s)")
    html = _build_html(games_results, prop_results, target_date)

    ok, err = EmailService.send_digest_to_one(REPORT_RECIPIENT, subject, html)
    if ok:
        print(f"[integrity-report] Sent to {REPORT_RECIPIENT}")
    else:
        print(f"[integrity-report] Failed to send: {err}")
```

- [ ] **Step 5: Run it end-to-end and confirm the email arrives**

Run: `cd /Users/stephaniegillen/Projects/get-stam-py && python jobs/send_data_integrity_report.py`

Expected: console shows games-count lines, then prop-gap counts for NBA/NFL/MLB/NHL, then `[integrity-report] Sent to getstaminc@gmail.com`. Check that inbox for the email and visually confirm both tables render (counts table + any mismatch detail + prop gap tables).

- [ ] **Step 6: Commit**

```bash
git add jobs/send_data_integrity_report.py
git commit -m "feat: add player-prop completeness check and email delivery to integrity report"
```

---

### Task 3: Verify from Heroku and schedule it

**Files:** none (operational verification + manual dashboard step)

**Interfaces:** none — this task consumes the finished job from Tasks 1–2 as-is.

- [ ] **Step 1: Deploy and run once via `heroku run` to confirm ESPN isn't blocked from Heroku's IPs for the three new sports/slugs**

Run: `heroku run python jobs/send_data_integrity_report.py --app get-stam`

Expected: same console output shape as the local run in Task 2 Step 5, specifically with non-error lines for `NCAAF`, `NCAAB`, `EPL`, `La Liga`, `Bundesliga`, `Ligue 1`, `Serie A`, and `UCL` — these are the slugs never previously called from Heroku. If any of those show a `[integrity-report] <Sport> error (non-fatal): ...` with a 403/blocked response, note which sport(s) and stop here — that's a real finding to bring back before scheduling (ESPN may need a different code path for that sport, same as the roster-endpoint block already documented in `jobs/nfl_daily_player_team_assignment_job.py`).

- [ ] **Step 2: Add the Heroku Scheduler job via the dashboard**

Open Heroku Dashboard → `get-stam` → Resources → Heroku Scheduler → "Add Job". Command: `python jobs/send_data_integrity_report.py`. Frequency: Daily. Pick a time *after* the existing seed jobs' scheduled run times (open each existing seed job's entry in the same Scheduler UI to see what time they're set to run, and set this one at least 30 minutes after the latest of them) — this is a manual step since no `app.json` scheduler config exists in this repo for any job.

- [ ] **Step 3: Confirm the first scheduled run produced an email**

The next morning, check `getstaminc@gmail.com` for the "Data Integrity Report" email. No code change or commit for this task — it's operational verification only.

---

## Self-Review Notes

- **Spec coverage:** games-count check (all 12 entries) → Task 1. Prop-completeness check (NBA/NFL/MLB/NHL, both join modes from the spec) → Task 2. Email delivery via `EmailService.send_digest_to_one`, single recipient, failure-prefixed subject → Task 2 Step 4. Heroku scheduling + the ESPN-from-Heroku risk called out in the spec → Task 3.
- **Placeholder scan:** no TBD/TODO; every step has runnable code or a concrete manual action with a stated expected result.
- **Type consistency:** `SPORTS_CONFIG` entries keep the same keys across Tasks 1–2 (`key`, `display`, `espn_slug`, `espn_final_statuses`, `espn_extra_params`, `table`, `date_col`, `league_filter`, and optionally `prop_check`). `_check_games_count` and `_check_prop_completeness` both take `(engine, cfg, target_date, ...)` consistently. `_build_html` in Task 2 takes exactly the two result lists produced by `run()`'s loops in Tasks 1–2.
