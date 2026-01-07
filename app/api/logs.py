from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from typing import List, Dict
from pathlib import Path
import gzip
import io
import os
from app.core.config import get_settings

router = APIRouter()


def _safe_log_path(filename: str) -> Path:
    settings = get_settings()
    base = settings.log_dir
    p = (base / filename).resolve()
    # ensure the path is within log_dir
    if str(p).startswith(str(base.resolve())):
        return p
    raise HTTPException(status_code=400, detail="Percorso non valido")


def _read_text_file(path: Path, tail_lines: int | None = None) -> str:
    try:
        if path.suffix == ".gz":
            with gzip.open(path, 'rt', encoding='utf-8', errors='replace') as f:
                content = f.read()
        else:
            content = path.read_text(encoding='utf-8', errors='replace')
        if tail_lines and tail_lines > 0:
            lines = content.splitlines()
            return "\n".join(lines[-tail_lines:])
        return content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log non trovato")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore lettura log: {e}")


@router.get("/list")
def list_logs() -> Dict[str, List[Dict[str, str]]]:
    """Elenca tutti i file di log nella cartella logs (odierni e archiviati/compressi)."""
    settings = get_settings()
    log_dir = settings.log_dir
    if not log_dir.exists():
        return {"files": [], "today": [], "archive": []}

    # Raccogli tutti i file .log e .gz
    entries: List[Dict[str, str]] = []
    for p in log_dir.iterdir():
        if not p.is_file():
            continue
        name = p.name
        # Limita a log noti o compressi
        if (name.endswith(".log") or name.endswith(".gz")):
            try:
                stat = p.stat()
                entries.append({
                    "name": name,
                    "size": str(stat.st_size),
                    "mtime": str(stat.st_mtime)
                })
            except Exception:
                continue

    # Ordina per mtime decrescente
    entries.sort(key=lambda x: float(x["mtime"]), reverse=True)

    # Mantieni anche suddivisione today/archive per retrocompatibilità
    bases = ["app.log", "errors.log", "scheduler.log"]
    today = [e for e in entries if e["name"] in bases]
    archive = [e for e in entries if e["name"] not in bases]

    return {"files": entries, "today": today, "archive": archive}


@router.get("/read", response_class=PlainTextResponse)
def read_log(
    file: str = Query(..., description="Nome file da leggere (es. app.log o app.log.2025-12-29.gz)"),
    tail: int | None = Query(None, description="Numero di righe finali da restituire")
):
    """Restituisce il contenuto del log richiesto. Supporta .gz per archivi."""
    path = _safe_log_path(file)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File non trovato")
    content = _read_text_file(path, tail_lines=tail)
    return content


@router.get("/read-today", response_class=PlainTextResponse)
def read_today(
    kind: str = Query("app", description="Tipo log: app|errors|scheduler"),
    tail: int | None = Query(None, description="Numero di righe finali da restituire")
):
    """Restituisce il contenuto del log odierno (non compresso) per tipo."""
    name_map = {
        "app": "app.log",
        "errors": "errors.log",
        "scheduler": "scheduler.log",
    }
    base = name_map.get(kind.lower())
    if not base:
        raise HTTPException(status_code=400, detail="Tipo log non valido")
    path = _safe_log_path(base)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File odierno non trovato")
    content = _read_text_file(path, tail_lines=tail)
    return content
