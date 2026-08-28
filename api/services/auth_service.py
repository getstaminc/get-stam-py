"""Auth service — passwordless signup/login via emailed 6-digit codes, stateless bearer
tokens, and profile updates. Entering the code is the only verification step: there's no
separate email-link flow, since receiving the code already proves the user controls the inbox."""

import os
import re
import hmac
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY")

TOKEN_MAX_AGE_SECONDS = 30 * 24 * 60 * 60  # 30 days
CODE_MAX_AGE_SECONDS = 10 * 60  # 10 minutes
MAX_CODE_ATTEMPTS = 5

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PRO_STATUSES = {"trialing", "active", "past_due", "comped"}


def _get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def _auth_serializer():
    return URLSafeTimedSerializer(AUTH_SECRET_KEY, salt="auth")


def _hash_code(code):
    # Keyed hash (not a plain sha256) so read-only DB access alone isn't enough to brute-force
    # a 6-digit code offline -- the attacker would also need AUTH_SECRET_KEY.
    return hmac.new(AUTH_SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def _generate_code():
    return f"{secrets.randbelow(1_000_000):06d}"


class AuthService:

    @staticmethod
    def request_code(email, intent=None, require_existing=False):
        """Create the user if new (unless require_existing), generate+store a hashed 6-digit
        login code, and return the plaintext code for the caller to email (never stored or
        logged in plaintext). Returns (user_dict, code, error) -- error is 'invalid_email',
        'account_not_found' (only possible when require_existing=True), or a generic message.

        require_existing=True is used for the "Log In" entry point specifically: a user who
        pays under one email and mistypes another would otherwise get silently signed up for a
        fresh free account under the typo'd address with no indication anything's wrong. Signup
        keeps the normal unified auto-create behavior -- picking a plan is a deliberate
        "create an account" action, so there's no existing-email confusion to guard against there."""
        email = (email or "").strip().lower()
        if not email or not _EMAIL_RE.match(email):
            return None, None, "invalid_email"
        if intent not in ("trial", None):
            intent = None

        code = _generate_code()
        code_hash = _hash_code(code)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=CODE_MAX_AGE_SECONDS)

        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    if require_existing:
                        cur.execute("""
                            UPDATE users
                            SET login_code_hash = %s, login_code_expires_at = %s, login_code_attempts = 0, updated_at = now()
                            WHERE email = %s
                            RETURNING *
                        """, (code_hash, expires_at, email))
                        row = cur.fetchone()
                        if not row:
                            conn.commit()
                            return None, None, "account_not_found"
                    else:
                        cur.execute("""
                            INSERT INTO users (email, signup_intent, login_code_hash, login_code_expires_at, login_code_attempts)
                            VALUES (%(email)s, %(intent)s, %(code_hash)s, %(expires_at)s, 0)
                            ON CONFLICT (email) DO UPDATE
                            SET login_code_hash = %(code_hash)s, login_code_expires_at = %(expires_at)s,
                                login_code_attempts = 0, updated_at = now()
                            RETURNING *
                        """, {"email": email, "intent": intent, "code_hash": code_hash, "expires_at": expires_at})
                        row = cur.fetchone()
                    conn.commit()
            return dict(row), code, None
        except Exception as e:
            logger.error("AuthService.request_code error: %s", e)
            return None, None, str(e)

    @staticmethod
    def verify_code(email, code):
        """Check a submitted code against the stored hash. Returns (user_dict, error,
        is_first_verification) -- error is 'invalid_code', 'expired_code', 'too_many_attempts',
        or a generic message. is_first_verification is True only the first time an account is
        ever verified (used to decide whether to kick off a signup-time trial checkout)."""
        email = (email or "").strip().lower()
        code = (code or "").strip()
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                    row = cur.fetchone()

                    if not row or not row["login_code_hash"]:
                        return None, "invalid_code", False
                    if row["login_code_attempts"] >= MAX_CODE_ATTEMPTS:
                        return None, "too_many_attempts", False
                    expires_at = row["login_code_expires_at"]
                    if expires_at and expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    if not expires_at or expires_at < datetime.now(timezone.utc):
                        return None, "expired_code", False

                    if not hmac.compare_digest(_hash_code(code), row["login_code_hash"]):
                        cur.execute(
                            "UPDATE users SET login_code_attempts = login_code_attempts + 1 WHERE id = %s",
                            (row["id"],),
                        )
                        conn.commit()
                        return None, "invalid_code", False

                    is_first_verification = row["email_verified_at"] is None
                    cur.execute("""
                        UPDATE users
                        SET login_code_hash = NULL, login_code_expires_at = NULL, login_code_attempts = 0,
                            email_verified_at = COALESCE(email_verified_at, now()), updated_at = now()
                        WHERE id = %s
                        RETURNING *
                    """, (row["id"],))
                    updated = cur.fetchone()
                    conn.commit()
            return dict(updated), None, is_first_verification
        except Exception as e:
            logger.error("AuthService.verify_code error: %s", e)
            return None, str(e), False

    @staticmethod
    def get_user_by_id(user_id):
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                    row = cur.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error("AuthService.get_user_by_id error: %s", e)
            return None

    @staticmethod
    def get_user_by_email(email):
        email = (email or "").strip().lower()
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                    row = cur.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error("AuthService.get_user_by_email error: %s", e)
            return None

    @staticmethod
    def issue_token(user):
        return _auth_serializer().dumps({"uid": user["id"], "tv": user["token_version"]})

    @staticmethod
    def verify_token(token):
        """Verify a bearer token and return the current user row, or None on any failure."""
        if not token:
            return None
        try:
            payload = _auth_serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
        except (BadSignature, SignatureExpired):
            return None

        user = AuthService.get_user_by_id(payload.get("uid"))
        if not user or user["token_version"] != payload.get("tv"):
            return None
        return user

    @staticmethod
    def update_profile(user_id, timezone=None, theme_preference=None):
        fields = []
        values = {}
        if timezone is not None:
            fields.append("timezone = %(timezone)s")
            values["timezone"] = timezone
        if theme_preference is not None:
            if theme_preference not in ("light", "dark"):
                return None, "invalid_theme_preference"
            fields.append("theme_preference = %(theme_preference)s")
            values["theme_preference"] = theme_preference
        if not fields:
            return None, "no_updatable_fields"

        values["id"] = user_id
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        UPDATE users SET {', '.join(fields)}, updated_at = now()
                        WHERE id = %(id)s
                        RETURNING *
                    """, values)
                    row = cur.fetchone()
                    conn.commit()
            return dict(row) if row else None, None
        except Exception as e:
            logger.error("AuthService.update_profile error: %s", e)
            return None, str(e)

    @staticmethod
    def effective_plan(user):
        """'pro' iff the user is on the pro plan with a currently-active-enough Stripe status, else 'free'."""
        if not user:
            return "free"
        if user.get("plan") == "pro" and user.get("subscription_status") in PRO_STATUSES:
            return "pro"
        return "free"
