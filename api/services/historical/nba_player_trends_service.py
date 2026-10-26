"""Service for computing NBA player prop over/under streaks (actual vs line).

Mirrors nfl_player_trends_service.py's algorithm (active-run detection +
historical continuation rate), adapted to nba_player_props' schema: team name
already lives on the props row (player_team_name, already Odds-API format —
no teams-table join needed), and player display name comes from a join to
nba_players (nba_player_props only carries the lowercase normalized_name).

Reuses the existing SQLAlchemy engine/retry helper in player_props_service.py
rather than opening a second connection pool against the same table family.
"""

from collections import defaultdict
from ..player_props_service import execute_with_retry

# Number of most-recent games per player scanned for an active run.
RECENT_GAMES_WINDOW = 20

# Minimum prior occurrences of a streak before its continuation rate is worth
# showing — below this the rate is noise (0/1, 0/2) dressed up as a percentage.
MIN_CONTINUATION_SAMPLE = 5

# stat key -> (actual column, odds/line column)
STAT_COLUMNS = {
    "points":   ("actual_player_points",   "odds_player_points"),
    "rebounds": ("actual_player_rebounds", "odds_player_rebounds"),
    "assists":  ("actual_player_assists",  "odds_player_assists"),
    "threes":   ("actual_player_threes",   "odds_player_threes"),
}

_ALL_STAT_COLS = [c for pair in STAT_COLUMNS.values() for c in pair]
_ACTUAL_COLS = [a for a, _ in STAT_COLUMNS.values()]


def _to_float(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _direction(actual, line):
    """'over' | 'under' | None (push / missing data)."""
    a, l = _to_float(actual), _to_float(line)
    if a is None or l is None:
        return None
    if a > l:
        return "over"
    if a < l:
        return "under"
    return None  # push breaks the run


class NBAPlayerTrendsService:

    def get_player_streaks(self, team_names=None, min_streak=3):
        """
        Return active over/under streaks for NBA players — consecutive recent games
        where a player's actual stat landed on the same side of their prop line —
        with a historical continuation rate per player per (stat, direction).

        team_names: optional list of Odds API full team names.
        min_streak: minimum consecutive games on the same side (default 3).

        Returns dict keyed by player_team_name:
            {
              "Charlotte Hornets": [
                {
                  "player_id": int,
                  "player_name": str,
                  "stat": "points" | "rebounds" | "assists" | "threes",
                  "direction": "over" | "under",
                  "streak_count": int,
                  "line": float,                       # line in the most recent game of the run
                  "continuation_rate": float | None,   # 0-1
                  "sample_size": int | None,
                }
              ]
            }
        """
        params = {"window": RECENT_GAMES_WINDOW}
        team_filter = ""
        if team_names:
            team_params = {f"team{i}": name for i, name in enumerate(team_names)}
            placeholders = ", ".join(f":{k}" for k in team_params)
            team_filter = f"AND pp.player_team_name IN ({placeholders})"
            params.update(team_params)

        stat_select = ", ".join(_ALL_STAT_COLS)
        actual_coalesce = ", ".join(_ACTUAL_COLS)
        recent_sql = f"""
            SELECT player_id, team_name, player_name, game_date, {stat_select}
            FROM (
                SELECT
                    pp.player_id,
                    pp.player_team_name AS team_name,
                    np.player_name,
                    pp.game_date,
                    {", ".join('pp.' + c for c in _ALL_STAT_COLS)},
                    ROW_NUMBER() OVER (
                        PARTITION BY pp.player_id ORDER BY pp.game_date DESC, pp.id DESC
                    ) AS rn
                FROM nba_player_props pp
                JOIN nba_players np ON np.id = pp.player_id
                WHERE pp.did_not_play IS NOT TRUE
                  AND COALESCE({', '.join('pp.' + c for c in _ACTUAL_COLS)}) IS NOT NULL
                  {team_filter}
            ) ranked
            WHERE rn <= :window
            ORDER BY player_id, game_date DESC
        """
        recent_rows = execute_with_retry(recent_sql, params)

        # ── Group recent games per player (already DESC by date) ──────────────
        players = defaultdict(list)
        player_meta = {}
        col_index = {c: 4 + i for i, c in enumerate(_ALL_STAT_COLS)}
        for row in recent_rows:
            player_id, team_name, player_name, game_date = row[0], row[1], row[2], row[3]
            game = {}
            for stat, (actual_col, line_col) in STAT_COLUMNS.items():
                game[stat] = (row[col_index[actual_col]], row[col_index[line_col]])
            players[player_id].append(game)
            player_meta.setdefault(player_id, {"player_name": player_name, "team_name": team_name})

        # ── Compute current runs ─────────────────────────────────────────────
        active_streaks = []  # (player_id, stat, direction, streak_count, line)
        for player_id, games in players.items():
            for stat in STAT_COLUMNS:
                run_dir = None
                run_len = 0
                run_line = None
                for actual, line in (g[stat] for g in games):
                    d = _direction(actual, line)
                    if d is None:
                        break
                    if run_dir is None:
                        run_dir, run_line = d, _to_float(line)
                        run_len = 1
                    elif d == run_dir:
                        run_len += 1
                    else:
                        break
                if run_dir is None or run_len < min_streak:
                    continue
                active_streaks.append((player_id, stat, run_dir, run_len, run_line))

        if not active_streaks:
            return {}

        # ── Full history for those players → continuation rates ───────────────
        player_ids = list({pid for pid, *_ in active_streaks})
        rates = self._compute_continuation_rates(player_ids, active_streaks)

        # ── Assemble result ──────────────────────────────────────────────────
        result = defaultdict(list)
        for player_id, stat, direction, streak_count, line in active_streaks:
            meta = player_meta[player_id]
            continued, total = rates.get((player_id, stat, direction, streak_count), (None, None))
            has_rate = bool(total) and total >= MIN_CONTINUATION_SAMPLE
            result[meta["team_name"]].append({
                "player_id": player_id,
                "player_name": meta["player_name"],
                "stat": stat,
                "direction": direction,
                "streak_count": streak_count,
                "line": line,
                "continuation_rate": round(continued / total, 3) if has_rate else None,
                "sample_size": total if has_rate else None,
            })

        for team_name in result:
            result[team_name].sort(
                key=lambda x: (
                    -x["streak_count"],
                    x["continuation_rate"] is None,          # None rates last
                    -(x["continuation_rate"] or 0),
                )
            )

        return dict(result)

    def _compute_continuation_rates(self, player_ids, active_streaks):
        """
        For each (player_id, stat, direction, streak_count) in active_streaks, scan
        the player's full history and compute how often a run of that length on that
        side of the line continued in the next game.

        Returns dict: (player_id, stat, direction, streak_count) -> (continued, total)
        """
        if not player_ids:
            return {}

        id_params = {f"pid{i}": pid for i, pid in enumerate(player_ids)}
        placeholders = ", ".join(f":{k}" for k in id_params)
        sql = f"""
            SELECT pp.player_id, {", ".join('pp.' + c for c in _ALL_STAT_COLS)}
            FROM nba_player_props pp
            WHERE pp.did_not_play IS NOT TRUE
              AND pp.player_id IN ({placeholders})
              AND COALESCE({', '.join('pp.' + c for c in _ACTUAL_COLS)}) IS NOT NULL
            ORDER BY pp.player_id, pp.game_date ASC, pp.id ASC
        """
        rows = execute_with_retry(sql, id_params)

        col_index = {c: 1 + i for i, c in enumerate(_ALL_STAT_COLS)}
        player_games = defaultdict(list)
        for row in rows:
            pid = row[0]
            game = {}
            for stat, (actual_col, line_col) in STAT_COLUMNS.items():
                game[stat] = (row[col_index[actual_col]], row[col_index[line_col]])
            player_games[pid].append(game)

        results = {}
        seen = set()
        for player_id, stat, direction, threshold, _line in active_streaks:
            key = (player_id, stat, direction, threshold)
            if key in seen:
                continue
            seen.add(key)

            games = player_games.get(player_id, [])
            run = 0
            continued = 0
            total = 0
            for i, g in enumerate(games):
                d = _direction(*g[stat])
                if d == direction:
                    run += 1
                    if run == threshold and i + 1 < len(games):
                        total += 1
                        if _direction(*games[i + 1][stat]) == direction:
                            continued += 1
                else:
                    run = 0

            results[key] = (continued, total) if total > 0 else (None, None)

        return results
