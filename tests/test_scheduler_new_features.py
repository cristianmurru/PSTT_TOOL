import asyncio
from pathlib import Path
import pytest
from app.services.scheduler_service import SchedulerService

class DummyResult:
    def __init__(self, rows=5):
        self.success = True
        self.row_count = rows
        self.data = [{"a": i, "b": i * 2} for i in range(rows)]
        self.error_message = None

@pytest.mark.asyncio
async def test_run_scheduled_query_creates_temp_and_metrics(monkeypatch, tmp_path):
    svc = SchedulerService()
    # indirizza export_dir al tmp
    monkeypatch.setattr(svc, 'export_dir', tmp_path)
    # patch query_service per evitare accesso DB
    monkeypatch.setattr(svc, 'query_service', type('QS', (), {
        'execute_query': staticmethod(lambda req: DummyResult())
    }))
    # timeout custom (aggiunti dinamicamente, code usa getattr con default)
    setattr(svc.settings, 'scheduler_query_timeout_sec', 5)
    setattr(svc.settings, 'scheduler_write_timeout_sec', 5)

    sched = {
        'query': 'TEST_QUERY.sql',
        'connection': 'TEST_CONN',
        'scheduling_mode': 'classic',
        'hour': 12,
        'minute': 0,
        'output_dir': str(tmp_path),
        'output_filename_template': '{query_name}_{date}.xlsx',
        'output_date_format': '%Y-%m-%d',
    }

    await svc.run_scheduled_query(sched)

    # verifica file finale
    files = list(tmp_path.glob('TEST_QUERY_*'))
    assert files, 'File export finale non trovato'
    # verifica nessun file .tmp residuo se move ok
    assert not list((tmp_path / '_tmp').glob('*.tmp.xlsx')), 'File temporaneo non rimosso'
    # verifica metriche
    metrics_path = tmp_path / 'scheduler_metrics.json'
    assert metrics_path.exists(), 'metrics file mancante'
    import json
    data = json.loads(metrics_path.read_text(encoding='utf-8'))
    assert data, 'metrics vuote'
    last = data[-1]
    assert last['rows'] == 5
    assert last['duration_total_sec'] >= last['duration_query_sec']

@pytest.mark.asyncio
async def test_cleanup_old_exports(monkeypatch, tmp_path):
    svc = SchedulerService()
    monkeypatch.setattr(svc, 'export_dir', tmp_path)
    # crea file vecchio >30 giorni
    old_file = tmp_path / 'old.gz'
    old_file.write_bytes(b'old')
    import time
    past = (time.time() - 60*60*24*40)  # 40 giorni per garantire >30
    os_utime = __import__('os').utime
    os_utime(old_file, (past, past))

    await svc.cleanup_old_exports()

    assert not old_file.exists(), 'cleanup non ha rimosso file >30 giorni'
