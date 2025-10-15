import pytest
from app.services.scheduler_service import SchedulerService

def test_scheduler_metrics():
    scheduler = SchedulerService()
    # Simula alcune esecuzioni
    scheduler.execution_history = [
        {"status": "success", "duration_sec": 2.0},
        {"status": "fail", "duration_sec": 1.0},
        {"status": "success", "duration_sec": 3.0},
    ]
    status = scheduler.get_status()
    assert status["success_count"] == 2
    assert status["fail_count"] == 1
    assert abs(status["avg_duration_sec"] - 2.0) < 0.01
