"""Service for computing active MLB batter hit/HR/RBI streaks."""

from collections import defaultdict
from .base_service import BaseHistoricalService

MIN_COVER_STREAK = 5


class MLBPlayerTrendsService(BaseHistoricalService):

    def get_batter_streaks(self, team_names=None, min_streak=5):
        """
        Return active hit/HR/RBI streaks and prop-cover streaks for batters,
        with historical continuation rates per player per streak type.

        team_names: optional list of Odds API full team names.
        min_streak: minimum consecutive 1+ games required (default 5).
                    Cover streaks use MIN_COVER_STREAK (3).

        Returns dict keyed by player_team_name:
            {
              "New York Yankees": [
                {
                  "player_name": str,
                  "stat": "hits" | "hits_cover" | ...,
                  "streak_count": int,
                  "line": float | None,           # cover streaks only
                  "continuation_rate": float | None,  # 0-1
                  "sample_size": int | None,
                }
              ]
            }
        """
        conn = self._get_connection()
        if conn is None:
            return {}

        try:
            with conn:
                with conn.cursor() as cur:
                    # ── Step 1: recent games to find current streaks ──────────
                    base_sql = """
                        SELECT
                            bp.player_id,
                            bp.player_team_name,
                            p.player_name,
                            bp.game_date,
                            bp.actual_batter_hits,
                            bp.actual_batter_home_runs,
                            bp.actual_batter_rbi,
                            bp.odds_batter_hits,
                            bp.odds_batter_home_runs,
                            bp.odds_batter_rbi
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
                    recent_rows = cur.fetchall()

        finally:
            conn.close()

        # ── Build recent game groups ──────────────────────────────────────────
        players: dict = defaultdict(list)
        player_meta: dict = {}
        for row in recent_rows:
            (player_id, team_name, player_name, game_date,
             hits, hrs, rbi,
             hits_line, hr_line, rbi_line) = row
            players[player_id].append({
                "hits": hits, "hr": hrs, "rbi": rbi,
                "hits_line": float(hits_line) if hits_line is not None else None,
                "hr_line":   float(hr_line)   if hr_line   is not None else None,
                "rbi_line":  float(rbi_line)  if rbi_line  is not None else None,
            })
            if player_id not in player_meta:
                player_meta[player_id] = {"player_name": player_name, "team_name": team_name}

        # ── Compute current streaks ───────────────────────────────────────────
        active_streaks: list[tuple] = []   # (player_id, stat, streak_count, line)

        for player_id, game_rows in players.items():
            meta = player_meta[player_id]

            # 1+ streaks
            for stat in ("hits", "hr", "rbi"):
                streak = 0
                for game in game_rows:
                    val = game[stat]
                    if val is not None and val >= 1:
                        streak += 1
                    else:
                        break
                if streak >= min_streak:
                    active_streaks.append((player_id, stat, streak, None))

            # Cover streaks
            for stat, line_key in [("hits", "hits_line"), ("hr", "hr_line"), ("rbi", "rbi_line")]:
                streak = 0
                current_line = None
                for game in game_rows:
                    actual = game[stat]
                    line = game[line_key]
                    if actual is not None and line is not None and actual > line:
                        streak += 1
                        if current_line is None:
                            current_line = line
                    else:
                        break
                if streak >= MIN_COVER_STREAK:
                    active_streaks.append((player_id, f"{stat}_cover", streak, current_line))

        if not active_streaks:
            return {}

        # ── Step 2: full history for those players to compute rates ───────────
        unique_player_ids = list({pid for pid, _, _, _ in active_streaks})
        rates = self._compute_continuation_rates(unique_player_ids, active_streaks)

        # ── Assemble result ───────────────────────────────────────────────────
        result: dict = defaultdict(list)

        for player_id, stat, streak_count, line in active_streaks:
            meta = player_meta[player_id]
            continued, total = rates.get((player_id, stat, streak_count), (None, None))
            entry = {
                "player_name": meta["player_name"],
                "stat": stat,
                "streak_count": streak_count,
                "continuation_rate": round(continued / total, 3) if total else None,
                "sample_size": total if total else None,
            }
            if line is not None:
                entry["line"] = line
            result[meta["team_name"]].append(entry)

        for team_name in result:
            result[team_name].sort(
                key=lambda x: (
                    -x["streak_count"],
                    x["continuation_rate"] is None,   # None rates last
                    -(x["continuation_rate"] or 0),
                )
            )

        return dict(result)

    def _compute_continuation_rates(self, player_ids, active_streaks):
        """
        For each (player_id, stat, streak_count) in active_streaks, query the
        player's full history and compute how often a streak of that length
        continued in the next game.

        Returns dict: (player_id, stat, streak_count) -> (continued, total)
        """
        conn = self._get_connection()
        if conn is None:
            return {}

        try:
            with conn:
                with conn.cursor() as cur:
                    placeholders = ", ".join(["%s"] * len(player_ids))
                    sql = f"""
                        SELECT
                            bp.player_id,
                            bp.actual_batter_hits,
                            bp.actual_batter_home_runs,
                            bp.actual_batter_rbi,
                            bp.odds_batter_hits,
                            bp.odds_batter_home_runs,
                            bp.odds_batter_rbi
                        FROM mlb_batter_props bp
                        WHERE bp.did_not_play IS NOT TRUE
                          AND bp.player_id IN ({placeholders})
                          AND (
                              bp.actual_batter_hits IS NOT NULL
                              OR bp.actual_batter_home_runs IS NOT NULL
                              OR bp.actual_batter_rbi IS NOT NULL
                          )
                        ORDER BY bp.player_id, bp.game_date ASC
                    """
                    cur.execute(sql, player_ids)
                    rows = cur.fetchall()
        finally:
            conn.close()

        # Group by player (ASC order = chronological)
        player_games: dict = defaultdict(list)
        for row in rows:
            (player_id, hits, hrs, rbi, hits_line, hr_line, rbi_line) = row
            player_games[player_id].append({
                "hits": hits, "hr": hrs, "rbi": rbi,
                "hits_line": float(hits_line) if hits_line is not None else None,
                "hr_line":   float(hr_line)   if hr_line   is not None else None,
                "rbi_line":  float(rbi_line)  if rbi_line  is not None else None,
            })

        results = {}
        # Dedupe: same player+stat+threshold may appear multiple times
        seen = set()
        for player_id, stat, threshold, _line in active_streaks:
            key = (player_id, stat, threshold)
            if key in seen:
                continue
            seen.add(key)

            games = player_games.get(player_id, [])
            if len(games) < threshold + 1:
                results[key] = (None, None)
                continue

            is_cover = stat.endswith("_cover")
            base_stat = stat.replace("_cover", "") if is_cover else stat
            line_key = f"{base_stat}_line"

            def hit(game):
                if is_cover:
                    v, l = game[base_stat], game[line_key]
                    return v is not None and l is not None and v > l
                else:
                    v = game[base_stat]
                    return v is not None and v >= 1

            # Build running streak for each game position
            streaks = []
            current = 0
            for g in games:
                current = current + 1 if hit(g) else 0
                streaks.append(current)

            # Count instances where streak == threshold and check continuation
            continued = 0
            total = 0
            for i in range(len(streaks) - 1):
                if streaks[i] == threshold:
                    total += 1
                    if hit(games[i + 1]):
                        continued += 1

            results[key] = (continued, total) if total > 0 else (None, None)

        return results
