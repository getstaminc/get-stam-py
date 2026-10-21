"""Read/write access to cached opening-line snapshots for line-movement display.
Snapshots are captured once per game by jobs/capture_opening_lines.py — this service
never calls the Odds API itself, only the database."""

import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")


def _get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


class OpeningLinesService:

    @staticmethod
    def get_opening_lines(sport, event_ids):
        """Batch-fetch opening lines for the given event ids.
        Returns {odds_event_id: row_dict} for whichever ids have a captured row."""
        event_ids = [e for e in event_ids if e]
        if not event_ids:
            return {}
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT odds_event_id, home_spread_point, home_spread_price,
                           away_spread_point, away_spread_price, home_moneyline,
                           away_moneyline, total_point, over_price, under_price,
                           opening_snapshot_time
                    FROM game_opening_lines
                    WHERE sport = %s AND odds_event_id = ANY(%s)
                    """,
                    (sport, event_ids),
                )
                rows = cur.fetchall()
        return {row["odds_event_id"]: row for row in rows}

    @staticmethod
    def has_opening_line(sport, event_id):
        """True if an opening line has already been captured for this event."""
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM game_opening_lines WHERE sport = %s AND odds_event_id = %s",
                    (sport, event_id),
                )
                return cur.fetchone() is not None

    @staticmethod
    def save_opening_line(sport, event_id, home_team, away_team, commence_time,
                           opening_snapshot_time, markets):
        """Insert a captured opening line. Write-once: does nothing if a row for
        (sport, event_id) already exists."""
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO game_opening_lines (
                        sport, odds_event_id, home_team, away_team, commence_time,
                        opening_snapshot_time, home_spread_point, home_spread_price,
                        away_spread_point, away_spread_price, home_moneyline,
                        away_moneyline, total_point, over_price, under_price
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (sport, odds_event_id) DO NOTHING
                    """,
                    (
                        sport, event_id, home_team, away_team, commence_time,
                        opening_snapshot_time,
                        markets.get("home_spread_point"), markets.get("home_spread_price"),
                        markets.get("away_spread_point"), markets.get("away_spread_price"),
                        markets.get("home_moneyline"), markets.get("away_moneyline"),
                        markets.get("total_point"), markets.get("over_price"),
                        markets.get("under_price"),
                    ),
                )
            conn.commit()
