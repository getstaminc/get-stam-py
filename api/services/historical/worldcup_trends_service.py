"""World Cup Trends Service — queries international_soccer_games table."""

from typing import Dict, List, Set, Tuple
from psycopg2.extras import RealDictCursor
from .soccer_trends_service import SoccerTrendsService
from .worldcup_service import WorldcupService


class WorldcupTrendsService(SoccerTrendsService):
    """Trend analysis for World Cup games using international_soccer_games."""

    @classmethod
    def _get_team_id_mapping(cls, teams):
        """Get team IDs from the INTL_SOCCER sport."""
        conn = None
        try:
            conn = WorldcupService._get_connection()
            if not conn:
                return {}
            team_names = list(teams)
            placeholders = ','.join(['%s'] * len(team_names))
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT team_name, team_id FROM teams "
                    f"WHERE team_name IN ({placeholders}) AND sport = 'INTL_SOCCER'",
                    team_names
                )
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            print(f"Error getting worldcup team ID mapping: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    @classmethod
    def _batch_fetch_all_team_games(cls, teams, limit, league=None):
        """Fetch team games from international_soccer_games."""
        conn = None
        try:
            conn = WorldcupService._get_connection()
            if not conn:
                return {}

            team_names = list(teams)
            placeholders = ','.join(['%s'] * len(team_names))
            query = f"""
                SELECT
                    game_id, game_date, home_team_name, home_team_id,
                    away_team_name, away_team_id,
                    home_goals, away_goals, total_goals,
                    home_spread, away_spread,
                    home_money_line, draw_money_line, away_money_line,
                    start_time, total_over_point, total_over_price,
                    total_under_point, total_under_price, league
                FROM international_soccer_games
                WHERE (home_team_name IN ({placeholders}) OR away_team_name IN ({placeholders}))
                ORDER BY game_date DESC
            """

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, team_names + team_names)
                all_games = cursor.fetchall()

            team_games = {team: [] for team in teams}

            for game in all_games:
                g = dict(game)
                if g['home_team_name'] in team_games:
                    gw = dict(g)
                    gw['team_side'] = 'home'
                    team_games[g['home_team_name']].append(gw)
                if g['away_team_name'] in team_games:
                    gw = dict(g)
                    gw['team_side'] = 'away'
                    team_games[g['away_team_name']].append(gw)

            for team in team_games:
                team_games[team] = sorted(
                    team_games[team], key=lambda x: x['game_date'], reverse=True
                )[:limit]

            print(f"Batch fetched worldcup games for {len(team_games)} teams")
            return team_games

        except Exception as e:
            print(f"Error batch fetching worldcup team games: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    @classmethod
    def _batch_fetch_all_head_to_head_games(cls, team_pairs, limit):
        """Fetch H2H games from international_soccer_games."""
        conn = None
        try:
            all_teams = set()
            for home, away in team_pairs:
                all_teams.add(home)
                all_teams.add(away)

            team_id_map = cls._get_team_id_mapping(all_teams)

            conn = WorldcupService._get_connection()
            if not conn:
                return {}

            h2h_conditions = []
            params = []
            valid_pairs = []

            for home_team, away_team in team_pairs:
                home_id = team_id_map.get(home_team)
                away_id = team_id_map.get(away_team)
                if home_id and away_id:
                    h2h_conditions.append(
                        "(home_team_id = %s AND away_team_id = %s) OR "
                        "(home_team_id = %s AND away_team_id = %s)"
                    )
                    params.extend([home_id, away_id, away_id, home_id])
                    valid_pairs.append((home_team, away_team))

            h2h_results = {pair: [] for pair in team_pairs}

            if h2h_conditions:
                query = f"""
                    SELECT
                        game_id, game_date, home_team_name, away_team_name,
                        home_goals, away_goals, total_goals,
                        home_spread, away_spread,
                        home_money_line, draw_money_line, away_money_line,
                        start_time, total_over_point, total_over_price,
                        total_under_point, total_under_price,
                        home_team_id, away_team_id
                    FROM international_soccer_games
                    WHERE ({' OR '.join(h2h_conditions)})
                    ORDER BY game_date DESC
                """
                reverse_id_map = {v: k for k, v in team_id_map.items()}

                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    all_h2h = cursor.fetchall()

                for game in all_h2h:
                    g = dict(game)
                    g['home_team_orig'] = reverse_id_map.get(g['home_team_id'])
                    g['away_team_orig'] = reverse_id_map.get(g['away_team_id'])
                    for home, away in valid_pairs:
                        if ((g['home_team_orig'] == home and g['away_team_orig'] == away) or
                                (g['home_team_orig'] == away and g['away_team_orig'] == home)):
                            if len(h2h_results[(home, away)]) < limit:
                                h2h_results[(home, away)].append(g)
                            break

            print(f"Batch fetched worldcup H2H for {len(team_pairs)} pairs")
            return h2h_results

        except Exception as e:
            print(f"Error batch fetching worldcup H2H games: {e}")
            return {}
        finally:
            if conn:
                conn.close()
