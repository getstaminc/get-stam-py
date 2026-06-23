"""
Trend context service — for H2H streaks found in the digest, find every historical
instance where any matchup reached that streak length and report what happened next.

E.g. "Total went OVER 6 straight at home vs Mariners — OVER in 3 of 4 similar MLB matchups next game"
"""

import os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

SPORT_CONFIG: Dict[str, Dict[str, str]] = {
    'mlb': {'table': 'mlb_games',   'home_score': 'home_runs',   'away_score': 'away_runs',   'total_col': 'total', 'time_col': 'start_time'},
    'nhl': {'table': 'nhl_games',   'home_score': 'home_goals',  'away_score': 'away_goals',  'total_col': 'total'},
    'nba': {'table': 'nba_games_1', 'home_score': 'home_points', 'away_score': 'away_points', 'total_col': 'total', 'time_col': 'start_time'},
}

# Module-level cache: sport → loaded context dict
_context_cache: Dict[str, Dict] = {}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_connection():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not set")
    parsed = urlparse(database_url)
    return psycopg2.connect(
        host=parsed.hostname,
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        port=parsed.port or 5432,
    )


# ---------------------------------------------------------------------------
# Per-game result helpers
# ---------------------------------------------------------------------------

def _game_results(games: List[Dict], trend_type: str) -> List[bool]:
    """
    Build a chronologically-ordered list of True/False for each game that has
    the required data. Games missing scores/total are silently skipped.

    For home_h2h: perspective is always the home team.
    For gen_h2h:  over/under is symmetric; win/loss is from the first-named (A) team.
    """
    results: List[bool] = []
    for g in sorted(games, key=lambda x: x['game_date']):
        hs = g.get('hs')
        aw = g.get('aw')
        tl = g.get('tl')

        if hs is None or aw is None:
            continue
        if trend_type in ('over_streak', 'under_streak') and tl is None:
            continue

        actual = hs + aw
        if trend_type == 'over_streak':
            results.append(actual > tl)
        elif trend_type == 'under_streak':
            results.append(actual < tl)
        elif trend_type == 'win_streak':
            results.append(hs > aw)
        elif trend_type == 'loss_streak':
            results.append(hs < aw)

    return results


def _game_results_with_ml(games: List[Dict], trend_type: str) -> List[Tuple[bool, Optional[int]]]:
    """
    Like _game_results but also returns the focal team's money line per game.
    For win/loss, focal = home team (hml). For over/under, ML is not meaningful (None).
    """
    out: List[Tuple[bool, Optional[int]]] = []
    for g in sorted(games, key=lambda x: x['game_date']):
        hs = g.get('hs')
        aw = g.get('aw')
        tl = g.get('tl')

        if hs is None or aw is None:
            continue
        if trend_type in ('over_streak', 'under_streak') and tl is None:
            continue

        actual = hs + aw
        if trend_type == 'over_streak':
            out.append((actual > tl, None))
        elif trend_type == 'under_streak':
            out.append((actual < tl, None))
        elif trend_type == 'win_streak':
            out.append((hs > aw, g.get('hml')))
        elif trend_type == 'loss_streak':
            out.append((hs < aw, g.get('hml')))
    return out


def _max_streak(results: List[bool]) -> int:
    max_s = cur = 0
    for r in results:
        if r:
            cur += 1
            if cur > max_s:
                max_s = cur
        else:
            cur = 0
    return max_s


# ---------------------------------------------------------------------------
# Loader — fetches and caches raw game sequences + max-streak stats
# ---------------------------------------------------------------------------

def _load_sport_context(sport: str) -> Optional[Dict]:
    """
    Returns:
    {
        'home_h2h_games': { (home_team, away_team): [game dicts sorted by date] },
        'gen_h2h_games':  { (team_a, team_b):       [game dicts sorted by date] },   # a < b
        'home_h2h_max':   { (home_team, away_team): { trend_type: max_streak, ... } },
        'gen_h2h_max':    { (team_a, team_b):       { trend_type: max_streak, ... } },
    }
    """
    if sport in _context_cache:
        return _context_cache[sport]

    cfg = SPORT_CONFIG.get(sport)
    if not cfg:
        return None

    conn = None
    try:
        conn = _get_connection()
        query = f"""
            SELECT game_date, home_team_name, away_team_name,
                   {cfg['home_score']} AS hs,
                   {cfg['away_score']} AS aw,
                   {cfg['total_col']}  AS tl,
                   home_money_line    AS hml,
                   away_money_line    AS aml
            FROM {cfg['table']}
            WHERE {cfg['home_score']} IS NOT NULL AND {cfg['away_score']} IS NOT NULL
            ORDER BY game_date ASC{', ' + cfg['time_col'] + ' ASC NULLS LAST' if cfg.get('time_col') else ''}, game_id ASC
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            rows = [dict(r) for r in cur.fetchall()]

        print(f"[context] Loaded {len(rows)} completed {sport.upper()} games")

        home_h2h_games: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
        gen_h2h_games: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
        team_games: Dict[str, List[Dict]] = defaultdict(list)

        for row in rows:
            ht, at = row['home_team_name'], row['away_team_name']
            g = {'hs': row['hs'], 'aw': row['aw'], 'tl': row['tl'], 'game_date': row['game_date'],
                 'hml': row['hml'], 'aml': row['aml']}
            home_h2h_games[(ht, at)].append(g)
            gen_h2h_games[(min(ht, at), max(ht, at))].append(g)
            # Team-perspective: each team's own score first, their own ML as hml
            team_games[ht].append({
                'hs': row['hs'], 'aw': row['aw'], 'tl': row['tl'],
                'game_date': row['game_date'], 'hml': row['hml'],
            })
            team_games[at].append({
                'hs': row['aw'], 'aw': row['hs'], 'tl': row['tl'],
                'game_date': row['game_date'], 'hml': row['aml'],
            })

        TREND_TYPES = ('over_streak', 'under_streak', 'win_streak', 'loss_streak')

        # Max streaks for home H2H (home team perspective)
        home_h2h_max = {}
        for pair, games in home_h2h_games.items():
            home_h2h_max[pair] = {tt: _max_streak(_game_results(games, tt)) for tt in TREND_TYPES}
            home_h2h_max[pair]['num_games'] = len(games)

        # Max streaks for gen H2H (over/under symmetric; win/loss takes max across both perspectives)
        gen_h2h_max = {}
        for pair, games in gen_h2h_games.items():
            a_results = {tt: _game_results(games, tt) for tt in TREND_TYPES}
            # For win/loss, also compute from "away" perspective (flip hs/aw)
            flipped = [{'hs': g['aw'], 'aw': g['hs'], 'tl': g['tl'], 'game_date': g['game_date']} for g in games]
            b_win  = _max_streak(_game_results(flipped, 'win_streak'))
            b_loss = _max_streak(_game_results(flipped, 'loss_streak'))
            gen_h2h_max[pair] = {
                'over_streak':  _max_streak(a_results['over_streak']),
                'under_streak': _max_streak(a_results['under_streak']),
                'win_streak':   max(_max_streak(a_results['win_streak']), b_win),
                'loss_streak':  max(_max_streak(a_results['loss_streak']), b_loss),
                'num_games':    len(games),
            }

        context = {
            'home_h2h_games': dict(home_h2h_games),
            'gen_h2h_games':  dict(gen_h2h_games),
            'home_h2h_max':   home_h2h_max,
            'gen_h2h_max':    gen_h2h_max,
            'team_games':     dict(team_games),
        }
        _context_cache[sport] = context
        print(
            f"[context] {sport.upper()}: "
            f"{len(home_h2h_games)} home matchup pairs, "
            f"{len(gen_h2h_games)} H2H pairs, "
            f"{len(team_games)} teams cached"
        )
        return context

    except Exception as e:
        print(f"[context] Error loading {sport} context: {e}")
        return None
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Continuation analysis
# ---------------------------------------------------------------------------

def _continuation_stats(
    all_pair_games: Dict[Tuple[str, str], List[Dict]],
    trend_type: str,
    target_length: int,
    gen_h2h: bool = False,
) -> Tuple[int, int, Optional[Dict[str, Tuple[int, int]]]]:
    """
    Scan every matchup pair's chronological game sequence.
    Every time the running streak hits exactly `target_length`, record what happened
    in the NEXT game (did the streak continue, or did it break?).

    Returns (continued, total_instances, ml_stats).
    ml_stats = {'fav': (continued, total), 'dog': (continued, total)} for win/loss, else None.

    For gen_h2h win/loss: check both team perspectives and count each separately.
    """
    continued = 0
    total = 0
    track_ml = trend_type in ('win_streak', 'loss_streak')
    fav_c = fav_t = dog_c = dog_t = 0

    pairs_to_check = list(all_pair_games.items())

    # For gen_h2h win/loss, also run the flipped perspective (swap scores and ML)
    if gen_h2h and trend_type in ('win_streak', 'loss_streak'):
        flipped_pairs = []
        for pair, games in all_pair_games.items():
            flipped = [
                {'hs': g['aw'], 'aw': g['hs'], 'tl': g['tl'], 'game_date': g['game_date'],
                 'hml': g.get('aml'), 'aml': g.get('hml')}
                for g in games
            ]
            flipped_pairs.append((pair, flipped))
        pairs_to_check = pairs_to_check + flipped_pairs

    for _pair, games in pairs_to_check:
        paired = _game_results_with_ml(games, trend_type)
        current = 0
        for i, (r, ml) in enumerate(paired):
            if r:
                current += 1
                if current == target_length and i + 1 < len(paired):
                    total += 1
                    next_r = paired[i + 1][0]
                    if next_r:
                        continued += 1
                    if track_ml and ml is not None:
                        if ml < 0:
                            fav_t += 1
                            if next_r:
                                fav_c += 1
                        else:
                            dog_t += 1
                            if next_r:
                                dog_c += 1
            else:
                current = 0

    ml_stats: Optional[Dict[str, Tuple[int, int]]] = None
    if track_ml and (fav_t + dog_t) > 0:
        ml_stats = {'fav': (fav_c, fav_t), 'dog': (dog_c, dog_t)}

    return continued, total, ml_stats


def _continuation_stats_team(
    team_games: Dict[str, List[Dict]],
    trend_type: str,
    target_length: int,
) -> Tuple[int, int, Optional[Dict[str, Tuple[int, int]]]]:
    """
    Scan every team's chronological game sequence.
    Every time the running streak hits exactly `target_length`, record what happened next.
    Games are stored from each team's own perspective (their score as hs, opp as aw, own ML as hml).
    """
    continued = 0
    total = 0
    track_ml = trend_type in ('win_streak', 'loss_streak')
    fav_c = fav_t = dog_c = dog_t = 0

    for _team, games in team_games.items():
        paired = _game_results_with_ml(games, trend_type)
        current = 0
        for i, (r, ml) in enumerate(paired):
            if r:
                current += 1
                if current == target_length and i + 1 < len(paired):
                    total += 1
                    next_r = paired[i + 1][0]
                    if next_r:
                        continued += 1
                    if track_ml and ml is not None:
                        if ml < 0:
                            fav_t += 1
                            if next_r:
                                fav_c += 1
                        else:
                            dog_t += 1
                            if next_r:
                                dog_c += 1
            else:
                current = 0

    ml_stats: Optional[Dict[str, Tuple[int, int]]] = None
    if track_ml and (fav_t + dog_t) > 0:
        ml_stats = {'fav': (fav_c, fav_t), 'dog': (dog_c, dog_t)}

    return continued, total, ml_stats


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _pct(c: int, t: int) -> str:
    return f"{round(c / t * 100)}%"



def get_streak_context(
    sport: str,
    trend_type: str,
    streak_length: int,
    h2h_mode: str = 'home_h2h',
    today_ml: Optional[int] = None,
    today_team: Optional[str] = None,
) -> str:
    """
    Return a short context string for a streak trend, or '' if no useful data.

    Looks across all historical matchups of this sport, finds every instance where
    a running streak hit exactly `streak_length`, and reports the continuation rate
    as a percentage, split by favorite/underdog.

    If today_ml and today_team are provided, the matching bucket is labeled
    "today (fav/dog)", shown first, and a team role note is appended at the end.

    Example output:
        "Win continued 57% in similar MLB home matchups (today (fav): 59%, dogs: 40%) — Yankees are the favorite"

    Args:
        sport:         'mlb', 'nhl', or 'nba'
        trend_type:    'win_streak', 'loss_streak', 'over_streak', 'under_streak'
        streak_length: current streak count
        h2h_mode:      'home_h2h' or 'gen_h2h'
        today_ml:      focal team's American money line for today (negative = favorite)
        today_team:    focal team's name for the role note
    """
    try:
        ctx = _load_sport_context(sport)
        if not ctx:
            return ''

        if h2h_mode == 'team':
            all_team_games = ctx.get('team_games', {})
            if not all_team_games:
                return ''
            continued, total, ml_stats = _continuation_stats_team(
                all_team_games, trend_type, streak_length,
            )
        else:
            games_key = 'home_h2h_games' if h2h_mode == 'home_h2h' else 'gen_h2h_games'
            all_pair_games = ctx.get(games_key, {})
            if not all_pair_games:
                return ''
            continued, total, ml_stats = _continuation_stats(
                all_pair_games, trend_type, streak_length,
                gen_h2h=(h2h_mode == 'gen_h2h'),
            )

        if total == 0:
            return ''

        sport_label = sport.upper()
        sample_note = ' (small sample)' if total <= 3 else ''
        location = {'home_h2h': 'home H2H matchups', 'gen_h2h': 'H2H matchups', 'team': 'games'}.get(h2h_mode, 'games')

        # Descriptive base string — self-contained so it makes sense without the trend description
        if trend_type in ('over_streak', 'under_streak'):
            direction = 'OVER' if trend_type == 'over_streak' else 'UNDER'
            if h2h_mode == 'team':
                condition = f"when the {direction} hits {streak_length} straight"
            else:
                condition = f"when the {direction} hits {streak_length} straight in {sport_label} {location}"
            if continued == 0:
                base = f"historically {condition}, it has never continued{sample_note}"
            elif continued == total:
                base = f"historically {condition}, it has always continued{sample_note}"
            else:
                base = f"historically {condition}, it continues {_pct(continued, total)} of the time{sample_note}"
        else:  # win_streak / loss_streak
            direction = 'wins' if trend_type == 'win_streak' else 'losses'
            if h2h_mode == 'team':
                condition = f"when a team hits {streak_length} straight {direction}"
            else:
                condition = f"when a team hits {streak_length} straight {direction} in {sport_label} {location}"
            if continued == 0:
                base = f"historically {condition}, the streak has never continued{sample_note}"
            elif continued == total:
                base = f"historically {condition}, the streak has always continued{sample_note}"
            else:
                base = f"historically {condition}, the streak continues {_pct(continued, total)} of the time{sample_note}"

        # For win/loss: integrate ML split inline with team name in the applicable bucket
        if ml_stats and trend_type in ('win_streak', 'loss_streak'):
            fav_c, fav_t = ml_stats['fav']
            dog_c, dog_t = ml_stats['dog']

            fav_str = f"{_pct(fav_c, fav_t)} when favored" if fav_t >= 2 else None
            dog_str = f"{_pct(dog_c, dog_t)} as the underdog" if dog_t >= 2 else None

            # Inline team name with the matching bucket
            if today_team and today_ml is not None:
                if today_ml < 0 and fav_str:
                    fav_str = f"{_pct(fav_c, fav_t)} when favored ({today_team} today)"
                elif today_ml >= 0 and dog_str:
                    dog_str = f"{_pct(dog_c, dog_t)} as the underdog ({today_team} today)"

            parts = [p for p in [fav_str, dog_str] if p]
            result = f"{base} — {', '.join(parts)}" if parts else base

        # For over/under: no ML split; just append team role if known
        else:
            result = base
            if today_team and today_ml is not None:
                role = "the favorite" if today_ml < 0 else "the underdog"
                result = f"{result} — {today_team} are {role}"

        return result

    except Exception as e:
        print(f"[context] get_streak_context error: {e}")
        return ''


