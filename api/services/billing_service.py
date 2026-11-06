"""Stripe billing service — checkout/portal session creation and webhook event processing."""

import os
import logging
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import stripe
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://www.getstam.com")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
ADMIN_NOTIFY_EMAIL = os.getenv("ADMIN_NOTIFY_EMAIL", "info@getstam.com")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Hosts we're willing to send a user back to after Stripe Checkout/Portal. Stripe redirects
# via a full page load, so the return URL must land on the *same origin* the user started on
# — otherwise their auth token (in that origin's localStorage) isn't there and they look
# logged out. Keeping this list aligned with the CORS origins in app.py plus the apex domain.
_ALLOWED_RETURN_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "https://getstam.com",
    "https://www.getstam.com",
}


def resolve_return_base(origin):
    """Base URL for Stripe return links: the caller's own Origin when it's a known one (so they
    come back to the exact host + localStorage they left from), else SITE_BASE_URL."""
    if origin and origin.rstrip("/") in _ALLOWED_RETURN_ORIGINS:
        return origin.rstrip("/")
    return SITE_BASE_URL


def resolve_return_path(path):
    """Path to send the user back to after Stripe — the page they started on. Only plain
    same-site paths are accepted ("//host" or backslashes could point off-site); else home."""
    if isinstance(path, str) and path.startswith("/") and not path.startswith("//") and "\\" not in path:
        return path
    return "/"


def _with_param(path, param):
    return f"{path}{'&' if '?' in path else '?'}{param}"


def _notify_admin(subject, livemode, lines):
    """Email the team about a billing event. Non-fatal — a failed send never fails the webhook.
    Sandbox events (local `stripe listen`) are tagged [TEST] so they aren't mistaken for real money."""
    from .email_service import EmailService

    if not livemode:
        subject = f"[TEST] {subject}"
    html = "".join(f"<p>{line}</p>" for line in lines)
    ok, err = EmailService.send_digest_to_one(ADMIN_NOTIFY_EMAIL, subject, html)
    if not ok:
        logger.error("Admin billing notification failed: %s", err)


def _get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def _sget(obj, key, default=None):
    """obj.get(key) equivalent for Stripe SDK objects — their StripeObject class supports
    bracket access and `in`, but not .get(), which raises AttributeError instead of returning
    a default."""
    return obj[key] if obj is not None and key in obj else default


class BillingService:

    @staticmethod
    def create_checkout_session(user, start_trial=True, origin=None, return_path=None):
        """Returns (checkout_url, error). start_trial=False charges immediately with no trial period.
        origin is the caller's Origin header — the user is returned to that host when it's known —
        and return_path the page they started checkout from (home if missing or not same-site)."""
        return_url = f"{resolve_return_base(origin)}{resolve_return_path(return_path)}"
        try:
            kwargs = {
                "mode": "subscription",
                "line_items": [{"price": STRIPE_PRICE_ID, "quantity": 1}],
                "client_reference_id": str(user["id"]),
                "metadata": {"user_id": str(user["id"])},
                "success_url": _with_param(return_url, "checkout=success"),
                "cancel_url": _with_param(return_url, "checkout=cancel"),
            }
            if start_trial:
                kwargs["subscription_data"] = {"trial_period_days": 7}
            if user.get("stripe_customer_id"):
                kwargs["customer"] = user["stripe_customer_id"]
            else:
                kwargs["customer_email"] = user["email"]

            session = stripe.checkout.Session.create(**kwargs)
            return session.url, None
        except Exception as e:
            logger.error("create_checkout_session error: %s", e)
            return None, str(e)

    @staticmethod
    def create_portal_session(user, origin=None, return_path=None):
        """Returns (portal_url, error)."""
        if not user.get("stripe_customer_id"):
            return None, "no_stripe_customer"
        try:
            session = stripe.billing_portal.Session.create(
                customer=user["stripe_customer_id"],
                return_url=f"{resolve_return_base(origin)}{resolve_return_path(return_path)}",
            )
            return session.url, None
        except Exception as e:
            logger.error("create_portal_session error: %s", e)
            return None, str(e)

    @staticmethod
    def handle_webhook_event(event):
        """Idempotently apply a verified Stripe event to the users table. Returns (True, None) or (False, error)."""
        event_id = event["id"]
        event_type = event["type"]
        event_created = event["created"]
        obj = event["data"]["object"]
        previous = _sget(event["data"], "previous_attributes") or {}
        notification = None

        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO processed_stripe_events (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
                        (event_id,),
                    )
                    is_new = cur.rowcount > 0

                    if is_new:
                        if event_type == "checkout.session.completed":
                            notification = BillingService._apply_checkout_completed(cur, obj, event_created)
                        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
                            notification = BillingService._apply_subscription_status(
                                cur, obj, event_type, event_created, previous
                            )

                    conn.commit()
        except Exception as e:
            logger.error("handle_webhook_event error: %s", e)
            return False, str(e)

        # Sent only after the commit, and only for a new event, so a Stripe retry never re-sends.
        if notification:
            _notify_admin(notification[0], _sget(event, "livemode", False), notification[1])
        return True, None

    @staticmethod
    def _apply_checkout_completed(cur, obj, event_created):
        user_id = _sget(obj, "client_reference_id") or _sget(_sget(obj, "metadata"), "user_id")
        if not user_id:
            logger.warning("checkout.session.completed with no client_reference_id/metadata.user_id")
            return

        # subscription_status must be set here too, not left to wait for a later
        # customer.subscription.updated event -- that event can be unsubscribed,
        # delayed, or fail signature checks independently of this one, leaving
        # plan='pro' with subscription_status=NULL (effective_plan() reads as free).
        subscription_id = _sget(obj, "subscription")
        status = "active"
        trial_ends_at = None
        if subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                status = subscription["status"]
                trial_end = subscription["trial_end"]
                trial_ends_at = datetime.fromtimestamp(trial_end, tz=timezone.utc) if trial_end else None
            except Exception as e:
                logger.error("Failed to retrieve subscription %s for checkout completion: %s", subscription_id, e)

        cur.execute("""
            UPDATE users
            SET stripe_customer_id = %s, stripe_subscription_id = %s, plan = 'pro',
                subscription_status = %s, trial_ends_at = %s,
                stripe_event_created_at = %s, updated_at = now()
            WHERE id = %s AND (stripe_event_created_at IS NULL OR stripe_event_created_at <= %s)
        """, (_sget(obj, "customer"), subscription_id, status, trial_ends_at,
              event_created, int(user_id), event_created))

        email = _sget(_sget(obj, "customer_details"), "email") or _sget(obj, "customer_email") or f"user #{user_id}"
        if status == "trialing":
            trial_note = f" — trial ends {trial_ends_at:%b %d, %Y}" if trial_ends_at else ""
            return (f"New GetSTAM Pro signup (free trial): {email}",
                    [f"{email} started a Pro free trial{trial_note}.",
                     "They'll be charged automatically when the trial ends unless they cancel."])
        return (f"New GetSTAM Pro subscriber: {email}",
                [f"{email} subscribed to Pro and was charged today (status: {status})."])

    @staticmethod
    def _apply_subscription_status(cur, obj, event_type, event_created, previous=None):
        customer_id = _sget(obj, "customer")
        if not customer_id:
            return
        status = "canceled" if event_type == "customer.subscription.deleted" else _sget(obj, "status")
        trial_end = _sget(obj, "trial_end")
        trial_ends_at = datetime.fromtimestamp(trial_end, tz=timezone.utc) if trial_end else None
        cur.execute("""
            UPDATE users
            SET subscription_status = %s, trial_ends_at = %s, stripe_event_created_at = %s, updated_at = now()
            WHERE stripe_customer_id = %s AND (stripe_event_created_at IS NULL OR stripe_event_created_at <= %s)
            RETURNING email
        """, (status, trial_ends_at, event_created, customer_id, event_created))

        # A trial turning into a paying subscription is the moment money actually changes hands.
        if _sget(previous, "status") == "trialing" and status == "active":
            row = cur.fetchone()
            email = (row or {}).get("email") or customer_id
            return (f"GetSTAM Pro trial converted to paid: {email}",
                    [f"{email}'s free trial ended and their first Pro payment went through."])
        return None
