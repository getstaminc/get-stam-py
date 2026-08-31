"""User account API routes — passwordless signup/login via emailed 6-digit codes."""

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ..services.auth_service import AuthService
from ..services.billing_service import BillingService
from ..services.email_service import EmailService
from ..utils.auth_helpers import require_user, serialize_user
from limiter import limiter

load_dotenv()
API_KEY = os.getenv("API_KEY")

auth_bp = Blueprint("auth", __name__)


@auth_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)


def _send_code_email(email, code):
    EmailService.send_digest_to_one(
        email,
        "Your GetSTAM login code",
        f'<p>Your GetSTAM login code is:</p>'
        f'<p style="font-size:28px;font-weight:bold;letter-spacing:4px;">{code}</p>'
        f'<p>This code expires in 10 minutes. If you didn\'t request this, you can ignore this email.</p>',
    )


@auth_bp.route("/api/auth/request-code", methods=["POST"])
@limiter.limit("5 per hour")
def request_code():
    data = request.get_json() or {}
    email = data.get("email")
    user, code, error = AuthService.request_code(
        email, intent=data.get("intent"), require_existing=bool(data.get("require_existing"))
    )
    if error in ("invalid_email", "account_not_found"):
        return jsonify({"error": error}), 404 if error == "account_not_found" else 400
    if error == "rate_limited":
        return jsonify({"error": "Please wait a minute before requesting another code."}), 429
    if error:
        return jsonify({"error": "Could not send login code"}), 500

    _send_code_email(user["email"], code)
    return jsonify({"success": True, "message": "Check your email for a 6-digit code."})


@auth_bp.route("/api/auth/verify-code", methods=["POST"])
@limiter.limit("10 per minute")
def verify_code():
    data = request.get_json() or {}
    user, error, is_first_verification = AuthService.verify_code(data.get("email"), data.get("code"))
    if error:
        if error == "too_many_attempts":
            return jsonify({"error": error}), 429
        if error in ("invalid_code", "expired_code"):
            return jsonify({"error": error}), 400
        # Unexpected (e.g. a DB error surfaced as str(e)) — don't echo internals to the client.
        return jsonify({"error": "Could not verify login code"}), 500

    token = AuthService.issue_token(user)
    response = {"token": token, "user": serialize_user(user)}

    if is_first_verification and user.get("signup_intent") == "trial":
        checkout_url, checkout_error = BillingService.create_checkout_session(user, start_trial=True)
        if checkout_error:
            # Non-fatal — they're still verified and logged in, just land on the site
            # instead of Checkout. They can always start a trial from the Upgrade dialog.
            pass
        else:
            response["checkout_url"] = checkout_url

    return jsonify(response)


@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    user = require_user()
    return jsonify({"user": serialize_user(user)})


@auth_bp.route("/api/auth/me", methods=["PATCH"])
def update_me():
    user = require_user()
    data = request.get_json() or {}
    updated, error = AuthService.update_profile(
        user["id"],
        timezone=data.get("timezone"),
        theme_preference=data.get("theme_preference"),
    )
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"user": serialize_user(updated)})
