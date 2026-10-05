#!/usr/bin/env python3
"""
Check whether a daily player-props import log exists for a given date, and
email an alert if it doesn't -- meaning that day's scheduled run never fired
at all (e.g. the Mac was asleep straight through it), not just failed.

Called from scripts/{mlb,nfl}_daily_import.sh right before each day's run,
checking the date from two days before "today" (the day whose own run should
already have produced a log file by now).

Usage: check_missed_import.py <sport> <date YYYY-MM-DD> <log_dir>
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def main():
    if len(sys.argv) != 4:
        print("usage: check_missed_import.py <sport> <date> <log_dir>", file=sys.stderr)
        sys.exit(1)

    sport, check_date, log_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    log_path = os.path.join(log_dir, f"{sport}_daily_import_{check_date}.log")

    if os.path.exists(log_path):
        return  # that day ran, nothing to report

    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

    from api.services.email_service import EmailService

    alert_email = os.getenv("ALERT_EMAIL", "sgillen77@gmail.com")
    subject = f"⚠️ {sport.upper()} daily import skipped for {check_date}"
    html = f"""
        <p>No log file was ever created for the <b>{sport}</b> daily import
        targeting <b>{check_date}</b> ({log_path}).</p>
        <p>This means the scheduled run never fired that morning at all
        (most likely the Mac was asleep straight through it) -- not that it
        ran and failed.</p>
        <p>Backfill it with:</p>
        <pre>python jobs/{sport}_historical_import_orchestrator_reverse.py {check_date} {check_date}</pre>
    """
    ok, err = EmailService.send_digest_to_one(alert_email, subject, html)
    print(f"[alert] missed {sport} day {check_date} -- email {'sent' if ok else 'FAILED: ' + str(err)}")


if __name__ == "__main__":
    main()
