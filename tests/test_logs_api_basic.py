from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings


def test_logs_list_and_read_tail(tmp_path):
    client = TestClient(app)
    settings = get_settings()
    # Ensure log dir exists and has at least one file
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.log_dir / "app.log"
    # Append a few lines to help tail
    log_file.write_text("line1\nline2\nline3\n", encoding="utf-8")

    # List
    r = client.get("/api/logs/list")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("files"), list)

    # Read tail=2 of app.log
    r2 = client.get(f"/api/logs/read?file={log_file.name}&tail=2")
    assert r2.status_code == 200
    txt = r2.text.strip()
    assert txt.endswith("line2\nline3") or txt == "line2\nline3"
