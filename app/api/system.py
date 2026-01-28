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
_LAST_RESTART_STRATEGY: str | None = None


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


def _get_nssm_path() -> str | None:
    """Return absolute path to nssm.exe if available in PATH or local BASE_DIR."""
    # Try PATH first
    try:
        result = subprocess.run(["where", "nssm"], capture_output=True, text=True)
        if result.returncode == 0:
            exe = result.stdout.strip().splitlines()[0]
            if exe:
                return exe
    except Exception:
        pass
    # Try local directory (BASE_DIR) and common subfolders
    local = BASE_DIR / "nssm.exe"
    try:
        if local.exists():
            return str(local)
        # Common locations inside the app folder
        for rel in [
            Path("tools") / "nssm.exe",
            Path("Setup") / "nssm.exe",
            Path("setup") / "nssm.exe",
        ]:
            candidate = BASE_DIR / rel
            if candidate.exists():
                return str(candidate)
    except Exception:
        pass
    return None


def _restart_as_service(prefer_nssm: bool = False) -> bool:
    """
    Multi-strategy restart with fallback mechanisms:
    1. Try Windows native commands (Stop-Service + Start-Service)
    2. If fails and NSSM available, try: nssm restart
    3. If still fails, try: nssm stop + wait + nssm start
    """
    global _LAST_RESTART_STRATEGY
    try:
        name = _resolve_service_name()
        # Check if service exists
        cmd = ["powershell", "-NoProfile", "-Command",
               f"(Get-Service -Name '{name}' -ErrorAction SilentlyContinue) -ne $null"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        exists = res.returncode == 0 and "True" in (res.stdout or "")
        if not exists:
            logger.warning(f"Service {name} not found")
            _LAST_RESTART_STRATEGY = "none"
            return False
        
        logger.info(f"Restarting service: {name}")

        # If explicitly requested, prefer NSSM first (Strategy 2)
        if prefer_nssm:
            nssm_path = _get_nssm_path()
            if nssm_path:
                try:
                    logger.info("Strategy 2: Trying NSSM restart command (preferred)")
                    # Use PowerShell call operator to avoid PATH/current-location policy issues
                    ps_restart = f"& '{nssm_path}' restart {name}"
                    subprocess.Popen([
                        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-Command", ps_restart
                    ], creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    logger.info(f"Service restart via NSSM sent for {name}")
                    _LAST_RESTART_STRATEGY = "nssm-restart"
                    return True
                except Exception as e2:
                    logger.warning(f"Preferred Strategy 2 failed: {e2}")
                    # fallthrough to Strategy 3 then Strategy 1
                    try:
                        logger.info("Strategy 3: Trying NSSM stop + start sequence (fallback)")
                        ps_nssm = f"""
                            & '{nssm_path}' stop {name}
                            Start-Sleep -Seconds 3
                            & '{nssm_path}' start {name}
                        """
                        subprocess.Popen([
                            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-Command", ps_nssm
                        ], creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                        logger.info(f"Service restart via NSSM stop/start sent for {name}")
                        _LAST_RESTART_STRATEGY = "nssm-stopstart"
                        return True
                    except Exception as e3:
                        logger.warning(f"Strategy 3 failed: {e3}")
                        # Continue to Strategy 1
        
        # Strategy 1: Windows native commands (preferred - works without NSSM in PATH)
        logger.info("Strategy 1: Trying Windows native Stop-Service/Start-Service")
        ps_script = f"""
            $serviceName = '{name}'
            
            # Stop service
            try {{
                Stop-Service -Name $serviceName -Force -ErrorAction Stop
                Write-Host "Service stopped successfully"
            }} catch {{
                Write-Error "Stop failed: $_"
                exit 1
            }}
            
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
                    if ($i -lt ($maxRetries - 1)) {{
                        Start-Sleep -Seconds 2
                    }}
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
        
        logger.info(f"Service restart command sent (native Windows commands) for {name}")
        _LAST_RESTART_STRATEGY = "native"
        return True
        
    except Exception as e:
        logger.warning(f"Strategy 1 failed: {e}")
        
        # Strategy 2: NSSM restart (if available)
        nssm_path = _get_nssm_path()
        if nssm_path:
            try:
                logger.info("Strategy 2: Trying NSSM restart command")
                ps_restart = f"& '{nssm_path}' restart {name}"
                subprocess.Popen([
                    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-Command", ps_restart
                ], creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                logger.info(f"Service restart via NSSM sent for {name}")
                _LAST_RESTART_STRATEGY = "nssm-restart"
                return True
            except Exception as e2:
                logger.warning(f"Strategy 2 failed: {e2}")
                
                # Strategy 3: NSSM stop + start (last resort)
                try:
                    logger.info("Strategy 3: Trying NSSM stop + start sequence")
                    ps_nssm = f"""
                        & '{nssm_path}' stop {name}
                        Start-Sleep -Seconds 3
                        & '{nssm_path}' start {name}
                    """
                    subprocess.Popen([
                        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-Command", ps_nssm
                    ], creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    logger.info(f"Service restart via NSSM stop/start sent for {name}")
                    _LAST_RESTART_STRATEGY = "nssm-stopstart"
                    return True
                except Exception as e3:
                    logger.error(f"All restart strategies failed: {e3}")
                    _LAST_RESTART_STRATEGY = "none"
                    return False
        else:
            logger.error("NSSM not available for fallback, restart failed")
            _LAST_RESTART_STRATEGY = "none"
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
def restart_app(prefer_nssm: bool = False, strategy: str | None = None):
    """Prova a riavviare l'app.
    - Se eseguita come servizio NSSM, effettua il restart del servizio.
    - Altrimenti, pianifica un riavvio avviando start_pstt.bat e terminando il processo corrente.
    """
    try:
        # Prefer NSSM if requested by query or environment
        env_val = os.environ.get("PSTT_PREFER_NSSM", "").strip().lower()
        env_prefer = env_val in ("1", "true", "yes", "2", "nssm", "restart")
        query_prefer = False
        if strategy:
            s = (strategy or "").strip().lower()
            query_prefer = s in ("2", "nssm", "restart")
        success = _restart_as_service(prefer_nssm or env_prefer or query_prefer)
        mode = _LAST_RESTART_STRATEGY or "none"
        if success:
            if mode.startswith("nssm"):
                logger.info("Restart richiesto: servizio NSSM")
            else:
                logger.info("Restart richiesto: servizio Windows nativo")
            # NOTA: Non chiamiamo _exit_process qui - NSSM gestisce stop/start
            # Il servizio continuerà a rispondere fino a quando NSSM non lo fermerà
            return JSONResponse(content={"success": True, "mode": "service", "strategy": mode, "message": "Riavvio del servizio in corso"})
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


@router.get("/service/nssm-path", tags=["system"], summary="Percorso di nssm.exe rilevato")
def nssm_path():
    try:
        p = _get_nssm_path()
        return JSONResponse(content={"path": p, "available": bool(p)})
    except Exception as e:
        logger.error(f"Read nssm path fallito: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
