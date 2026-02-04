import asyncio
from datetime import datetime
import pytest
from app.services.scheduler_service import SchedulerService


class DummyResult:
    def __init__(self, rows=3, success=True, error_message=None):
        self.success = success
        self.row_count = rows
        self.data = [{"id": i, "v": i * 2} for i in range(rows)]
        self.error_message = error_message


@pytest.mark.asyncio
async def test_retry_scheduled_on_query_timeout(monkeypatch, tmp_path):
    svc = SchedulerService()
    # indirizza export dir al tmp
    monkeypatch.setattr(svc, 'export_dir', tmp_path)
    # forza timeout basso
    setattr(svc.settings, 'scheduler_query_timeout_sec', 1)

    # funzione che simula una query lenta oltre il timeout
    def slow_execute(_req):
        import time
        time.sleep(3)
        return DummyResult(rows=1)

    monkeypatch.setattr(svc, 'query_service', type('QS', (), {
        'execute_query': staticmethod(slow_execute)
    }))

    sched = {
        'query': 'TEST_TIMEOUT.sql',
        'connection': 'TEST_CONN',
        'scheduling_mode': 'classic',
        'hour': 12,
        'minute': 0,
        'output_dir': str(tmp_path)
    }

    await svc.run_scheduled_query(sched)

    # history deve avere un evento fail e un retry_scheduled
    assert len(svc.execution_history) >= 2
    last = svc.execution_history[-1]
    prev = svc.execution_history[-2]
    assert last['status'] == 'retry_scheduled'
    assert 'Timeout query' in (last.get('error') or '')
    assert prev['status'] == 'fail'


@pytest.mark.asyncio
async def test_retry_max_attempts_respected(monkeypatch, tmp_path):
    svc = SchedulerService()
    monkeypatch.setattr(svc, 'export_dir', tmp_path)
    setattr(svc.settings, 'scheduler_retry_enabled', True)
    setattr(svc.settings, 'scheduler_retry_max_attempts', 2)

    sched = {
        'query': 'TEST_MAX.sql',
        'connection': 'TEST_CONN',
        'retry_attempt': 2,
        'sharing_mode': 'filesystem'
    }

    # non deve creare eventi quando max tentativi già raggiunto
    await svc._schedule_retry(sched, datetime.now(), 'error')
    assert len(svc.execution_history) == 0


@pytest.mark.asyncio
async def test_retry_scheduled_on_kafka_failure(monkeypatch, tmp_path):
    svc = SchedulerService()
    monkeypatch.setattr(svc, 'export_dir', tmp_path)

    # query veloce con dati
    monkeypatch.setattr(svc, 'query_service', type('QS', (), {
        'execute_query': staticmethod(lambda req: DummyResult(rows=5))
    }))

    # forza failure in export Kafka
    async def fake_kafka_export(**kwargs):
        raise Exception('Kafka export failed: simulated')

    monkeypatch.setattr(svc, '_execute_kafka_export', fake_kafka_export)

    sched = {
        'query': 'TEST_KAFKA.sql',
        'connection': 'TEST_CONN',
        'scheduling_mode': 'classic',
        'hour': 1,
        'minute': 0,
        'output_dir': str(tmp_path),
        'sharing_mode': 'kafka',
        'kafka_topic': 'test-topic',
        'kafka_connection': 'Kafka-COL'
    }

    await svc.run_scheduled_query(sched)

    # ultimo evento è retry_scheduled e l'evento precedente è stato segnato fail
    assert len(svc.execution_history) >= 2
    last = svc.execution_history[-1]
    prev = svc.execution_history[-2]
    assert last['status'] == 'retry_scheduled'
    assert 'Kafka export failed' in (last.get('error') or '')
    assert prev['status'] == 'fail'
