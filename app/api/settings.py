from fastapi import APIRouter
from typing import Dict, Any
from pathlib import Path
from loguru import logger

from app.core.config import get_settings

router = APIRouter()

ALLOWED_KEYS = [
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_password",
    "smtp_from",
    "daily_report_enabled",
    "daily_report_cron",
    "daily_reports_hour",
    "daily_report_recipients",
    "daily_report_cc",
    "daily_report_subject",
    "daily_report_tail_lines",
]


def _env_path() -> Path:
    settings = get_settings()
    # .env at base dir
    return settings.base_dir / ".env"


@router.get("/env", tags=["settings"])
def get_env_settings() -> Dict[str, Any]:
    """Return current settings values for the editable keys."""
    s = get_settings()
    out: Dict[str, Any] = {}
    for k in ALLOWED_KEYS:
        out[k] = getattr(s, k, None)
    return {"values": out, "env_path": str(_env_path())}


@router.post("/env", tags=["settings"])
def update_env_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist provided settings into .env by upserting allowed keys.
    Note: service restart may be required for scheduler to reflect changes.
    """
    # Filter allowed keys
    updates: Dict[str, str] = {}
    for k, v in payload.items():
        if k in ALLOWED_KEYS:
            updates[k] = str(v) if v is not None else ""
    env_file = _env_path()
    env_file.parent.mkdir(parents=True, exist_ok=True)

    existing_lines: list[str] = []
    if env_file.exists():
        try:
            existing_lines = env_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            existing_lines = []

    # Build map from existing
    kv: Dict[str, str] = {}
    for line in existing_lines:
        if not line.strip() or line.strip().startswith("#"):
            continue
        if "=" in line:
            k, _, val = line.partition("=")
            kv[k.strip()] = val.strip()

    # Apply updates
    kv.update(updates)

    # Reconstruct .env preserving simple grouping
    header = [
        "# SMTP basic",
        f"smtp_host={kv.get('smtp_host','')}",
        f"smtp_port={kv.get('smtp_port','')}",
        f"smtp_user={kv.get('smtp_user','')}",
        f"smtp_password={kv.get('smtp_password','')}",
        f"smtp_from={kv.get('smtp_from','')}",
        "",
        '# Report giornaliero schedulazioni (destinatari separati da pipe "|")',
        f"DAILY_REPORT_ENABLED={kv.get('daily_report_enabled','')}",
        "# Se impostato usa questo cron, altrimenti fallback su DAILY_REPORTS_HOUR",
        f"DAILY_REPORT_CRON={kv.get('daily_report_cron','')}",
        f"DAILY_REPORTS_HOUR={kv.get('daily_reports_hour','')}",
        f"DAILY_REPORT_RECIPIENTS={kv.get('daily_report_recipients','')}",
        f"DAILY_REPORT_CC={kv.get('daily_report_cc','')}",
        f"DAILY_REPORT_SUBJECT={kv.get('daily_report_subject','')}",
        f"DAILY_REPORT_TAIL_LINES={kv.get('daily_report_tail_lines','')}",
        "",
    ]
    try:
        env_file.write_text("\n".join(header), encoding="utf-8")
    except Exception as e:
        logger.error(f"[SETTINGS] Errore scrittura .env: {e}")
        return {"success": False, "error": str(e)}

    # Return new values; app may require restart to reload
    logger.info("[SETTINGS] .env aggiornato")
    return {"success": True, "env_path": str(env_file), "values": kv}
