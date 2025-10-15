"""
Test di configurazione per pytest
"""
import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
import time
from datetime import datetime
import os

from app.main import app
from app.core.config import get_settings

test_results = []


@pytest.fixture
def client():
    """Client di test per FastAPI"""
    return TestClient(app)


@pytest.fixture 
def settings():
    """Configurazioni dell'applicazione"""
    return get_settings()


@pytest.fixture
def sample_query_content():
    """Contenuto di esempio per una query SQL"""
    return """
-- Query di test per gli accessi operatori
-- Questa query estrae gli operatori per ufficio

define OFFICE_PREFIX='77%'  --Obbligatorio: Prefisso ufficio
define STATUS='ACTIVE'      --Opzionale: Status operatore

SELECT 
    trim(id) as "ID",
    trim(operator_name) as "OPERATOR_NAME", 
    trim(status) as "STATUS"
FROM tt_application.operator o
WHERE o.office_id LIKE '&OFFICE_PREFIX'
AND o.status = '&STATUS';
"""


@pytest.fixture
def sample_query_file(tmp_path, sample_query_content):
    """Crea un file query di test temporaneo"""
    query_file = tmp_path / "test_query.sql"
    query_file.write_text(sample_query_content, encoding='utf-8')
    return query_file


@pytest.fixture(scope="session")
def event_loop():
    """Event loop per test asincroni"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def pytest_runtest_logreport(report):
    if report.when == "call":
        test_results.append({
            "name": report.nodeid,
            "outcome": report.outcome,
            "duration": f"{report.duration:.2f}s"
        })


def pytest_sessionfinish(session, exitstatus):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join(os.path.dirname(__file__), f'verbale_test_{timestamp}.md')
    pass_count = sum(1 for r in test_results if r["outcome"] == "passed")
    fail_count = sum(1 for r in test_results if r["outcome"] == "failed")
    error_count = sum(1 for r in test_results if r["outcome"] == "error")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f'# Verbale Test - {timestamp}\n\n')
        for r in test_results:
            f.write(f'- **{r["name"]}**: {r["outcome"]} (Durata: {r["duration"]})\n')
        f.write(f'\n**Totali:**\n')
        f.write(f'- Passati: {pass_count}\n')
        f.write(f'- Falliti: {fail_count}\n')
        f.write(f'- Errori: {error_count}\n')
        f.write(f'\n**Exit status:** {exitstatus}\n')
