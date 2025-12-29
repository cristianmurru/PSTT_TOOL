import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_add_edit_delete_schedule():
    client = TestClient(app)
    # Add
    new_sched = {"query": "test_query.sql", "hour": 10, "minute": 30, "connection": "test_conn"}
    r = client.post("/api/scheduler/scheduling", json=new_sched)
    assert r.status_code == 200
    data = r.json()
    assert any(s["query"] == "test_query.sql" for s in data["scheduling"])
    idx = next(i for i,s in enumerate(data["scheduling"]) if s["query"] == "test_query.sql")
    # Edit
    edit_sched = {"query": "test_query.sql", "hour": 11, "minute": 45, "connection": "test_conn2"}
    r = client.put(f"/api/scheduler/scheduling/{idx}", json=edit_sched)
    assert r.status_code == 200
    data = r.json()
    assert data["scheduling"][idx]["hour"] == 11
    # Delete
    r = client.delete(f"/api/scheduler/scheduling/{idx}")
    assert r.status_code == 200
    data = r.json()
    # Verifica che sia stata rimossa solo la schedulazione target
    remaining = [s for s in data["scheduling"] if s["query"] == "test_query.sql"]
    # non deve esistere la versione modificata (conn test_conn2)
    assert not any(s["query"] == "test_query.sql" and s.get("connection") == "test_conn2" for s in remaining)
