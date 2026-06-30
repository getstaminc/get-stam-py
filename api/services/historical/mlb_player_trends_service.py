"""Service for computing active MLB batter hit/HR/RBI streaks."""

from collections import defaultdict
from .base_service import BaseHistoricalService


class MLBPlayerTrendsService(BaseHistoricalService):

    def get_batter_streaks(self, team_names=None, min_streak=5):
        """
        Return active hit/HR/RBI streaks for batters.

        team_names: optional list of Odds API full team names (e.g. "New York Yankees").
        min_streak: minimum consecutive games required (default 5).

        Returns dict keyed by player_team_name:
            { "New York Yankees": [{"player_name": str, "stat": str, "streak_count": int}] }
        """
        conn = self._get_connection()
        if conn is None:
            return {}

        try:
            with conn:
                with conn.cursor() as cur:
                    base_sql = """
                        SELECT
                            bp.player_id,
                            bp.player_team_name,
                            p.player_name,
                            bp.game_date,
                            bp.actual_batter_hits,
                            bp.actual_batter_home_runs,
                            bp.actual_batter_rbi
                        FROM mlb_batter_props bp
                        JOIN mlb_players p ON p.id = bp.player_id
                        WHERE bp.did_not_play IS NOT TRUE
                          AND bp.game_date >= NOW() - INTERVAL '45 days'
                          AND (
                              bp.actual_batter_hits IS NOT NULL
                              OR bp.actual_batter_home_runs IS NOT NULL
                              OR bp.actual_batter_rbi IS NOT NULL
                          )
                    """
                    params = []
                    if team_names:
                        placeholders = ", ".join(["%s"] * len(team_names))
                        base_sql += f" AND bp.player_team_name IN ({placeholders})"
                        params.extend(team_names)

                    base_sql += " ORDER BY bp.player_id, bp.game_date DESC"

                    cur.execute(base_sql, params)
                    rows = cur.fetchall()
        finally:
            conn.close()

        # Group by player_id
        players: dict = defaultdict(list)
        player_meta: dict = {}
        for row in rows:
            (player_id, team_name, player_name, game_date,
             hits, hrs, rbi) = row
            players[player_id].append({
                "hits": hits,
                "hr": hrs,
                "rbi": rbi,
            })
            if player_id not in player_meta:
                player_meta[player_id] = {
                    "player_name": player_name,
                    "team_name": team_name,
                }

        result: dict = defaultdict(list)

        for player_id, game_rows in players.items():
            meta = player_meta[player_id]
            team_name = meta["team_name"]
            player_name = meta["player_name"]

            for stat in ("hits", "hr", "rbi"):
                streak = 0
                for game in game_rows:  # already sorted DESC (most recent first)
                    val = game[stat]
                    if val is not None and val >= 1:
                        streak += 1
                    else:
                        break

                if streak >= min_streak:
                    result[team_name].append({
                        "player_name": player_name,
                        "stat": stat,
                        "streak_count": streak,
                    })

        # Sort each team's streaks by streak_count descending
        for team_name in result:
            result[team_name].sort(key=lambda x: x["streak_count"], reverse=True)

        return dict(result)
