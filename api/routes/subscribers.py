"""Public subscriber endpoint — NO X-API-KEY guard."""

import re
import logging
from flask import Blueprint, request, jsonify

from ..services.email_service import EmailService

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

subscribers_bp = Blueprint("subscribers", __name__)


@subscribers_bp.route("/api/subscribers", methods=["POST"])
def subscribe():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email or not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email address"}), 400

    ok, err = EmailService.subscribe(email)
    if ok:
        return jsonify({"subscribed": True}), 200
    if err == "already_subscribed":
        return jsonify({"error": "You're already subscribed!"}), 409
    logger.error("subscribe endpoint error for %s: %s", email, err)
    return jsonify({"error": "Failed to subscribe. Please try again later."}), 500
