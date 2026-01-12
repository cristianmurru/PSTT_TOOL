"""
API endpoints per il sistema di scheduling (stub)
"""
from fastapi import APIRouter, HTTPException, status, Request, Body
from fastapi.responses import JSONResponse
import json
from app.core.config import get_settings
from pathlib import Path
from app.services.scheduler_service import SchedulerService
from apscheduler.triggers.cron import CronTrigger
import asyncio
from typing import Dict, Any
from fastapi import Body
from app.models.scheduling import SchedulingItem
import re
import json
from loguru import logger

router = APIRouter()


@router.get("/", summary="Lista schedule")
async def get_schedules():
    """
    Ottiene la lista delle query schedulate
    """
    return {
        "schedules": [],
        "total_count": 0,
        "message": "Scheduler non ancora implementato"
    }


@router.get("/jobs", summary="Lista job executions")
async def get_jobs():
    """
    Ottiene la lista delle esecuzioni dei job
    """
    # If scheduler service available, return real jobs with trigger info
    from fastapi import Request
    # attempt to access app state via a Request is not available here; instead try get_settings fallback
    try:
        # import app to access state
        from fastapi import current_app
        app = current_app._get_current_object()
        if hasattr(app.state, 'scheduler_service') and getattr(app.state.scheduler_service, 'scheduler', None):
            sched = app.state.scheduler_service.scheduler
            jobs = []
            for j in sched.get_jobs():
                jobs.append({
                    'id': j.id,
                    'name': j.name,
                    'next_run_time': j.next_run_time.isoformat() if j.next_run_time else None,
                    'trigger': str(j.trigger)
                })
            return {'jobs': jobs, 'total_count': len(jobs)}
    except Exception:
        # fallthrough to default
        pass
    return {
        "jobs": [],
        "total_count": 0,
        "message": "Scheduler non ancora implementato o non attivo"
    }


@router.get("/scheduling", summary="Elenco schedulazioni")
async def get_scheduling():
    settings = get_settings()
    return {"scheduling": getattr(settings, "scheduling", [])}





@router.put("/scheduling/{idx}", summary="Modifica schedulazione esistente")
async def update_scheduling(idx: int, request: Request, payload: Dict[str, Any] = Body(...)):
    settings = get_settings()
    scheduling = getattr(settings, 'scheduling', [])
    if idx < 0 or idx >= len(scheduling):
        raise HTTPException(status_code=404, detail="Indice schedulazione non trovato")
    # Normalize cron_expression: if user pasted a 6-field cron (includes seconds), convert to 5-field by removing the first token
    cron_normalized = None
    if isinstance(payload, dict) and payload.get('cron_expression'):
        raw = str(payload.get('cron_expression'))
        parts = re.split(r"\s+", raw.strip())
        if len(parts) == 6:
            new_cron = ' '.join(parts[1:6])
            cron_normalized = { 'original': raw, 'normalized': new_cron }
            payload['cron_expression'] = new_cron

    try:
        item = SchedulingItem(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        scheduling[idx] = item.model_dump()
    except Exception:
        scheduling[idx] = item.dict()
    try:
        cf = settings.connections_file
        with open(cf, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['scheduling'] = scheduling
        with open(cf, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        settings.scheduling = scheduling
        reload_scheduler_jobs(request)
        resp = {"message": "Schedulazione aggiornata", "scheduling": scheduling}
        if cron_normalized:
            resp['cron_normalized'] = cron_normalized
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore salvataggio schedulazione: {e}")


@router.delete("/scheduling/{idx}", summary="Elimina schedulazione")
async def delete_scheduling(idx: int, request: Request):
    settings = get_settings()
    scheduling = getattr(settings, 'scheduling', [])
    if idx < 0 or idx >= len(scheduling):
        raise HTTPException(status_code=404, detail="Indice schedulazione non trovato")
    removed = scheduling.pop(idx)
    try:
        cf = settings.connections_file
        with open(cf, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['scheduling'] = scheduling
        with open(cf, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        settings.scheduling = scheduling
        # ricarica jobs
        reload_scheduler_jobs(request)
        return {"message": "Schedulazione rimossa", "removed": removed, "scheduling": scheduling}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore salvataggio schedulazione: {e}")


@router.post("/preview", summary="Anteprima nome file output dalla schedulazione")
async def preview_filename(payload: Dict[str, Any] = Body(...)):
    """Accetta payload con i campi di SchedulingItem e opzionale 'exec_dt' (ISO) per generare il nome file."""
    try:
        exec_dt = None
        if isinstance(payload, dict) and 'exec_dt' in payload:
            from datetime import datetime
            try:
                exec_dt = datetime.fromisoformat(payload.get('exec_dt'))
            except Exception:
                exec_dt = None
            # remove exec_dt before building model
            payload = {k: v for k, v in payload.items() if k != 'exec_dt'}

        item = SchedulingItem(**payload)
        fname = item.render_filename(exec_dt)
        return {"filename": fname}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Endpoint per lo storico schedulazioni
@router.get("/history", summary="Storico schedulazioni (ultimi 30 giorni)")
async def get_scheduler_history():
    export_dir = Path(get_settings().export_dir)
    history_path = export_dir / "scheduler_history.json"
    if not history_path.exists():
        return {"history": [], "total_count": 0}
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history_all = json.load(f)
        # Applica filtro ultimi 30 giorni lato API
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=30)
        history = []
        for h in history_all:
            try:
                ts = h.get("timestamp")
                if ts:
                    dt = datetime.fromisoformat(ts)
                    if dt >= cutoff:
                        history.append(h)
                else:
                    # se timestamp mancante, includi per compatibilità
                    history.append(h)
            except Exception:
                # se parsing timestamp fallisce, includi comunque
                history.append(h)
        return {"history": history, "total_count": len(history)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Errore lettura storico: {e}"})


def reload_scheduler_jobs(request: Request):
    # Se il TestClient non ha il service nello state, esci silenziosamente
    if not hasattr(request.app.state, 'scheduler_service'):
        return
    scheduler_service = request.app.state.scheduler_service
    if not getattr(scheduler_service, 'scheduler', None):
        return
    try:
        scheduler_service.scheduler.remove_all_jobs()
    except Exception:
        pass
    scheduling = getattr(scheduler_service.settings, 'scheduling', [])
    for sched in scheduling:
        try:
            # Respect scheduling_mode: if 'cron' use cron_expression, otherwise build from hour/minute/days
            mode = sched.get('scheduling_mode', 'classic')
            if mode == 'cron' and sched.get('cron_expression'):
                try:
                    trigger = CronTrigger.from_crontab(sched.get('cron_expression'))
                except Exception:
                    # fallback: try to parse as cron kwargs or skip
                    trigger = None
                    logger.exception(f"Impossibile parsare cron_expression per sched: {sched.get('cron_expression')}")
            else:
                trigger_args = {}
                if sched.get('hour') is not None:
                    trigger_args['hour'] = sched.get('hour')
                if sched.get('minute') is not None:
                    trigger_args['minute'] = sched.get('minute')
                if sched.get('second') is not None:
                    trigger_args['second'] = sched.get('second')
                days = sched.get('days_of_week')
                if days:
                    trigger_args['day_of_week'] = ','.join(str(d) for d in days)
                # if no trigger args, leave trigger None and skip
                trigger = CronTrigger(**trigger_args) if trigger_args else None

            if not trigger:
                logger.warning(f"Schedulazione priva di trigger valido per job {sched.get('query')}, skipping")
                continue

            scheduler_service.scheduler.add_job(
                scheduler_service.run_scheduled_query,
                trigger,
                args=[sched],
                name=f"Export {sched.get('query')} on {sched.get('connection')}",
                misfire_grace_time=600,
                coalesce=True
            )
        except Exception:
            logger.exception(f"Impossibile aggiungere job per sched: {sched}")
    # Cleanup job
    try:
        scheduler_service.scheduler.add_job(
            lambda: asyncio.create_task(scheduler_service.cleanup_old_exports()),
            CronTrigger(hour=7, minute=0),
            name="Cleanup old exports"
        )
    except Exception:
        pass


@router.post("/scheduling", summary="Aggiungi una nuova schedulazione")
async def add_scheduling(request: Request, payload: Dict[str, Any] = Body(...)):
    settings = get_settings()
    # valida payload con Pydantic
    # Normalize cron_expression similarly to update: reject or convert 6-field cron (seconds)
    cron_normalized = None
    if isinstance(payload, dict) and payload.get('cron_expression'):
        raw = str(payload.get('cron_expression'))
        parts = re.split(r"\s+", raw.strip())
        if len(parts) == 6:
            # auto-convert by removing the leading seconds field
            new_cron = ' '.join(parts[1:6])
            cron_normalized = { 'original': raw, 'normalized': new_cron }
            payload['cron_expression'] = new_cron

    try:
        item = SchedulingItem(**payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    scheduling = getattr(settings, 'scheduling', [])
    # usa model_dump per compatibilità pydantic v2
    try:
        scheduling.append(item.model_dump())
    except Exception:
        scheduling.append(item.dict())
    # persist su file connections.json
    try:
        cf = settings.connections_file
        with open(cf, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['scheduling'] = scheduling
        with open(cf, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        # aggiorna in-memory
        settings.scheduling = scheduling
        # ricarica jobs (solo se presente lo scheduler service)
        try:
            reload_scheduler_jobs(request)
        except Exception:
            logger.warning('reload_scheduler_jobs non eseguito (probabilmente TestClient senza lifespan)')
        resp = {"message": "Schedulazione aggiunta", "scheduling": scheduling}
        if cron_normalized:
            resp['cron_normalized'] = cron_normalized
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore salvataggio schedulazione: {e}")
    # legacy trailing code removed after refactor


@router.post("/cleanup-test", summary="Rimuove schedulazioni e storico di test")
async def cleanup_test(request: Request, payload: Dict[str, Any] | None = Body(None)):
    """Rimuove schedulazioni di test (es. query che iniziano con 'test_' o 'test_query.sql') e ripulisce lo storico.
    Parametri opzionali nel payload:
      - pattern: regex per identificare le query da rimuovere (default: ^(test_|.*test_.*|test_query\.sql)$)
      - dry_run: se True, mostra cosa verrebbe rimosso senza applicare
    """
    settings = get_settings()
    sched = getattr(settings, 'scheduling', [])
    pattern = r"^(test_|.*test_.*|test_query\.sql)$"
    dry_run = False
    if isinstance(payload, dict):
        if 'pattern' in payload and payload['pattern']:
            pattern = str(payload['pattern'])
        dry_run = bool(payload.get('dry_run', False))
    try:
        to_remove_idx = []
        for i, s in enumerate(sched):
            q = s.get('query', '') or ''
            if re.match(pattern, q, flags=re.IGNORECASE):
                to_remove_idx.append(i)
        removed = [sched[i] for i in to_remove_idx]
        if not dry_run and to_remove_idx:
            # crea nuovo elenco senza gli elementi rimossi
            new_sched = [s for i, s in enumerate(sched) if i not in to_remove_idx]
            # persisti su connections.json
            cf = settings.connections_file
            with open(cf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['scheduling'] = new_sched
            with open(cf, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            # aggiorna in-memory
            settings.scheduling = new_sched
            # ricarica i job
            try:
                reload_scheduler_jobs(request)
            except Exception:
                logger.warning('reload_scheduler_jobs non eseguito durante cleanup-test')
            # ripulisci storico
            export_dir = Path(get_settings().export_dir)
            history_path = export_dir / "scheduler_history.json"
            try:
                if history_path.exists():
                    with open(history_path, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                    filtered = []
                    for h in history:
                        q = h.get('query', '') or ''
                        if not re.match(pattern, q, flags=re.IGNORECASE):
                            filtered.append(h)
                    with open(history_path, 'w', encoding='utf-8') as f:
                        json.dump(filtered, f, indent=2)
            except Exception as e:
                logger.warning(f"Ripulitura storico fallita: {e}")
        return {
            'pattern': pattern,
            'dry_run': dry_run,
            'removed_count': len(removed),
            'removed': removed if dry_run else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore cleanup test: {e}")
