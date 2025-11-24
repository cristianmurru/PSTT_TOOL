from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
r=client.post('/api/scheduler/scheduling', json={"query":"test_query.sql","hour":10,"minute":30,"connection":"test_conn"})
print('status', r.status_code)
print(r.text)
