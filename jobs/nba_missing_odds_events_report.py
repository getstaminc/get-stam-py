#!/usr/bin/python3

import os
import sys
import requests
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", 'e143ef401675904470a5b72e6145091a')

def get_historical_nba_events(target_date: date):
    """
    Get all NBA event IDs for a specific historical date.
    """
    date_str = target_date.strftime('%Y-%m-%d')
    url = f"https://api.the-odds-api.com/v4/historical/sports/basketball_nba/events"
    params = {
        'apiKey': ODDS_API_KEY,
        'date': f"{date_str}T12:00:00Z"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        events_data = response.json()
        if isinstance(events_data, dict) and 'data' in events_data:
            events = events_data['data']
        elif isinstance(events_data, list):
            events = events_data
        else:
            print(f"  Unexpected API response format: {type(events_data)}")
            return []
        return events
    except Exception as e:
        print(f"  Error fetching events for {target_date}: {e}")
        return []

def check_event_in_db(conn, event_id):
    result = conn.execute(text("""
        SELECT COUNT(*) FROM nba_player_props WHERE odds_event_id = :event_id
    """), {'event_id': event_id})
    count = result.scalar()
    return count > 0

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 jobs/nba_missing_odds_events_report.py START_DATE END_DATE")
        print("Example: python3 jobs/nba_missing_odds_events_report.py 2025-10-22 2025-10-25")
        sys.exit(1)
    start_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    end_date = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        current_date = start_date
        missing_events = []
        while current_date <= end_date:
            events = get_historical_nba_events(current_date)
            for event in events:
                event_id = event.get('id')
                if not event_id:
                    continue
                if not check_event_in_db(conn, event_id):
                    missing_events.append({'date': current_date, 'event_id': event_id, 'home_team': event.get('home_team'), 'away_team': event.get('away_team')})
            current_date += timedelta(days=1)
        if missing_events:
            print("\nMissing NBA Odds Events (not in nba_player_props):")
            for evt in missing_events:
                print(f"Date: {evt['date']} | Event ID: {evt['event_id']} | {evt['away_team']} at {evt['home_team']}")
        else:
            print("All events found in nba_player_props for the given date range.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
