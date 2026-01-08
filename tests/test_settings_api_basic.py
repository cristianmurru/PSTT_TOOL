from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings


def test_settings_env_read_and_write_roundtrip(tmp_path):
    client = TestClient(app)
    # Read current values and path
    res = client.get("/api/settings/env")
    assert res.status_code == 200
    data = res.json()
    env_path = Path(data["env_path"]) if "env_path" in data else get_settings().base_dir / ".env"

    # Backup existing .env content (if any)
    original = env_path.read_text(encoding="utf-8") if env_path.exists() else None

    try:
        # Write a few keys
        payload = {
            "smtp_host": "smtp.test.local",
            "smtp_port": "2525",
            "smtp_user": "",
            "smtp_password": "",
            "smtp_from": "pstt@test.local",
            "daily_report_enabled": "true",
            "daily_report_cron": "",
            "daily_reports_hour": "7",
            "daily_report_recipients": "user1@test|user2@test",
            "daily_report_cc": "",
            "daily_report_subject": "Report schedulazioni PSTT",
            "daily_report_tail_lines": "25",
        }
        r2 = client.post("/api/settings/env", json=payload)
        assert r2.status_code == 200
        j = r2.json()
        assert j.get("success") is True
        # Verify .env was written with expected lines
        text = env_path.read_text(encoding="utf-8")
        assert "smtp_host=smtp.test.local" in text
        assert "smtp_port=2525" in text
        assert "smtp_from=pstt@test.local" in text
        assert "DAILY_REPORT_ENABLED=true" in text
        assert "DAILY_REPORTS_HOUR=7" in text
        assert "DAILY_REPORT_RECIPIENTS=user1@test|user2@test" in text
        assert "DAILY_REPORT_SUBJECT=Report schedulazioni PSTT" in text
    finally:
        # Restore previous .env content to avoid side effects
        if original is None:
            try:
                env_path.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            env_path.write_text(original, encoding="utf-8")
