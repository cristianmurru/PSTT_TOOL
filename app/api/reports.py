from fastapi import APIRouter, Query
from datetime import date, datetime
from typing import Optional
from loguru import logger

from app.services.daily_report_service import DailyReportService
from app.core.config import get_settings

router = APIRouter()

@router.get("/daily", tags=["reports"])
def preview_daily_report(date_str: Optional[str] = Query(None, alias="date")):
    """Preview del report giornaliero (HTML).
    - Parametro opzionale `date=YYYY-MM-DD`.
    """
    try:
        d = date.today()
        if date_str:
            try:
                d = date.fromisoformat(date_str)
            except Exception:
                pass
        svc = DailyReportService()
        payload = svc.generate(d)
        return {
            "date": payload["date"],
            "items_count": payload["items_count"],
            "html": payload["body_html"],
        }
    except Exception as e:
        logger.error(f"[REPORTS] Errore preview: {e}")
        return {"error": str(e)}

@router.post("/daily/send", tags=["reports"])
def send_daily_report(date_str: Optional[str] = Query(None, alias="date")):
    """Invio manuale del report giornaliero.
    - Parametro opzionale `date=YYYY-MM-DD`.
    - Usa destinatari/CC da settings `.env`.
    """
    try:
        d = date.today()
        if date_str:
            try:
                d = date.fromisoformat(date_str)
            except Exception:
                pass
        svc = DailyReportService()
        settings = get_settings()
        payload = svc.generate(d)
        subj = getattr(settings, 'daily_report_subject', 'Report schedulazioni PSTT')
        svc.send_email(
            getattr(settings, 'daily_report_recipients', None),
            getattr(settings, 'daily_report_cc', None),
            subj,
            payload['body_html']
        )
        return {"success": True, "date": d.isoformat()}
    except Exception as e:
        logger.error(f"[REPORTS] Errore invio: {e}")
        return {"success": False, "error": str(e)}
