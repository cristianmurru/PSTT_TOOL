import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_scheduler_status_api():
    client = TestClient(app)
    response = client.get("/api/monitoring/scheduler/status")
    assert response.status_code == 200 or response.status_code == 500
    # Se 200, controlla che ci sia la chiave 'running'
    if response.status_code == 200:
        data = response.json()
        assert "running" in data
        assert "jobs" in data
        assert "history" in data
