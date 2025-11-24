"""
API endpoints per monitoring e health check
"""
import psutil
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Request
from loguru import logger

from app.core.config import get_settings
from app.services.scheduler_service import SchedulerService
from pathlib import Path

router = APIRouter()


@router.get("/health", summary="Health hardware")
async def health_hardware():
    """
    Verifica lo stato di salute dell'applicazione
    """
    try:
        disk = psutil.disk_usage("/")
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        return {
            "app_name": "PSTT Tool v1.0.0",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_available_gb": round(mem.available / (1024**3), 2),
            "cpu_percent": cpu
        }
        
    except Exception as e:
        logger.error(f"Errore in health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Servizio non disponibile: {str(e)}"
        )


@router.get("/stats", summary="Statistiche sistema")
async def system_stats():
    """
    Ottiene statistiche del sistema
    """
    try:
        # Statistiche CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Statistiche memoria
        memory = psutil.virtual_memory()
        
        # Statistiche disco
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count
            },
            "memory": {
                "total_bytes": memory.total,
                "available_bytes": memory.available,
                "used_bytes": memory.used,
                "percent": memory.percent
            },
            "disk": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "percent": (disk.used / disk.total) * 100
            }
        }
        
    except Exception as e:
        logger.error(f"Errore nel recupero statistiche sistema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nel recupero delle statistiche"
        )


@router.get("/scheduler/status", summary="Stato dettagliato scheduler")
async def scheduler_status(request: Request):
    """
    Restituisce lo stato dettagliato del sistema di scheduling
    """
    try:
        app_instance = request.app
        scheduler_service = getattr(app_instance.state, "scheduler_service", None)
        if not scheduler_service:
            logger.warning("SchedulerService non trovato in app.state. Scheduler non attivo o non inizializzato.")
            return {"running": False, "jobs": [], "history": [], "message": "Scheduler non attivo o non inizializzato."}
        jobs = []
        try:
            for job in scheduler_service.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
        except Exception as job_error:
            logger.error(f"Errore nel recupero dei job scheduler: {job_error}")
        status = scheduler_service.get_status() if hasattr(scheduler_service, "get_status") else {}
        return {
            "running": status.get("running", False),
            "active_jobs": status.get("active_jobs", 0),
            "scheduled_jobs": status.get("scheduled_jobs", 0),
            "last_execution": status.get("last_execution"),
            "jobs": jobs,
            "history": status.get("history", []),
            "success_count": status.get("success_count", 0),
            "fail_count": status.get("fail_count", 0),
            "avg_duration_sec": status.get("avg_duration_sec", 0)
        }
    except Exception as e:
        logger.error(f"Errore nel recupero stato scheduler: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel recupero stato scheduler: {str(e)}"
        )
