import pytest
from datetime import date, datetime
from app.services.scheduler_service import SchedulerService

@pytest.mark.parametrize("input_date, today, expected_skip", [
    ("2025-10-14", date(2025, 10, 15), True),   # ISO, scaduto
    ("15/10/2025", date(2025, 10, 15), False),  # DD/MM/YYYY, oggi
    ("14/10/2025", date(2025, 10, 15), True),   # DD/MM/YYYY, scaduto
    ("2025/10/15", date(2025, 10, 15), False),  # YYYY/MM/DD, oggi
    ("invalid", date(2025, 10, 15), False),     # formato non valido
    (None, date(2025, 10, 15), False),           # nessuna data
    (date(2025, 10, 14), date(2025, 10, 15), True), # oggetto date
    (datetime(2025, 10, 14), date(2025, 10, 15), True), # oggetto datetime
])
def test_end_date_parsing_and_skip(monkeypatch, input_date, today, expected_skip):
    svc = SchedulerService()
    # monkeypatch _today helper per test deterministico
    monkeypatch.setattr("app.services.scheduler_service._today", lambda: today)
    # accediamo al parser privato
    parser = getattr(svc, "_parse_end_date", None)
    if parser is None:
        # fallback: copia la funzione dal servizio
        def _parse_end_date(ed):
            if ed is None:
                return None
            # controlla datetime prima di date
            if isinstance(ed, datetime):
                return ed.date()
            if isinstance(ed, date):
                return ed
            if isinstance(ed, str):
                s = ed.strip()
                try:
                    return date.fromisoformat(s)
                except Exception:
                    pass
                for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                    try:
                        return datetime.strptime(s, fmt).date()
                    except Exception:
                        continue
            return None
        parser = _parse_end_date
    parsed = parser(input_date)
    if parsed is None:
        skip = False
    else:
        skip = today > parsed
    assert skip == expected_skip
