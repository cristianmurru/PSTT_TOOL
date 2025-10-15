import pytest
from datetime import date, datetime
from app.services.scheduler_service import SchedulerService

class DummyResult:
    def __init__(self):
        self.success = True
        self.data = []
        self.row_count = 0
        self.error_message = None


def test_run_scheduled_query_skips_when_end_date_passed(monkeypatch, tmp_path):
    svc = SchedulerService()
    # patch settings export_dir to tmp
    monkeypatch.setattr(svc, 'export_dir', tmp_path)
    # set today via helper
    monkeypatch.setattr('app.services.scheduler_service._today', lambda: date(2025,10,15))
    called = {'executed': False}

    def fake_execute(req_obj):
        called['executed'] = True
        return DummyResult()

    monkeypatch.setattr(svc, 'query_service', type('Q', (), {'execute_query': staticmethod(fake_execute)}))

    # passata a run_scheduled_query una sched con end_date passato
    sched = {'query': 'Q.sql', 'connection': 'A00', 'end_date': '14/10/2025'}
    # run (sync call to coroutine)
    import asyncio
    asyncio.get_event_loop().run_until_complete(svc.run_scheduled_query(sched))

    assert called['executed'] is False


def test_run_scheduled_query_executes_when_end_date_future(monkeypatch, tmp_path):
    svc = SchedulerService()
    monkeypatch.setattr(svc, 'export_dir', tmp_path)
    monkeypatch.setattr('app.services.scheduler_service._today', lambda: date(2025,10,15))
    called = {'executed': False}

    def fake_execute(req_obj):
        called['executed'] = True
        return DummyResult()

    monkeypatch.setattr(svc, 'query_service', type('Q', (), {'execute_query': staticmethod(fake_execute)}))

    sched = {'query': 'Q.sql', 'connection': 'A00', 'end_date': '16/10/2025'}
    import asyncio
    asyncio.get_event_loop().run_until_complete(svc.run_scheduled_query(sched))

    assert called['executed'] is True
