import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings

client = TestClient(app)


def test_preview_filename():
    payload = {
        "query": "MYQ.sql",
        "connection": "A00",
        "output_filename_template": "{query_name}_{date}.xlsx",
        "output_date_format": "%Y-%m-%d"
    }
    resp = client.post('/api/scheduler/preview', json=payload)
    assert resp.status_code == 200
    assert 'filename' in resp.json()


def test_add_and_delete_scheduling():
    settings = get_settings()
    # initial count
    initial = len(getattr(settings, 'scheduling', []))
    payload = {
        "query": "NEWQ.sql",
        "connection": "A00",
        "scheduling_mode": "classic",
        "hour": 12,
        "minute": 30
    }
    resp = client.post('/api/scheduler/scheduling', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert 'scheduling' in data
    new_count = len(data['scheduling'])
    assert new_count == initial + 1
    # delete last
    resp2 = client.delete(f"/api/scheduler/scheduling/{new_count-1}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2['message'] == 'Schedulazione rimossa'
