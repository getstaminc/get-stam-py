"""Public blog API routes."""

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ..services.blog_service import BlogService
from cache import cache

load_dotenv()
API_KEY = os.getenv("API_KEY")

blog_bp = Blueprint("blog", __name__)


@blog_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)


@blog_bp.route("/api/blog/posts", methods=["GET"])
def get_posts():
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)
    category = request.args.get("category") or None
    sport_tag = request.args.get("sport") or None
    posts, err = BlogService.get_published_posts(limit=limit, offset=offset, category=category, sport_tag=sport_tag)
    if err:
        return jsonify({"error": err}), 500
    return jsonify({"posts": posts, "count": len(posts)})


@blog_bp.route("/api/blog/posts/<slug>", methods=["GET"])
def get_post(slug):
    cache_key = f"blog_post_{slug}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    post, err = BlogService.get_post_by_slug(slug)
    if err:
        return jsonify({"error": err}), 500
    if not post:
        return jsonify({"error": "Not found"}), 404
    response = jsonify(post)
    cache.set(cache_key, response, timeout=43200)
    return response
