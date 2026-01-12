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

    # Reconstruct .env with expected sections, preserving existing keys
    allowed_set = set(ALLOWED_KEYS) | set(k.upper() for k in ALLOWED_KEYS)

    # Runtime keys and app config
    runtime_keys = ["HOST", "PORT", "DEBUG", "LOG_LEVEL"]
    app_cfg_keys = ["DEFAULT_ENVIRONMENT", "DEFAULT_CONNECTION"]

    # Group DB credentials by environment family (A: Collaudo, B: Certificazione, C: Produzione)
    db_groups = {"SVILUPPO": [], "COLLAUDO": [], "CERTIFICAZIONE": [], "PRODUZIONE": [], "ALTRE": []}
    for k_orig, v in kv.items():
        if k_orig.startswith("DB_USER_") or k_orig.startswith("DB_PASS_"):
            # Determine family by first letter after prefix (A/B/C)
            env_tag = k_orig.split("_", 2)[1] if "_" in k_orig else ""
            fam = "ALTRE"
            if env_tag.startswith("A"):
                fam = "COLLAUDO"
            elif env_tag.startswith("B"):
                fam = "CERTIFICAZIONE"
            elif env_tag.startswith("C"):
                fam = "PRODUZIONE"
            db_groups[fam].append(f"{k_orig}={v}")

    header: list[str] = []
    header.extend([
        "# Database Credentials Template - Multi Environment",
        "# Copia questo file in .env e inserisci le credenziali reali",
        "",
        "# === Runtime App ===",
        *(f"{rk}={kv.get(rk,'')}" for rk in runtime_keys),
        "",
        "# === SVILUPPO ===",
        "#DB_USER_DEV_ORACLE_APP1=your_dev_oracle_user",
        "#DB_PASS_DEV_ORACLE_APP1=your_dev_oracle_pass",
        "#DB_USER_DEV_PG_ANALYTICS=your_dev_postgres_user",
        "#DB_PASS_DEV_PG_ANALYTICS=your_dev_postgres_pass",
        "",
        "# === COLLAUDO ===",
        *db_groups["COLLAUDO"],
        "",
        "# === CERTIFICAZIONE ===",
        *db_groups["CERTIFICAZIONE"],
        "",
        "# === PRODUZIONE ===",
        *db_groups["PRODUZIONE"],
        "",
        "# Configurazione applicazione",
        *(f"{ck}={kv.get(ck,'')}" for ck in app_cfg_keys),
        "",
        "# SMTP basic",
        f"smtp_host={kv.get('smtp_host','')}",
        f"smtp_port={kv.get('smtp_port','')}",
        f"smtp_user={kv.get('smtp_user','')}",
        f"smtp_password={kv.get('smtp_password','')}",
        f"smtp_from={kv.get('smtp_from','')}",
        "",
        "# Timeout",
        f"scheduler_query_timeout_sec={kv.get('scheduler_query_timeout_sec','')}",
        f"scheduler_write_timeout_sec={kv.get('scheduler_write_timeout_sec','')}",
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
        "# Altre variabili ambiente (preservate)",
    ])

    # Append preserved unknown keys in stable order, skipping those we already rendered
    rendered_keys = set(runtime_keys + app_cfg_keys + [
        'smtp_host','smtp_port','smtp_user','smtp_password','smtp_from',
        'scheduler_query_timeout_sec','scheduler_write_timeout_sec',
        'DAILY_REPORT_ENABLED','DAILY_REPORT_CRON','DAILY_REPORTS_HOUR',
        'DAILY_REPORT_RECIPIENTS','DAILY_REPORT_CC','DAILY_REPORT_SUBJECT','DAILY_REPORT_TAIL_LINES']
    )
    # Also skip DB_* keys because they are rendered in their sections
    for k_orig, v in kv.items():
        if k_orig in rendered_keys:
            continue
        if k_orig.startswith('DB_USER_') or k_orig.startswith('DB_PASS_'):
            continue
        header.append(f"{k_orig}={v}")
    header.append("")

    try:
        env_file.write_text("\n".join(header), encoding="utf-8")
    except Exception as e:
        logger.error(f"[SETTINGS] Errore scrittura .env: {e}")
        return {"success": False, "error": str(e)}

    # Return new values; app may require restart to reload
    logger.info("[SETTINGS] .env aggiornato")
    # Opportunistic: aggiorna l'istanza runtime per riflettere i cambi (UI-friendly)
    try:
        s = get_settings()
        for k in ALLOWED_KEYS:
            if k in updates:
                setattr(s, k, updates[k])
    except Exception:
        # ignore runtime update errors
        pass
    return {"success": True, "env_path": str(env_file), "values": kv}
