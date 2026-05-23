"""Admin blog API routes — X-API-KEY guarded."""

import os
import re
import requests as http_requests
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ..services.blog_service import BlogService

load_dotenv()
API_KEY = os.getenv("API_KEY")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")

admin_blog_bp = Blueprint("admin_blog", __name__)


@admin_blog_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)


# ---------------------------------------------------------------------------
# Posts CRUD
# ---------------------------------------------------------------------------

@admin_blog_bp.route("/api/admin/blog/posts", methods=["GET"])
def list_all_posts():
    posts, err = BlogService.get_all_posts_admin()
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"posts": posts, "count": len(posts)})


@admin_blog_bp.route("/api/admin/blog/posts/<int:post_id>", methods=["GET"])
def get_post_admin(post_id):
    try:
        import psycopg2
        import psycopg2.extras
        DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
        with psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM blog_posts WHERE id = %s", (post_id,))
                row = cur.fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        data = {k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in dict(row).items()}
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_blog_bp.route("/api/admin/blog/posts", methods=["POST"])
def create_post():
    data = request.get_json()
    if not data or not data.get("title") or not data.get("slug"):
        return jsonify({"error": "title and slug are required"}), 400
    post_id, err = BlogService.create_post(data)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"id": post_id}), 201


@admin_blog_bp.route("/api/admin/blog/posts/<int:post_id>", methods=["PUT"])
def update_post(post_id):
    data = request.get_json()
    ok, err = BlogService.update_post(post_id, data or {})
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"updated": ok})


@admin_blog_bp.route("/api/admin/blog/posts/<int:post_id>/publish", methods=["POST"])
def publish_post(post_id):
    ok, err = BlogService.publish_post(post_id)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"published": ok})


@admin_blog_bp.route("/api/admin/blog/posts/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    ok, err = BlogService.delete_post(post_id)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"deleted": ok})


@admin_blog_bp.route("/api/admin/blog/posts/<int:post_id>/fetch-game-data", methods=["POST"])
def fetch_game_data(post_id):
    """Re-fetch game data for a blog post using optional overrides."""
    import psycopg2
    import psycopg2.extras

    body = request.get_json() or {}

    # Load existing post to get sport/teams if not overridden
    DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
    try:
        with psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT sport, sport_key, home_team, away_team, game_date FROM blog_posts WHERE id = %s",
                    (post_id,)
                )
                row = cur.fetchone()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not row:
        return jsonify({"error": "Post not found"}), 404

    sport = body.get('sport') or row['sport']
    sport_key = body.get('sport_key') or row['sport_key']
    home_team = body.get('home_team') or row['home_team']
    away_team = body.get('away_team') or row['away_team']
    game_date = body.get('game_date') or (str(row['game_date']) if row['game_date'] else None)

    if not sport or not home_team or not away_team:
        return jsonify({"error": "sport, home_team, and away_team are required"}), 400

    result, err = BlogService.fetch_and_save_game_data(
        post_id, sport, sport_key, home_team, away_team, game_date
    )
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"success": True, **result})


# ---------------------------------------------------------------------------
# Generate from YouTube URL
# ---------------------------------------------------------------------------

_VIDEO_ID_RE = re.compile(
    r'(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})'
)


@admin_blog_bp.route("/api/admin/blog/from-youtube", methods=["POST"])
def from_youtube():
    body = request.get_json() or {}
    raw = body.get("youtube_url") or body.get("video_id", "")

    # If it's already an 11-char ID, use it directly
    if re.match(r'^[A-Za-z0-9_-]{11}$', raw):
        video_id = raw
    else:
        m = _VIDEO_ID_RE.search(raw)
        if not m:
            return jsonify({"error": "Could not extract a video ID from the provided value"}), 400
        video_id = m.group(1)

    post_id, err = BlogService.generate_from_youtube(video_id)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"post_id": post_id, "video_id": video_id}), 201


# ---------------------------------------------------------------------------
# WebSub subscription
# ---------------------------------------------------------------------------

@admin_blog_bp.route("/api/admin/blog/subscribe-youtube", methods=["POST"])
def subscribe_youtube():
    if not YOUTUBE_CHANNEL_ID:
        return jsonify({"error": "YOUTUBE_CHANNEL_ID is not configured"}), 500

    callback_url = os.getenv(
        "WEBHOOK_CALLBACK_URL",
        "https://www.getstam.com/api/webhooks/youtube",
    )
    topic = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={YOUTUBE_CHANNEL_ID}"

    try:
        resp = http_requests.post(
            "https://pubsubhubbub.appspot.com/subscribe",
            data={
                "hub.callback": callback_url,
                "hub.mode": "subscribe",
                "hub.topic": topic,
                "hub.verify_token": WEBHOOK_VERIFY_TOKEN,
                "hub.lease_seconds": "864000",
            },
            timeout=10,
        )
        if resp.status_code in (200, 202, 204):
            return jsonify({"subscribed": True, "hub_status": resp.status_code})
        return jsonify({
            "error": f"Hub returned {resp.status_code}",
            "body": resp.text[:300],
        }), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500
