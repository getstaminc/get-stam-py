"""BillingService.resolve_return_base picks the origin the user actually started on.

Stripe returns the user via a full page load, so the return URL must land on the same
origin their auth token lives in (localStorage). A known Origin header wins; anything
unknown or missing falls back to SITE_BASE_URL.
"""
from api.services.billing_service import resolve_return_base, resolve_return_path, SITE_BASE_URL


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


def test_return_path_keeps_the_page_the_user_was_on():
    assert resolve_return_path("/nba/trends?date=20261105") == "/nba/trends?date=20261105"
    assert resolve_return_path("/") == "/"


def test_return_path_falls_back_to_home_when_missing_or_off_site():
    for bad in (None, "", "nba", "//evil.example.com", "/\\evil.example.com", "https://evil.example.com", 42):
        assert resolve_return_path(bad) == "/"


def test_checkout_returns_to_the_starting_page():
    from unittest.mock import patch, MagicMock
    from api.services.billing_service import BillingService
    with patch("api.services.billing_service.stripe.checkout.Session.create", return_value=MagicMock(url="u")) as create:
        BillingService.create_checkout_session({"id": 1, "email": "a@b.c"}, origin="http://127.0.0.1:5000", return_path="/nba/trends?date=20261105")
    kwargs = create.call_args.kwargs
    assert kwargs["success_url"] == "http://127.0.0.1:5000/nba/trends?date=20261105&checkout=success"
    assert kwargs["cancel_url"] == "http://127.0.0.1:5000/nba/trends?date=20261105&checkout=cancel"


def test_checkout_without_return_path_goes_home():
    from unittest.mock import patch, MagicMock
    from api.services.billing_service import BillingService
    with patch("api.services.billing_service.stripe.checkout.Session.create", return_value=MagicMock(url="u")) as create:
        BillingService.create_checkout_session({"id": 1, "email": "a@b.c"}, origin="http://127.0.0.1:5000")
    assert create.call_args.kwargs["success_url"] == "http://127.0.0.1:5000/?checkout=success"
