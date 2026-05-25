"""Blog service — CRUD + YouTube-to-blog pipeline."""

import os
import re
import json
import logging
from datetime import datetime, timezone, date, time

import psycopg2
import psycopg2.extras
import anthropic
from dotenv import load_dotenv


class _DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date, time)):
            return str(obj)
        return super().default(obj)


def _json_dumps(obj):
    return json.dumps(obj, cls=_DateTimeEncoder)

load_dotenv(override=True)

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
YOUTUBE_DATA_API_KEY = os.getenv("YOUTUBE_DATA_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

_SPORT_KEY_MAP = {
    "mlb": "baseball_mlb",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
}


def _get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


# ---------------------------------------------------------------------------
# Public read methods
# ---------------------------------------------------------------------------

class BlogService:

    @staticmethod
    def get_published_posts(limit=20, offset=0, category=None, sport_tag=None):
        """Return published posts ordered by published_at DESC."""
        try:
            query = """
                SELECT id, slug, title, excerpt, og_image_url,
                       youtube_thumbnail_url, tags, reading_time_minutes,
                       published_at, category
                FROM blog_posts
                WHERE status = 'published'
            """
            params = []
            if category:
                query += " AND category = %s"
                params.append(category)
            if sport_tag:
                query += " AND %s = ANY(tags)"
                params.append(sport_tag)
            query += " ORDER BY published_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
            return [dict(r) for r in rows], None
        except Exception as e:
            logger.error("get_published_posts error: %s", e)
            return [], str(e)

    @staticmethod
    def get_post_by_slug(slug):
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT * FROM blog_posts
                        WHERE slug = %s AND status = 'published'
                    """, (slug,))
                    row = cur.fetchone()
            return dict(row) if row else None, None
        except Exception as e:
            logger.error("get_post_by_slug error: %s", e)
            return None, str(e)

    @staticmethod
    def get_all_posts_admin():
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, slug, title, status, created_at, published_at,
                               youtube_video_id, reading_time_minutes
                        FROM blog_posts
                        ORDER BY created_at DESC
                    """)
                    rows = cur.fetchall()
            return [dict(r) for r in rows], None
        except Exception as e:
            logger.error("get_all_posts_admin error: %s", e)
            return [], str(e)

    @staticmethod
    def create_post(data):
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO blog_posts
                            (title, slug, meta_description, excerpt, content, tags,
                             reading_time_minutes, og_image_url, status,
                             youtube_video_id, youtube_title, youtube_description,
                             youtube_thumbnail_url, youtube_published_at,
                             sport, sport_key, home_team, away_team,
                             odds_event_id, game_date, game_data, category)
                        VALUES
                            (%(title)s, %(slug)s, %(meta_description)s, %(excerpt)s,
                             %(content)s, %(tags)s, %(reading_time_minutes)s,
                             %(og_image_url)s, %(status)s,
                             %(youtube_video_id)s, %(youtube_title)s,
                             %(youtube_description)s, %(youtube_thumbnail_url)s,
                             %(youtube_published_at)s,
                             %(sport)s, %(sport_key)s, %(home_team)s, %(away_team)s,
                             %(odds_event_id)s, %(game_date)s, %(game_data)s, %(category)s)
                        RETURNING id
                    """, {
                        'title': data.get('title'),
                        'slug': data.get('slug'),
                        'meta_description': data.get('meta_description'),
                        'excerpt': data.get('excerpt'),
                        'content': data.get('content'),
                        'tags': data.get('tags'),
                        'reading_time_minutes': data.get('reading_time_minutes'),
                        'og_image_url': data.get('og_image_url'),
                        'status': data.get('status', 'draft'),
                        'youtube_video_id': data.get('youtube_video_id'),
                        'youtube_title': data.get('youtube_title'),
                        'youtube_description': data.get('youtube_description'),
                        'youtube_thumbnail_url': data.get('youtube_thumbnail_url'),
                        'youtube_published_at': data.get('youtube_published_at'),
                        'sport': data.get('sport'),
                        'sport_key': data.get('sport_key'),
                        'home_team': data.get('home_team'),
                        'away_team': data.get('away_team'),
                        'odds_event_id': data.get('odds_event_id'),
                        'game_date': data.get('game_date'),
                        'game_data': _json_dumps(data['game_data']) if data.get('game_data') else None,
                        'category': data.get('category'),
                    })
                    row = cur.fetchone()
                    conn.commit()
            return row['id'], None
        except Exception as e:
            logger.error("create_post error: %s", e)
            return None, str(e)

    @staticmethod
    def update_post(post_id, data):
        fields = []
        values = {}
        allowed = ['title', 'slug', 'meta_description', 'excerpt', 'content',
                   'tags', 'reading_time_minutes', 'og_image_url', 'status',
                   'home_team', 'away_team', 'odds_event_id', 'game_date', 'category']
        for key in allowed:
            if key in data:
                fields.append(f"{key} = %({key})s")
                values[key] = data[key]
        if 'game_data' in data:
            fields.append("game_data = %(game_data)s")
            values['game_data'] = _json_dumps(data['game_data']) if data['game_data'] else None
        if not fields:
            return False, "No updatable fields provided"
        values['id'] = post_id
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE blog_posts SET {', '.join(fields)}, updated_at = now() WHERE id = %(id)s",
                        values,
                    )
                    conn.commit()
            return True, None
        except Exception as e:
            logger.error("update_post error: %s", e)
            return False, str(e)

    @staticmethod
    def publish_post(post_id):
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE blog_posts
                        SET status = 'published',
                            published_at = now(),
                            updated_at = now()
                        WHERE id = %s
                    """, (post_id,))
                    conn.commit()
            return True, None
        except Exception as e:
            logger.error("publish_post error: %s", e)
            return False, str(e)

    @staticmethod
    def delete_post(post_id):
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM blog_posts WHERE id = %s", (post_id,))
                    conn.commit()
            return True, None
        except Exception as e:
            logger.error("delete_post error: %s", e)
            return False, str(e)

    # -----------------------------------------------------------------------
    # YouTube pipeline
    # -----------------------------------------------------------------------

    @staticmethod
    def generate_from_youtube(video_id, game_date=None):
        """Fetch YouTube metadata + transcript, call Claude, save draft."""
        # Duplicate check
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM blog_posts WHERE youtube_video_id = %s",
                        (video_id,),
                    )
                    if cur.fetchone():
                        return None, f"Post for video {video_id} already exists"
        except Exception as e:
            return None, str(e)

        # Fetch YouTube metadata
        youtube_data, err = BlogService._fetch_youtube_metadata(video_id)
        if err:
            return None, err

        # Fetch transcript (best effort)
        transcript = BlogService._fetch_transcript(video_id)

        # Fetch in-season teams for Claude prompt
        teams_by_sport = BlogService._get_in_season_teams()

        # Call Claude
        claude_output, err = BlogService._call_claude(youtube_data, transcript, teams_by_sport)
        if err:
            return None, err

        # Fetch game data (best-effort, non-blocking)
        sport = claude_output.get('sport')
        home_team = claude_output.get('home_team')
        away_team = claude_output.get('away_team')
        game_data_dict = None
        odds_event_id = None
        game_date_used = None

        if sport and home_team and away_team:
            sport_key = _SPORT_KEY_MAP.get(sport)
            game_data_dict, odds_event_id, game_date_used, fetch_err = BlogService._fetch_game_data(
                sport, sport_key, home_team, away_team, game_date
            )
            if fetch_err:
                logger.warning("_fetch_game_data error (non-fatal): %s", fetch_err)

        # Save draft
        post_id, err = BlogService._save_draft(
            claude_output, youtube_data,
            sport=sport,
            sport_key=_SPORT_KEY_MAP.get(sport) if sport else None,
            home_team=home_team,
            away_team=away_team,
            odds_event_id=odds_event_id,
            game_date=game_date_used,
            game_data=game_data_dict,
        )
        return post_id, err

    @staticmethod
    def _get_in_season_teams():
        """Return dict of {sport_upper: [team_name, ...]} for MLB, NBA, NHL."""
        result = {"MLB": [], "NBA": [], "NHL": []}
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT team_name, sport FROM teams WHERE sport IN ('MLB', 'NBA', 'NHL') ORDER BY sport, team_name"
                    )
                    rows = cur.fetchall()
            for row in rows:
                sport_key = row['sport']
                if sport_key in result:
                    result[sport_key].append(row['team_name'])
        except Exception as e:
            logger.warning("_get_in_season_teams error: %s", e)
        return result

    @staticmethod
    def _fetch_youtube_metadata(video_id):
        try:
            import requests as http_requests
            api_key = os.getenv("YOUTUBE_DATA_API_KEY")
            if not api_key:
                return None, "YOUTUBE_DATA_API_KEY is not set in environment"
            resp = http_requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "snippet", "id": video_id, "key": api_key},
                timeout=10,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                return None, f"YouTube video {video_id} not found"
            snippet = items[0]["snippet"]
            thumbnails = snippet.get("thumbnails", {})
            thumb_url = (
                thumbnails.get("maxres", {}).get("url")
                or thumbnails.get("high", {}).get("url")
                or thumbnails.get("default", {}).get("url")
            )
            return {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "thumbnail_url": thumb_url,
                "published_at": snippet.get("publishedAt"),
            }, None
        except Exception as e:
            logger.error("_fetch_youtube_metadata error: %s", e)
            return None, str(e)

    @staticmethod
    def _fetch_transcript(video_id):
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            fetched = api.fetch(video_id)
            return " ".join(snippet.text for snippet in fetched)
        except Exception as e:
            logger.warning("Transcript unavailable for %s: %s", video_id, e)
            return ""

    @staticmethod
    def _call_claude(youtube_data, transcript, teams_by_sport=None):
        try:
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

            transcript_section = (
                f"\n\n## Video Transcript\n{transcript}"
                if transcript
                else "\n\n(No transcript available — use the description only.)"
            )

            teams_section = ""
            if teams_by_sport:
                teams_section = "\n\n## In-Season Teams (use exact names from this list)\n"
                for sport_name, teams in teams_by_sport.items():
                    if teams:
                        teams_section += f"**{sport_name}**: {', '.join(teams)}\n"

            prompt = f"""You are transcribing a sports betting video for GetSTAM.com.

## YouTube Video Info
Title: {youtube_data['title']}
Description: {youtube_data['description']}{transcript_section}{teams_section}

## Instructions
Transcribe exactly what the speaker said. Clean it up by removing filler words (um, uh, like, you know), false starts, and repeated words. Fix grammar so it reads naturally, but do NOT add analysis, commentary, or content that wasn't said. Keep the speaker's voice, phrasing, and opinions intact.

Also detect if this video is about a specific game between two teams. If so, identify the sport and teams using the exact names from the In-Season Teams list above.

Return ONLY valid JSON (no markdown code fences) with these exact keys:

- "title": use the YouTube video title as-is
- "meta_description": 150-160 character summary focused on the game — teams, key storylines, betting angle. Do NOT reference "the speaker" or "the video"
- "excerpt": 2-3 sentences about the game itself — key matchup context, injuries, betting angles. Do NOT start with "The speaker..." or reference the video creator. Write as if describing the game, e.g. "Game 2 of the WCF has the Avalanche hosting the Knights without Cale Makar. The under trend in this matchup is historically strong, with 10 straight unders at home."
- "content": the cleaned transcript as plain Markdown paragraphs — no headers, no bullet points, no added structure
- "tags": array of 5-8 lowercase strings based on topics mentioned (e.g. ["mlb", "betting picks", "over under"])
- "reading_time_minutes": integer estimate
- "sport": one of "mlb", "nba", "nhl", or null if this video is not about a specific game
- "home_team": short team name matching the In-Season Teams list (e.g. "Cubs") or null if not applicable
- "away_team": short team name matching the In-Season Teams list (e.g. "Astros") or null if not applicable"""

            message = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text

            # Try direct parse first, then regex fallback
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if not match:
                    return None, "Claude response was not valid JSON"
                result = json.loads(match.group(0))

            return result, None
        except Exception as e:
            logger.error("_call_claude error: %s", e)
            return None, str(e)

    @staticmethod
    def _fetch_game_data(sport, sport_key, home_team, away_team, game_date=None):
        """Fetch historical game data for a matchup. Returns (game_data_dict, odds_event_id, game_date_used, error)."""
        if sport not in ("mlb", "nhl"):
            return None, None, None, f"Sport '{sport}' not yet supported for game data fetch"

        try:
            if sport == "mlb":
                from .historical.mlb_service import MLBService as SportService
                from .historical.mlb_trends_service import MLBTrendsService as TrendsService
            else:
                from .historical.nhl_service import NHLService as SportService
                from .historical.nhl_trends_service import NHLTrendsService as TrendsService

            # Determine game date
            if game_date:
                game_date_used = game_date if isinstance(game_date, str) else str(game_date)
            else:
                game_date_used = str(date.today())

            # 1. Try to find odds_event_id from a live games lookup (best-effort)
            odds_event_id = None
            try:
                from .game_service import GameService
                result, _ = GameService.get_games_for_date(sport_key or "baseball_mlb", game_date_used)
                games_list = (result or {}).get('games', [])
                home_lower = home_team.lower()
                away_lower = away_team.lower()
                for g in games_list:
                    g_home = (g.get('home', {}).get('team') or '').lower()
                    g_away = (g.get('away', {}).get('team') or '').lower()
                    # Match short name (e.g. "Avalanche") against full name ("Colorado Avalanche")
                    if (home_lower in g_home or g_home in home_lower) and \
                       (away_lower in g_away or g_away in away_lower):
                        odds_event_id = g.get('game_id')
                        break
            except Exception as e:
                logger.warning("Could not fetch odds event_id: %s", e)

            # 2. Fetch last 5 games for each team (overall)
            home_last_5, _ = SportService.get_team_games_by_name(home_team, limit=5)
            away_last_5, _ = SportService.get_team_games_by_name(away_team, limit=5)

            # 3. Fetch last 5 home games for home team
            home_home_last_5, _ = SportService.get_team_games_by_name(home_team, limit=5, venue='home')

            # 4. Fetch last 5 away games for away team
            away_away_last_5, _ = SportService.get_team_games_by_name(away_team, limit=5, venue='away')

            # 5. Head-to-head last 5
            h2h_last_5, _ = SportService.get_head_to_head_games_by_name(home_team, away_team, limit=5)

            # 6. Trends
            trends_results, _ = TrendsService.analyze_multiple_games_trends(
                [{"home_team_name": home_team, "away_team_name": away_team}],
                limit=20
            )
            trends = trends_results[0] if trends_results else {}

            game_data = {
                "home_last_5": home_last_5 or [],
                "away_last_5": away_last_5 or [],
                "home_home_last_5": home_home_last_5 or [],
                "away_away_last_5": away_away_last_5 or [],
                "h2h_last_5": h2h_last_5 or [],
                "trends": trends,
            }

            return game_data, odds_event_id, game_date_used, None

        except Exception as e:
            logger.error("_fetch_game_data error: %s", e)
            return None, None, None, str(e)

    @staticmethod
    def fetch_and_save_game_data(post_id, sport, sport_key, home_team, away_team, game_date=None):
        """Re-fetch game data for an existing post and save it. Returns (result_dict, error)."""
        game_data, odds_event_id, game_date_used, err = BlogService._fetch_game_data(
            sport, sport_key, home_team, away_team, game_date
        )
        if err:
            return None, err

        update_data = {
            'game_data': game_data,
            'odds_event_id': odds_event_id,
            'game_date': game_date_used,
            'home_team': home_team,
            'away_team': away_team,
        }
        ok, save_err = BlogService.update_post(post_id, update_data)
        if save_err:
            return None, save_err

        return {
            'odds_event_id': odds_event_id,
            'game_date': game_date_used,
            'game_data': game_data,
        }, None

    @staticmethod
    def _slugify(title):
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        date_suffix = datetime.now(timezone.utc).strftime('%Y%m%d')
        return f"{slug}-{date_suffix}"

    @staticmethod
    def _save_draft(claude_output, youtube_data, sport=None, sport_key=None,
                    home_team=None, away_team=None, odds_event_id=None,
                    game_date=None, game_data=None):
        base_slug = BlogService._slugify(claude_output.get('title', 'untitled'))

        # Handle slug collisions
        slug = base_slug
        suffix = 2
        while True:
            try:
                with _get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id FROM blog_posts WHERE slug = %s", (slug,))
                        if not cur.fetchone():
                            break
            except Exception as e:
                return None, str(e)
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        published_at_raw = youtube_data.get('published_at')
        youtube_published_at = None
        if published_at_raw:
            try:
                youtube_published_at = datetime.fromisoformat(
                    published_at_raw.replace('Z', '+00:00')
                )
            except ValueError:
                pass

        data = {
            'title': claude_output.get('title', youtube_data['title']),
            'slug': slug,
            'meta_description': (claude_output.get('meta_description') or '')[:200],
            'excerpt': claude_output.get('excerpt'),
            'content': claude_output.get('content'),
            'tags': claude_output.get('tags'),
            'reading_time_minutes': claude_output.get('reading_time_minutes'),
            'og_image_url': youtube_data.get('thumbnail_url'),
            'status': 'draft',
            'youtube_video_id': youtube_data['video_id'],
            'youtube_title': youtube_data['title'],
            'youtube_description': youtube_data.get('description'),
            'youtube_thumbnail_url': youtube_data.get('thumbnail_url'),
            'youtube_published_at': youtube_published_at,
            'sport': sport,
            'sport_key': sport_key,
            'home_team': home_team,
            'away_team': away_team,
            'odds_event_id': odds_event_id,
            'game_date': game_date,
            'game_data': game_data,
            'category': 'preview',
        }
        return BlogService.create_post(data)

    @staticmethod
    def get_published_slugs():
        """Return list of all published post slugs (for sitemap)."""
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT slug FROM blog_posts WHERE status = 'published' ORDER BY published_at DESC"
                    )
                    rows = cur.fetchall()
            return [r['slug'] for r in rows], None
        except Exception as e:
            return [], str(e)
