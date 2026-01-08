from fastapi.testclient import TestClient
from app.main import app


def test_settings_page_has_gear_icon_and_titles():
    client = TestClient(app)
    r = client.get("/settings")
    assert r.status_code == 200
    html = r.text
    # Inline FA gear glyph present in header
    assert "&#xf013;" in html
    # Section titles styled larger with spacing
    assert "<h2 class=\"text-xl" in html
    assert ">SMTP</h2>" in html
    assert ">Report giornaliero</h2>" in html


def test_logs_page_has_settings_link_with_gear():
    client = TestClient(app)
    r = client.get("/logs")
    assert r.status_code == 200
    html = r.text
    # Navbar includes settings link and inline gear glyph
    assert "/settings" in html
    assert "&#xf013;" in html


def test_scheduler_dashboard_nav_links_present():
    client = TestClient(app)
    r = client.get("/dashboard")
    assert r.status_code == 200
    html = r.text
    # Contains links to Logs and Settings
    assert "/logs" in html
    assert "/settings" in html
