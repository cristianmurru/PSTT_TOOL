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
    # Timeouts
    "scheduler_query_timeout_sec",
    "scheduler_write_timeout_sec",
]


def _env_path() -> Path:
    settings = get_settings()
    # .env at base dir
    return settings.base_dir / ".env"


@router.get("/env", tags=["settings"])
def get_env_settings() -> Dict[str, Any]:
    """Return current settings values for the editable keys.
    Read directly from .env to reflect latest saved values without restart.
    """
    env_file = _env_path()
    kv: Dict[str, Any] = {}
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip()
                    kv[k] = v
        except Exception:
            kv = {}
    # Map env keys to allowed keys casing (env keys may be uppercased)
    out: Dict[str, Any] = {}
    for k in ALLOWED_KEYS:
        # try exact, then uppercase variant
        out[k] = kv.get(k, kv.get(k.upper(), None))
    return {"values": out, "env_path": str(env_file)}


@router.post("/env", tags=["settings"])
def update_env_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update only whitelisted settings in .env in-place, preserving all other lines.
    DB credentials and non-allowed keys are never touched.
    """
    # Prepare updates (lowercase keys), also support uppercase variants for daily report
    allowed = set(ALLOWED_KEYS)
    updates: Dict[str, str] = {}
    for k, v in payload.items():
        if k in allowed:
            updates[k] = str(v) if v is not None else ""

    env_file = _env_path()
    env_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    except Exception:
        lines = []

    # Map for quick lookup of found keys (both lower and upper for daily_report_* uppercase versions)
    found_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        raw = line
        s = raw.strip()
        if not s or s.startswith('#') or '=' not in s:
            new_lines.append(raw)
            continue
        k, _, v = s.partition('=')
        key = k.strip()
        # Never modify DB credentials or unrelated keys
        if key.startswith('DB_USER_') or key.startswith('DB_PASS_'):
            new_lines.append(raw)
            continue
        # Match allowed keys (lowercase) or their uppercase daily variants
        lkey = key.lower()
        if lkey in updates:
            new_lines.append(f"{key}={updates[lkey]}")
            found_keys.add(lkey)
        elif key in updates:
            new_lines.append(f"{key}={updates[key]}")
            found_keys.add(key)
        else:
            new_lines.append(raw)

    # Append any updates not found in file (create entries at the end)
    for k, v in updates.items():
        if k not in found_keys:
            new_lines.append(f"{k}={v}")

    try:
        env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as e:
        logger.error(f"[SETTINGS] Errore scrittura .env: {e}")
        return {"success": False, "error": str(e)}

    # Return new values; app may require restart to reload
    logger.info("[SETTINGS] .env aggiornato in-place (whitelist)")
    # Opportunistic: aggiorna l'istanza runtime per riflettere i cambi (UI-friendly)
    try:
        s = get_settings()
        for k in ALLOWED_KEYS:
            if k in updates:
                setattr(s, k, updates[k])
    except Exception:
        # ignore runtime update errors
        pass
    # Rileggi i valori aggiornati dall'.env per restituirli al client
    try:
        kv_all: Dict[str, Any] = {}
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip()
                kv_all[k] = v
        values_out: Dict[str, Any] = {}
        for k in ALLOWED_KEYS:
            values_out[k] = kv_all.get(k, kv_all.get(k.upper(), None))
    except Exception:
        values_out = {k: updates.get(k) for k in ALLOWED_KEYS}
    return {"success": True, "env_path": str(env_file), "values": values_out}
