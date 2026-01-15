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


def _resolve_service_name() -> str:
    """Resolve possible service names, allowing override via env var."""
    override = os.environ.get("PSTT_SERVICE_NAME")
    if override:
        return override
    # Accept both with underscore and space
    candidates = ["PSTT_Tool", "PSTT Tool"]
    for name in candidates:
        try:
            res = subprocess.run([
                "powershell", "-NoProfile", "-Command",
                f"(Get-Service -Name '{name}' -ErrorAction SilentlyContinue) -ne $null"
            ], capture_output=True, text=True)
            if res.returncode == 0 and "True" in (res.stdout or ""):
                return name
        except Exception:
            pass
    return candidates[0]


def _get_service_status(name: str) -> dict:
    try:
        ps = (
            f"$s = Get-Service -Name '{name}' -ErrorAction SilentlyContinue;"
            "if ($s) { $obj = [PSCustomObject]@{ Name=$s.Name; DisplayName=$s.DisplayName; Status=$s.Status.ToString() }; $obj | ConvertTo-Json -Compress }"
        )
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
        if res.returncode != 0 or not res.stdout.strip():
            return {"exists": False}
        try:
            import json as _json
            j = _json.loads(res.stdout.strip())
            j["exists"] = True
            return j
        except Exception:
            return {"exists": True, "raw": res.stdout.strip()}
    except Exception:
        logger.exception("Read service status failed")
        return {"exists": False}


def _restart_as_service() -> bool:
    try:
        name = _resolve_service_name()
        # Check if service exists
        cmd = ["powershell", "-NoProfile", "-Command",
               f"(Get-Service -Name '{name}' -ErrorAction SilentlyContinue) -ne $null"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        exists = res.returncode == 0 and "True" in (res.stdout or "")
        if not exists:
            logger.warning(f"Service {name} not found")
            return False
        
        logger.info(f"Restarting service: {name}")
        
        # Use Windows native commands (no NSSM dependency)
        # This works even if NSSM is not in PATH
        ps_script = f"""
            $serviceName = '{name}'
            
            # Stop service
            Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 3
            
            # Start service with retry
            $maxRetries = 5
            for ($i = 0; $i -lt $maxRetries; $i++) {{
                try {{
                    Start-Service -Name $serviceName -ErrorAction Stop
                    Write-Host "Service started successfully"
                    exit 0
                }} catch {{
                    Write-Warning "Start attempt $($i+1) failed: $_"
                    Start-Sleep -Seconds 2
                }}
            }}
            Write-Error "Failed to start service after $maxRetries attempts"
            exit 1
        """
        
        # Execute restart in background
        subprocess.Popen([
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-Command", ps_script
        ], creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
        
        logger.info(f"Service restart command sent for {name}")
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
            # NOTA: Non chiamiamo _exit_process qui - NSSM gestisce stop/start
            # Il servizio continuerà a rispondere fino a quando NSSM non lo fermerà
            return JSONResponse(content={"success": True, "mode": "service", "message": "Riavvio del servizio in corso"})
        # Fallback: terminal
        logger.info("Restart richiesto: modalità terminale")
        _schedule_terminal_restart(2)
        _exit_process(1)
        return JSONResponse(content={"success": True, "mode": "terminal", "message": "Riavvio pianificato"})
    except Exception as e:
        logger.error(f"Restart fallito: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/service/status", tags=["system"], summary="Stato del servizio Windows")
def service_status():
    try:
        name = _resolve_service_name()
        st = _get_service_status(name)
        return JSONResponse(content={"service": name, **st})
    except Exception as e:
        logger.error(f"Service status fallito: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
