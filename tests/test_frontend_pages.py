from fastapi.testclient import TestClient
from app.main import app


def test_settings_page_served_and_nav_links():
    client = TestClient(app)
    r = client.get("/settings")
    assert r.status_code == 200
    html = r.text
    assert "Impostazioni" in html
    # navbar coherence: links to Home, Schedulazioni, Log
    assert "/" in html and "/dashboard" in html and "/logs" in html


def test_logs_page_served_and_nav_links():
    client = TestClient(app)
    r = client.get("/logs")
    assert r.status_code == 200
    html = r.text
    assert "Log Viewer" in html
    # navbar coherence: links to Home, Schedulazioni, Settings
    assert "/" in html and "/dashboard" in html and "/settings" in html


def test_scheduler_dashboard_has_links_to_logs_and_settings():
    client = TestClient(app)
    r = client.get("/dashboard")
    assert r.status_code == 200
    html = r.text
    # UI title migrated to Italian; accept either legacy or new title
    assert ("Scheduler Dashboard" in html) or ("Schedulazioni" in html)
    assert "/logs" in html and "/settings" in html
