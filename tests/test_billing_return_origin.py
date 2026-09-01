"""BillingService.resolve_return_base picks the origin the user actually started on.

Stripe returns the user via a full page load, so the return URL must land on the same
origin their auth token lives in (localStorage). A known Origin header wins; anything
unknown or missing falls back to SITE_BASE_URL.
"""
from api.services.billing_service import resolve_return_base, SITE_BASE_URL


def test_known_origin_is_used():
    assert resolve_return_base("https://www.getstam.com") == "https://www.getstam.com"
    assert resolve_return_base("http://localhost:3000") == "http://localhost:3000"


def test_trailing_slash_is_normalized():
    assert resolve_return_base("https://www.getstam.com/") == "https://www.getstam.com"


def test_unknown_origin_falls_back_to_site_base_url():
    assert resolve_return_base("https://evil.example.com") == SITE_BASE_URL


def test_missing_origin_falls_back_to_site_base_url():
    assert resolve_return_base(None) == SITE_BASE_URL
    assert resolve_return_base("") == SITE_BASE_URL
