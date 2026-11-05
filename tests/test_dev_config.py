"""Coverage for /api/dev/config -- tells the frontend whether to show dev-only tools."""
from tests.conftest import make_test_app
from api.routes.dev_config import dev_config_bp


def _client():
    return make_test_app(dev_config_bp).test_client()


def test_dev_tools_enabled_in_development(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")
    resp = _client().get("/api/dev/config")
    assert resp.status_code == 200
    assert resp.get_json() == {"dev_tools": True}


def test_dev_tools_disabled_otherwise(monkeypatch):
    monkeypatch.delenv("FLASK_ENV", raising=False)
    assert _client().get("/api/dev/config").get_json() == {"dev_tools": False}
    monkeypatch.setenv("FLASK_ENV", "production")
    assert _client().get("/api/dev/config").get_json() == {"dev_tools": False}
