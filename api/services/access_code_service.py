"""Access code service — self-serve promo/comp codes that grant Pro access without Stripe."""

import os
import logging
from datetime import datetime

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")


def _get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


class AccessCodeService:

    @staticmethod
    def redeem(user_id, code):
        """Redeem an access code for the given user, granting Pro access. Returns (user_dict, None) or (None, error)."""
        normalized = (code or "").strip().upper()
        if not normalized:
            return None, "invalid_code"

        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT access_code_id FROM users WHERE id = %s", (user_id,))
                    user_row = cur.fetchone()
                    if user_row is None:
                        return None, "invalid_code"
                    if user_row["access_code_id"] is not None:
                        return None, "already_redeemed"

                    cur.execute("SELECT * FROM access_codes WHERE code = %s AND active = true", (normalized,))
                    access_code = cur.fetchone()
                    if not access_code:
                        return None, "invalid_code"
                    if access_code["expires_at"] and access_code["expires_at"] < datetime.utcnow():
                        return None, "expired_code"

                    # Atomically bump redemption_count within the max cap -- guards against two
                    # concurrent redemptions both passing an earlier "is there room?" check.
                    cur.execute("""
                        UPDATE access_codes
                        SET redemption_count = redemption_count + 1
                        WHERE id = %s AND (max_redemptions IS NULL OR redemption_count < max_redemptions)
                    """, (access_code["id"],))
                    if cur.rowcount == 0:
                        return None, "code_fully_redeemed"

                    cur.execute("""
                        UPDATE users
                        SET plan = 'pro', subscription_status = 'comped',
                            access_code_id = %s, access_code_redeemed_at = now(), updated_at = now()
                        WHERE id = %s
                        RETURNING *
                    """, (access_code["id"], user_id))
                    updated_user = cur.fetchone()
                    conn.commit()

            return dict(updated_user), None
        except Exception as e:
            logger.error("AccessCodeService.redeem error: %s", e)
            return None, str(e)
