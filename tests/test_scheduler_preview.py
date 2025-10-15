import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_preview_basic():
    client = TestClient(app)
    payload = {
        "query": "sample.sql",
        "connection": "A00",
        "output_filename_template": "{query_name}_{date}.xlsx"
    }
    r = client.post("/api/scheduler/preview", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data
    assert "sample" in data["filename"].lower()


def test_preview_with_exec_dt():
    client = TestClient(app)
    payload = {
        "query": "my-query.sql",
        "connection": "A00",
        "output_filename_template": "{query_name}_{date}.xlsx",
        "exec_dt": "2025-10-11T07:30:00"
    }
    r = client.post("/api/scheduler/preview", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data
    # date should reflect 2025-10-11
    assert "2025-10-11" in data["filename"]


def test_preview_invalid_exec_dt():
    client = TestClient(app)
    payload = {
        "query": "bad.sql",
        "connection": "A00",
        "exec_dt": "not-a-date"
    }
    # invalid exec_dt should not crash; preview should still return 200 using current date
    r = client.post("/api/scheduler/preview", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data
