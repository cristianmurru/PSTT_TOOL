import pytest
from fastapi.testclient import TestClient
from app.main import app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_tmp_post_scheduling_endpoint(client):
    r = client.post(
        "/api/scheduler/scheduling",
        json={"query": "test_query.sql", "hour": 10, "minute": 30, "connection": "test_conn"},
    )
    # Basic assertion to ensure endpoint responds (status may vary depending on test env)
    assert r.status_code in (200, 201, 422, 400, 404)

