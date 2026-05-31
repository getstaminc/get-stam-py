"""Public subscriber endpoint — NO X-API-KEY guard."""

import re
import base64
import logging
from flask import Blueprint, request, jsonify, make_response

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


@subscribers_bp.route("/api/unsubscribe", methods=["GET"])
def unsubscribe():
    encoded = request.args.get("e", "")
    try:
        # Pad base64 if needed
        padded = encoded + "=" * (-len(encoded) % 4)
        email = base64.urlsafe_b64decode(padded).decode("utf-8").strip().lower()
    except Exception:
        return make_response("Invalid unsubscribe link.", 400, {"Content-Type": "text/plain"})

    if not email or not EMAIL_RE.match(email):
        return make_response("Invalid unsubscribe link.", 400, {"Content-Type": "text/plain"})

    ok, err = EmailService.unsubscribe(email)
    if ok:
        html = """<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;text-align:center;padding:60px 20px;">
<h2>You've been unsubscribed.</h2>
<p style="color:#555;">You won't receive any more daily trends emails from GetSTAM.</p>
</body></html>"""
        return make_response(html, 200, {"Content-Type": "text/html"})

    logger.error("unsubscribe endpoint error for %s: %s", email, err)
    return make_response("Something went wrong. Please try again later.", 500, {"Content-Type": "text/plain"})
