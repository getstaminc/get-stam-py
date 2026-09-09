"""Service for computing NFL player prop over/under streaks (actual vs line)."""

from collections import defaultdict
from .base_service import BaseHistoricalService

# Number of most-recent games per player scanned for an active run.
RECENT_GAMES_WINDOW = 20

# stat key -> (actual column, odds/line column)
STAT_COLUMNS = {
    "pass_yds":      ("actual_player_pass_yds",      "odds_player_pass_yds"),
    "pass_tds":      ("actual_player_pass_tds",      "odds_player_pass_tds"),
    "rush_yds":      ("actual_player_rush_yds",      "odds_player_rush_yds"),
    "reception_yds": ("actual_player_reception_yds", "odds_player_reception_yds"),
    "anytime_td":    ("actual_player_anytime_td",    "odds_player_anytime_td"),
}

# anytime_td "under" (a player NOT scoring) is the default state for most of the
# roster, so an under run there is noise — only a scoring run is meaningful. Yardage
# and pass-TD props carry signal in both directions (a player consistently under
# their line matters as much as over).
OVER_ONLY_STATS = {"anytime_td"}

_ACTUAL_COLS = [a for a, _ in STAT_COLUMNS.values()]
_LINE_COLS = [l for _, l in STAT_COLUMNS.values()]
_ALL_STAT_COLS = _ACTUAL_COLS + _LINE_COLS


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


class NFLPlayerTrendsService(BaseHistoricalService):

    def get_player_streaks(self, team_names=None, min_streak=3):
        """
        Return active over/under streaks for NFL players — consecutive recent games
        where a player's actual stat landed on the same side of their prop line —
        with a historical continuation rate per player per (stat, direction).

        team_names: optional list of Odds API full team names.
        min_streak: minimum consecutive games on the same side (default 3).

        Returns dict keyed by player_team_name:
            {
              "Cincinnati Bengals": [
                {
                  "player_name": str,
                  "stat": "pass_yds" | "pass_tds" | "rush_yds" | "reception_yds" | "anytime_td",
                  "direction": "over" | "under",
                  "streak_count": int,
                  "line": float,                       # line in the most recent game of the run
                  "continuation_rate": float | None,   # 0-1
                  "sample_size": int | None,
                }
              ]
            }
        """
        conn = self._get_connection()
        if conn is None:
            return {}

        select_cols = ", ".join(f"pp.{c}" for c in _ALL_STAT_COLS)
        try:
            with conn:
                with conn.cursor() as cur:
                    # ── Step 1: recent games (last N per player) to find current runs ──
                    # Team comes from nfl_players.team_id (kept current by
                    # jobs/nfl_daily_player_team_assignment_job.py) -> teams.odds_api_team_name,
                    # falling back to the prop row's player_team_name for players with no
                    # team_id yet. Filtering on the stale player_team_name alone put e.g. a
                    # traded player's old-team streaks under his old team.
                    params = []
                    team_filter = ""
                    if team_names:
                        ph = ", ".join(["%s"] * len(team_names))
                        team_filter = (
                            f"AND (t.odds_api_team_name IN ({ph}) "
                            f"OR (p.team_id IS NULL AND pp.player_team_name IN ({ph})))"
                        )
                        params.extend(team_names)
                        params.extend(team_names)

                    recent_sql = f"""
                        SELECT player_id, team_name, player_name, game_date,
                               {", ".join(_ALL_STAT_COLS)}
                        FROM (
                            SELECT
                                pp.player_id,
                                COALESCE(t.odds_api_team_name, pp.player_team_name) AS team_name,
                                p.player_name,
                                pp.game_date,
                                {select_cols},
                                ROW_NUMBER() OVER (
                                    PARTITION BY pp.player_id ORDER BY pp.game_date DESC, pp.id DESC
                                ) AS rn
                            FROM nfl_player_props pp
                            JOIN nfl_players p ON p.id = pp.player_id
                            LEFT JOIN teams t ON t.team_id = p.team_id AND t.sport = 'NFL'
                            WHERE pp.did_not_play IS NOT TRUE
                              -- drop rows with odds but no actuals (unplayed / not-yet-imported
                              -- games, e.g. a future slate) so they can't head the recent window
                              AND COALESCE(
                                    pp.actual_player_pass_yds, pp.actual_player_pass_tds,
                                    pp.actual_player_rush_yds, pp.actual_player_reception_yds,
                                    pp.actual_player_receptions
                                  ) IS NOT NULL
                              {team_filter}
                        ) ranked
                        WHERE rn <= %s
                        ORDER BY player_id, game_date DESC
                    """
                    cur.execute(recent_sql, params + [RECENT_GAMES_WINDOW])
                    recent_rows = cur.fetchall()
        finally:
            conn.close()

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
                if stat in OVER_ONLY_STATS and run_dir != "over":
                    continue
                active_streaks.append((player_id, stat, run_dir, run_len, run_line))

        if not active_streaks:
            return {}

        # ── Step 2: full history for those players → continuation rates ───────
        player_ids = list({pid for pid, *_ in active_streaks})
        rates = self._compute_continuation_rates(player_ids, active_streaks)

        # ── Assemble result ──────────────────────────────────────────────────
        result = defaultdict(list)
        for player_id, stat, direction, streak_count, line in active_streaks:
            meta = player_meta[player_id]
            continued, total = rates.get((player_id, stat, direction, streak_count), (None, None))
            result[meta["team_name"]].append({
                "player_name": meta["player_name"],
                "stat": stat,
                "direction": direction,
                "streak_count": streak_count,
                "line": line,
                "continuation_rate": round(continued / total, 3) if total else None,
                "sample_size": total if total else None,
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
        conn = self._get_connection()
        if conn is None:
            return {}

        try:
            with conn:
                with conn.cursor() as cur:
                    placeholders = ", ".join(["%s"] * len(player_ids))
                    sql = f"""
                        SELECT pp.player_id, {", ".join('pp.' + c for c in _ALL_STAT_COLS)}
                        FROM nfl_player_props pp
                        WHERE pp.did_not_play IS NOT TRUE
                          AND pp.player_id IN ({placeholders})
                          AND COALESCE(
                                pp.actual_player_pass_yds, pp.actual_player_pass_tds,
                                pp.actual_player_rush_yds, pp.actual_player_reception_yds,
                                pp.actual_player_receptions
                              ) IS NOT NULL
                        ORDER BY pp.player_id, pp.game_date ASC, pp.id ASC
                    """
                    cur.execute(sql, player_ids)
                    rows = cur.fetchall()
        finally:
            conn.close()

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
            # Running count of consecutive games on `direction`; reset on the other
            # side or on a push/missing game.
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
