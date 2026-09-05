"""Shared helpers for resolving the requesting user from an Authorization header."""

from flask import request, abort

from ..services.auth_service import AuthService


def get_bearer_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer "):].strip()


def get_current_user_optional():
    """Returns the user dict for a valid bearer token, or None (anonymous request)."""
    token = get_bearer_token()
    if not token:
        return None
    return AuthService.verify_token(token)


def require_user():
    """Returns the current user dict, or aborts with 401 if the token is missing/invalid."""
    user = get_current_user_optional()
    if not user:
        abort(401)
    return user


def serialize_user(user):
    """Strip sensitive/internal fields before returning a user to the client."""
    return {
        "id": user["id"],
        "email": user["email"],
        "timezone": user["timezone"],
        "theme_preference": user["theme_preference"],
        "plan": AuthService.effective_plan(user),
        "subscription_status": user.get("subscription_status"),
        "trial_ends_at": user["trial_ends_at"].isoformat() if user.get("trial_ends_at") else None,
        "email_verified": bool(user.get("email_verified_at")),
    }
