"""
Trend context service — for H2H streaks found in the digest, find every historical
instance where any matchup reached that streak length and report what happened next.

E.g. "Total went OVER 6 straight at home vs Mariners — OVER in 3 of 4 similar MLB matchups next game"
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

SPORT_CONFIG: Dict[str, Dict[str, str]] = {
    'mlb':   {'table': 'mlb_games',   'home_score': 'home_runs',   'away_score': 'away_runs',   'total_col': 'total', 'time_col': 'start_time'},
    'nhl':   {'table': 'nhl_games',   'home_score': 'home_goals',  'away_score': 'away_goals',  'total_col': 'total'},
    'nba':   {'table': 'nba_games_1', 'home_score': 'home_points', 'away_score': 'away_points', 'total_col': 'total', 'time_col': 'start_time'},
    # home_spread/away_spread enable cover_streak/no_cover_streak analysis for a sport.
    # Omitted for mlb/nhl/nba: MLB's home_line/away_line columns are a duplicate of the
    # moneyline (not a real spread) — see GameFAQSection.tsx's same caveat.
    'ncaaf': {'table': 'ncaaf_games', 'home_score': 'home_points', 'away_score': 'away_points', 'total_col': 'total', 'time_col': 'start_time',
              'home_spread': 'home_line', 'away_spread': 'away_line'},
    'nfl':   {'table': 'nfl_games',   'home_score': 'home_points', 'away_score': 'away_points', 'total_col': 'total', 'time_col': 'start_time',
              'home_spread': 'home_line', 'away_spread': 'away_line'},
    # Soccer is scoped per-league (not one shared 'soccer' pool) — mixing e.g. EPL and
    # Bundesliga history would produce a misleading continuation rate.
    'soccer_epl':        {'table': 'soccer_games', 'home_score': 'home_goals', 'away_score': 'away_goals', 'total_col': 'total_goals', 'time_col': 'start_time',
                           'home_spread': 'home_spread', 'away_spread': 'away_spread', 'league_filter': 'EPL'},
    'soccer_laliga':     {'table': 'soccer_games', 'home_score': 'home_goals', 'away_score': 'away_goals', 'total_col': 'total_goals', 'time_col': 'start_time',
                           'home_spread': 'home_spread', 'away_spread': 'away_spread', 'league_filter': 'LA LIGA'},
    'soccer_bundesliga': {'table': 'soccer_games', 'home_score': 'home_goals', 'away_score': 'away_goals', 'total_col': 'total_goals', 'time_col': 'start_time',
                           'home_spread': 'home_spread', 'away_spread': 'away_spread', 'league_filter': 'BUNDESLIGA'},
    'soccer_ligue1':     {'table': 'soccer_games', 'home_score': 'home_goals', 'away_score': 'away_goals', 'total_col': 'total_goals', 'time_col': 'start_time',
                           'home_spread': 'home_spread', 'away_spread': 'away_spread', 'league_filter': 'LIGUE 1'},
    'soccer_seriea':     {'table': 'soccer_games', 'home_score': 'home_goals', 'away_score': 'away_goals', 'total_col': 'total_goals', 'time_col': 'start_time',
                           'home_spread': 'home_spread', 'away_spread': 'away_spread', 'league_filter': 'SERIE A'},
}

# Module-level cache: sport → loaded context dict
_context_cache: Dict[str, Dict] = {}

# Cache for get_odds_whiplash_context's pooled stats (built once per sport,
# same lifetime as _context_cache).
_whiplash_cache: Dict[str, Dict] = {}

# American-odds cutoff for what counts as a "big" favorite in
# get_odds_whiplash_context/find_odds_whiplash_trend below — -300 means
# roughly a 3-in-4 implied favorite or steeper.
BIG_FAVORITE_ML = -300


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
        ln = g.get('ln')

        if hs is None or aw is None:
            continue
        if trend_type in ('over_streak', 'under_streak') and tl is None:
            continue
        if trend_type in ('cover_streak', 'no_cover_streak') and ln is None:
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
        elif trend_type == 'draw_streak':
            results.append(hs == aw)
        elif trend_type == 'cover_streak':
            results.append(hs + ln > aw)
        elif trend_type == 'no_cover_streak':
            results.append(hs + ln < aw)

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
        ln = g.get('ln')

        if hs is None or aw is None:
            continue
        if trend_type in ('over_streak', 'under_streak') and tl is None:
            continue
        if trend_type in ('cover_streak', 'no_cover_streak') and ln is None:
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
        elif trend_type == 'draw_streak':
            out.append((hs == aw, g.get('hml')))
        elif trend_type == 'cover_streak':
            out.append((hs + ln > aw, g.get('hml')))
        elif trend_type == 'no_cover_streak':
            out.append((hs + ln < aw, g.get('hml')))
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
        has_spread = bool(cfg.get('home_spread') and cfg.get('away_spread'))
        spread_select = f", {cfg['home_spread']} AS hln, {cfg['away_spread']} AS aln" if has_spread else ""
        league_filter = cfg.get('league_filter')
        league_where = " AND league = %s" if league_filter else ""
        query = f"""
            SELECT game_date, home_team_name, away_team_name,
                   {cfg['home_score']} AS hs,
                   {cfg['away_score']} AS aw,
                   {cfg['total_col']}  AS tl,
                   home_money_line    AS hml,
                   away_money_line    AS aml{spread_select}
            FROM {cfg['table']}
            WHERE {cfg['home_score']} IS NOT NULL AND {cfg['away_score']} IS NOT NULL{league_where}
            ORDER BY game_date ASC{', ' + cfg['time_col'] + ' ASC NULLS LAST' if cfg.get('time_col') else ''}, game_id ASC
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [league_filter] if league_filter else None)
            rows = [dict(r) for r in cur.fetchall()]

        print(f"[context] Loaded {len(rows)} completed {sport.upper()} games")

        home_h2h_games: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
        gen_h2h_games: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
        team_games: Dict[str, List[Dict]] = defaultdict(list)

        for row in rows:
            ht, at = row['home_team_name'], row['away_team_name']
            hln, aln = row.get('hln'), row.get('aln')
            # 'ln' is the home team's own spread (for home_h2h/gen_h2h, perspective is home);
            # 'aln' is kept alongside so the away-perspective flip in _continuation_stats can use it.
            g = {'hs': row['hs'], 'aw': row['aw'], 'tl': row['tl'], 'game_date': row['game_date'],
                 'hml': row['hml'], 'aml': row['aml'], 'ln': hln, 'aln': aln}
            home_h2h_games[(ht, at)].append(g)
            gen_h2h_games[(min(ht, at), max(ht, at))].append(g)
            # Team-perspective: each team's own score, own ML, own spread, and
            # whether they were home or away, first (is_home powers
            # get_odds_whiplash_context/find_odds_whiplash_trend below, which
            # need to know venue as well as result/price).
            team_games[ht].append({
                'hs': row['hs'], 'aw': row['aw'], 'tl': row['tl'],
                'game_date': row['game_date'], 'hml': row['hml'], 'ln': hln,
                'is_home': True,
            })
            team_games[at].append({
                'hs': row['aw'], 'aw': row['hs'], 'tl': row['tl'],
                'game_date': row['game_date'], 'hml': row['aml'], 'ln': aln,
                'is_home': False,
            })

        TREND_TYPES = ('over_streak', 'under_streak', 'win_streak', 'loss_streak')
        if has_spread:
            TREND_TYPES = TREND_TYPES + ('cover_streak', 'no_cover_streak')

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
    track_ml = trend_type in ('win_streak', 'loss_streak', 'draw_streak', 'cover_streak', 'no_cover_streak')
    fav_c = fav_t = dog_c = dog_t = 0

    pairs_to_check = list(all_pair_games.items())

    # For gen_h2h win/loss/cover, also run the flipped perspective (swap scores, ML, and spread)
    if gen_h2h and trend_type in ('win_streak', 'loss_streak', 'draw_streak', 'cover_streak', 'no_cover_streak'):
        flipped_pairs = []
        for pair, games in all_pair_games.items():
            flipped = [
                {'hs': g['aw'], 'aw': g['hs'], 'tl': g['tl'], 'game_date': g['game_date'],
                 'hml': g.get('aml'), 'aml': g.get('hml'),
                 'ln': g.get('aln'), 'aln': g.get('ln')}
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
    track_ml = trend_type in ('win_streak', 'loss_streak', 'draw_streak', 'cover_streak', 'no_cover_streak')
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


def get_streak_stats(
    sport: str,
    trend_type: str,
    streak_length: int,
    h2h_mode: str = 'home_h2h',
) -> Optional[Dict[str, Any]]:
    """Return {'rate': float, 'sample_size': int} for the given streak, or None if no data.

    rate is the historical continuation probability (continued / total).
    sample_size is the number of instances where the streak hit exactly streak_length.
    """
    try:
        ctx = _load_sport_context(sport)
        if not ctx:
            return None

        if h2h_mode == 'team':
            continued, total, _ = _continuation_stats_team(
                ctx.get('team_games', {}), trend_type, streak_length
            )
        else:
            games_key = 'home_h2h_games' if h2h_mode == 'home_h2h' else 'gen_h2h_games'
            continued, total, _ = _continuation_stats(
                ctx.get(games_key, {}), trend_type, streak_length,
                gen_h2h=(h2h_mode == 'gen_h2h'),
            )

        if total == 0:
            return None
        return {'rate': continued / total, 'sample_size': total}
    except Exception as e:
        print(f"[context] get_streak_stats error: {e}")
        return None


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
        sample_note = f' ({continued} of {total} instances)' if total <= 3 else ''
        location = {'home_h2h': 'home H2H matchups', 'gen_h2h': 'H2H matchups', 'team': 'games'}.get(h2h_mode, 'games')

        # Descriptive base string — self-contained so it makes sense without the trend description
        if trend_type in ('over_streak', 'under_streak'):
            direction = 'OVER' if trend_type == 'over_streak' else 'UNDER'
            if h2h_mode == 'team':
                condition = f"when the {direction} hits {streak_length} straight"
            else:
                condition = f"when the {direction} hits {streak_length} straight in {sport_label} {location}"
            if continued == 0:
                base = f"Historically {condition}, it has never continued{sample_note}"
            elif continued == total:
                base = f"Historically {condition}, it has always continued{sample_note}"
            else:
                base = f"Historically {condition}, it continues {_pct(continued, total)} of the time{sample_note}"
        elif trend_type in ('cover_streak', 'no_cover_streak'):
            direction = 'covers' if trend_type == 'cover_streak' else 'fails to cover'
            if h2h_mode == 'team':
                condition = f"when a team {direction} {streak_length} straight spreads"
            else:
                condition = f"when a team {direction} {streak_length} straight spreads in {sport_label} {location}"
            if continued == 0:
                base = f"Historically {condition}, the streak has never continued{sample_note}"
            elif continued == total:
                base = f"Historically {condition}, the streak has always continued{sample_note}"
            else:
                base = f"Historically {condition}, the streak continues {_pct(continued, total)} of the time{sample_note}"
        else:  # win_streak / loss_streak / draw_streak
            direction = {'win_streak': 'wins', 'loss_streak': 'losses', 'draw_streak': 'draws'}[trend_type]
            if h2h_mode == 'team':
                condition = f"when a team hits {streak_length} straight {direction}"
            else:
                condition = f"when a team hits {streak_length} straight {direction} in {sport_label} {location}"
            if continued == 0:
                base = f"Historically {condition}, the streak has never continued{sample_note}"
            elif continued == total:
                base = f"Historically {condition}, the streak has always continued{sample_note}"
            else:
                base = f"Historically {condition}, the streak continues {_pct(continued, total)} of the time{sample_note}"

        # For win/loss/cover: show ML split breakdown, then team role as a separate statement
        if ml_stats and trend_type in ('win_streak', 'loss_streak', 'draw_streak', 'cover_streak', 'no_cover_streak'):
            fav_c, fav_t = ml_stats['fav']
            dog_c, dog_t = ml_stats['dog']

            fav_str = f"{_pct(fav_c, fav_t)} when favored ({fav_c}/{fav_t})" if fav_t >= 2 else None
            dog_str = f"{_pct(dog_c, dog_t)} as underdog ({dog_c}/{dog_t})" if dog_t >= 2 else None

            parts = [p for p in [fav_str, dog_str] if p]
            result = f"{base} — {', '.join(parts)}" if parts else base

            # Team role as a clear, separate concluding statement
            if today_team and today_ml is not None:
                role = "today's favorite" if today_ml < 0 else "today's underdog"
                result = f"{result} — {today_team} are {role}"

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


# ---------------------------------------------------------------------------
# Odds-status whiplash — situational patterns around a team's last game vs.
# tonight's own line, e.g. "lost last time as a big favorite, big favorite
# again tonight" or "won on the road as a dog, home favorite tonight".
# Pooled the same way as the streak stats above: scan every team's full
# game log league-wide for every historical instance of the pattern, not
# just these two teams (a single team's own history of it is nearly always
# too small a sample to say anything).
# ---------------------------------------------------------------------------

def get_odds_whiplash_context(sport: str) -> Dict[str, Dict[str, Any]]:
    """Pooled, cached stats for two situational patterns, scanned across every
    team's game log for `sport`:

      big_favorite_letdown_rebound: lost the previous game as a big favorite
        (moneyline <= BIG_FAVORITE_ML), and is a big favorite again this game.
      dog_win_home_favorite_swing: won the previous game on the road as an
        underdog, and is the home favorite this game.

    Returns {pattern_name: {'win_rate': float, 'sample_size': int,
    'avg_margin': float}} — avg_margin is the mean (team_score - opp_score)
    across the *next* game in every matching instance (so it's negative if
    the pattern more often ends in a loss). Empty dict if sport has no
    context loaded.
    """
    if sport in _whiplash_cache:
        return _whiplash_cache[sport]

    ctx = _load_sport_context(sport)
    if not ctx:
        return {}

    team_games = ctx.get('team_games', {})

    patterns = {
        'big_favorite_letdown_rebound': {'margins': [], 'wins': 0, 'total': 0},
        'dog_win_home_favorite_swing':  {'margins': [], 'wins': 0, 'total': 0},
    }

    for _team, games in team_games.items():
        # games is already chronological (game_date ASC) — see _load_sport_context.
        for i in range(len(games) - 1):
            g, nxt = games[i], games[i + 1]
            g_ml = g.get('hml')
            if g_ml is None:
                continue
            g_won = g['hs'] > g['aw']

            if g_ml <= BIG_FAVORITE_ML and not g_won:
                nxt_ml = nxt.get('hml')
                if nxt_ml is not None and nxt_ml <= BIG_FAVORITE_ML:
                    stats = patterns['big_favorite_letdown_rebound']
                    stats['total'] += 1
                    margin = nxt['hs'] - nxt['aw']
                    stats['margins'].append(margin)
                    if margin > 0:
                        stats['wins'] += 1

            if g.get('is_home') is False and g_ml > 0 and g_won:
                if nxt.get('is_home') is True and (nxt.get('hml') or 0) < 0:
                    stats = patterns['dog_win_home_favorite_swing']
                    stats['total'] += 1
                    margin = nxt['hs'] - nxt['aw']
                    stats['margins'].append(margin)
                    if margin > 0:
                        stats['wins'] += 1

    result = {}
    for name, stats in patterns.items():
        total = stats['total']
        result[name] = {
            'win_rate': (stats['wins'] / total) if total else 0.0,
            'sample_size': total,
            'avg_margin': (sum(stats['margins']) / total) if total else 0.0,
        }

    _whiplash_cache[sport] = result
    return result


def find_odds_whiplash_trend(
    sport: str, team_name: str, today_ml: Optional[int], today_is_home: bool,
) -> Optional[Dict[str, Any]]:
    """Check `team_name`'s most recent completed game against tonight's own
    line for one of the two odds-whiplash patterns (see
    get_odds_whiplash_context). Returns a trend dict (already carrying
    continuation_rate/sample_size, same shape as any other trend so
    get_confidence_score/rank_game_trends work on it unmodified) or None if
    neither pattern applies or there isn't enough data to check.

    The two patterns are mutually exclusive by construction (one requires
    the last game to be a loss, the other a win), so at most one is returned.
    """
    if today_ml is None:
        return None
    ctx = _load_sport_context(sport)
    if not ctx:
        return None
    games = ctx.get('team_games', {}).get(team_name)
    if not games:
        return None

    last = games[-1]
    last_ml = last.get('hml')
    if last_ml is None:
        return None
    last_won = last['hs'] > last['aw']

    if last_ml <= BIG_FAVORITE_ML and not last_won and today_ml <= BIG_FAVORITE_ML:
        stats = get_odds_whiplash_context(sport).get('big_favorite_letdown_rebound')
        if not stats or stats['sample_size'] == 0:
            return None
        base = f"{team_name} lost their last game as a big favorite and are a big favorite again tonight"
        return {
            'type': 'favorite_letdown_rebound',
            'count': 1,
            'description': f"{base} — {_whiplash_history_note(stats)}",
            'continuation_rate': stats['win_rate'],
            'sample_size': stats['sample_size'],
            'avg_margin': round(stats['avg_margin'], 1),
        }

    if last.get('is_home') is False and last_ml > 0 and last_won and today_is_home and today_ml < 0:
        stats = get_odds_whiplash_context(sport).get('dog_win_home_favorite_swing')
        if not stats or stats['sample_size'] == 0:
            return None
        base = f"{team_name} won on the road as an underdog last time out and are the favorite at home tonight"
        return {
            'type': 'dog_win_home_favorite_swing',
            'count': 1,
            'description': f"{base} — {_whiplash_history_note(stats)}",
            'continuation_rate': stats['win_rate'],
            'sample_size': stats['sample_size'],
            'avg_margin': round(stats['avg_margin'], 1),
        }

    return None


def _whiplash_history_note(stats: Dict[str, Any]) -> str:
    """Turn a get_odds_whiplash_context() stats dict into the same kind of
    self-contained "Historically... X% of the time" clause get_streak_context
    produces — this is the only text the model actually sees, so the
    percentage/margin has to be spelled out here rather than left as a raw
    field the prompt never renders."""
    pct = round(stats['win_rate'] * 100)
    n = stats['sample_size']
    margin = stats['avg_margin']
    margin_str = f"winning by about {abs(round(margin))} on average" if margin >= 0 else f"losing by about {abs(round(margin))} on average"
    return f"historically in this exact situation, teams win {pct}% of the time ({n} instances), {margin_str}"


# ---------------------------------------------------------------------------
# Live-series detection — is an active H2H win/loss streak actually from
# games these two teams played in the last few days (a live series), or
# spread across separate, non-adjacent past meetings?
# ---------------------------------------------------------------------------

def get_recent_series_games(
    sport: str, team_a: str, team_b: str, before_date_str: str, lookback_days: int = 6,
) -> List[Dict[str, Any]]:
    """Completed games between team_a and team_b (either home/away order)
    within lookback_days of before_date_str — reuses the cached gen_h2h_games
    data, no extra DB query. Used to tell whether an H2H streak reflects
    games played in the current live series vs. older, separate meetings."""
    ctx = _load_sport_context(sport)
    if not ctx:
        return []
    games = ctx.get('gen_h2h_games', {}).get((min(team_a, team_b), max(team_a, team_b)), [])
    try:
        before = datetime.strptime(before_date_str, "%Y-%m-%d").date()
    except ValueError:
        return []
    cutoff = before - timedelta(days=lookback_days)
    return [g for g in games if cutoff <= g['game_date'] < before]


