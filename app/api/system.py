from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger
import subprocess
import sys
import os
import threading
from pathlib import Path

router = APIRouter()

SERVICE_NAME = "PSTT_Tool"
BASE_DIR = Path(__file__).resolve().parents[2]


def _restart_as_service() -> bool:
    try:
        # Check if service exists
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(Get-Service -Name '{SERVICE_NAME}' -ErrorAction SilentlyContinue) -ne $null"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        exists = res.returncode == 0 and "True" in (res.stdout or "")
        if not exists:
            return False
        # Use manage_service.ps1 to restart
        script_path = str(BASE_DIR / "manage_service.ps1")
        subprocess.Popen([
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path,
            "-Action", "restart",
            "-ServiceName", SERVICE_NAME,
        ])
        return True
    except Exception:
        logger.exception("Restart service failed")
        return False


def _schedule_terminal_restart(delay_sec: int = 2):
    try:
        # Build a PowerShell one-liner to delay and relaunch start_pstt.bat
        start_bat = str(BASE_DIR / "start_pstt.bat")
        ps = (
            f"Start-Sleep -Seconds {delay_sec}; "
            f"Start-Process -FilePath '{start_bat}' -WorkingDirectory '{BASE_DIR}'"
        )
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])
    except Exception:
        logger.exception("Schedule terminal restart failed")


def _exit_process(delay_sec: int = 1):
    def _do_exit():
        try:
            # Use os._exit to immediately terminate the process
            os._exit(0)
        except Exception:
            sys.exit(0)
    t = threading.Timer(delay_sec, _do_exit)
    t.daemon = True
    t.start()


@router.post("/restart", tags=["system"], summary="Riavvia l'applicazione")
def restart_app():
    """Prova a riavviare l'app.
    - Se eseguita come servizio NSSM, effettua il restart del servizio.
    - Altrimenti, pianifica un riavvio avviando start_pstt.bat e terminando il processo corrente.
    """
    try:
        if _restart_as_service():
            logger.info("Restart richiesto: servizio NSSM")
            return JSONResponse(content={"success": True, "mode": "service", "message": "Riavvio del servizio in corso"})
        # Fallback: terminal
        logger.info("Restart richiesto: modalità terminale")
        _schedule_terminal_restart(2)
        _exit_process(1)
        return JSONResponse(content={"success": True, "mode": "terminal", "message": "Riavvio pianificato"})
    except Exception as e:
        logger.error(f"Restart fallito: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
