import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings


client = TestClient(app)


def test_update_scheduling_normalizes_6_field_cron_and_preserves_conn_query():
    settings = get_settings()
    # assicurati di avere almeno una schedulazione; se vuota, aggiungine una
    if not getattr(settings, 'scheduling', []):
        payload = {
            'query': 'NEW_CRON_TEST.sql',
            'connection': 'A00-CDG-Collaudo',
            'scheduling_mode': 'cron',
            'cron_expression': '0 */2 * * *'
        }
        resp_add = client.post('/api/scheduler/scheduling', json=payload)
        assert resp_add.status_code == 200

    idx = 0
    sched = settings.scheduling[idx]
    original_conn = sched['connection']
    original_query = sched['query']

    # invia una cron a 6 campi: la API deve normalizzare a 5 campi
    update_payload = dict(sched)
    update_payload['scheduling_mode'] = 'cron'
    update_payload['cron_expression'] = '0 */2 * * * *'  # 6 campi (con seconds)

    resp_upd = client.put(f"/api/scheduler/scheduling/{idx}", json=update_payload)
    assert resp_upd.status_code == 200
    data = resp_upd.json()
    assert 'scheduling' in data
    # verifica normalizzazione presente e che abbia 5 campi
    assert 'cron_normalized' in data
    normalized = data['cron_normalized']['normalized']
    assert len(normalized.split()) == 5

    # ricarica settings e verifica che connection/query siano invariati
    updated_sched = get_settings().scheduling[idx]
    assert updated_sched['connection'] == original_conn
    assert updated_sched['query'] == original_query
