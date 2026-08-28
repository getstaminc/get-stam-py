"""Stripe billing API routes — checkout and customer-portal session creation."""

import os
from flask import Blueprint, request, jsonify, abort
from dotenv import load_dotenv

from ..services.billing_service import BillingService
from ..services.access_code_service import AccessCodeService
from ..utils.auth_helpers import require_user, serialize_user

load_dotenv()
API_KEY = os.getenv("API_KEY")

billing_bp = Blueprint("billing", __name__)


@billing_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        abort(401)


@billing_bp.route("/api/billing/checkout-session", methods=["POST"])
def checkout_session():
    user = require_user()
    data = request.get_json() or {}
    start_trial = data.get("trial", True)
    url, error = BillingService.create_checkout_session(user, start_trial=start_trial)
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"url": url})


@billing_bp.route("/api/billing/portal-session", methods=["POST"])
def portal_session():
    user = require_user()
    url, error = BillingService.create_portal_session(user)
    if error:
        return jsonify({"error": error}), 400 if error == "no_stripe_customer" else 500
    return jsonify({"url": url})


@billing_bp.route("/api/billing/redeem-code", methods=["POST"])
def redeem_code():
    user = require_user()
    data = request.get_json() or {}
    updated_user, error = AccessCodeService.redeem(user["id"], data.get("code"))
    if error:
        status = 409 if error == "already_redeemed" else 400
        return jsonify({"error": error}), status
    return jsonify({"user": serialize_user(updated_user)})
