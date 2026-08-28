"""Stripe billing webhook — NO X-API-KEY guard, verified via Stripe-Signature instead."""

import os
import logging

import stripe
from flask import Blueprint, request, Response
from dotenv import load_dotenv

from ...services.billing_service import BillingService

load_dotenv()
logger = logging.getLogger(__name__)

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

stripe_webhook_bp = Blueprint("stripe_webhook", __name__)


@stripe_webhook_bp.route("/api/webhooks/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning("Stripe webhook signature verification failed: %s", e)
        return Response("Invalid signature", status=400)

    ok, error = BillingService.handle_webhook_event(event)
    if not ok:
        logger.error("Stripe webhook handling failed for event %s: %s", event["id"], error)
        return Response("Error processing event", status=500)

    return Response("OK", status=200)
