from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger
import subprocess
import sys
import os
import threading
import tempfile
import time
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
    1. Try Windows native commands (Stop-Service + Start-Service) - saved to disk and launched as detached process
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
        
        # Create temporary script file to survive parent process termination
        temp_dir = Path(tempfile.gettempdir())
        script_file = temp_dir / f"pstt_restart_{int(time.time())}.ps1"
        log_file = temp_dir / f"pstt_restart_{int(time.time())}.log"
        
        ps_script = f"""
# PSTT Service Restart Script
# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'
$serviceName = '{name}'
$logFile = '{log_file}'

function Write-Log {{
    param($Message)
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$timestamp - $Message" | Out-File -FilePath $logFile -Append -Encoding utf8
}}

Write-Log "=== PSTT Service Restart Started ==="
Write-Log "Service: $serviceName"

# Stop service
try {{
    Write-Log "Stopping service..."
    Stop-Service -Name $serviceName -Force -ErrorAction Stop
    Write-Log "Service stopped successfully"
}} catch {{
    Write-Log "ERROR: Stop failed - $_"
    exit 1
}}

Write-Log "Waiting 3 seconds before restart..."
Start-Sleep -Seconds 3

# Start service with retry
$maxRetries = 5
Write-Log "Starting service (max $maxRetries attempts)..."
for ($i = 0; $i -lt $maxRetries; $i++) {{
    try {{
        Start-Service -Name $serviceName -ErrorAction Stop
        Write-Log "Service started successfully on attempt $($i+1)"
        Write-Log "=== PSTT Service Restart Completed Successfully ==="
        Start-Sleep -Seconds 2
        Remove-Item -Path $logFile -Force -ErrorAction SilentlyContinue
        Remove-Item -Path '{script_file}' -Force -ErrorAction SilentlyContinue
        exit 0
    }} catch {{
        Write-Log "WARNING: Start attempt $($i+1) failed - $_"
        if ($i -lt ($maxRetries - 1)) {{
            Start-Sleep -Seconds 2
        }}
    }}
}}

Write-Log "ERROR: Failed to start service after $maxRetries attempts"
Write-Log "=== PSTT Service Restart FAILED ==="
exit 1
        """
        
        try:
            # Save script to disk
            script_file.write_text(ps_script, encoding='utf-8')
            logger.info(f"Restart script saved to: {script_file}")
            logger.info(f"Restart log will be at: {log_file}")
            
            # Launch as completely detached process
            # CREATE_NEW_PROCESS_GROUP (0x00000200) + DETACHED_PROCESS (0x00000008) = 0x00000208
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            creation_flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            
            subprocess.Popen([
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-WindowStyle", "Hidden",
                "-File", str(script_file)
            ], 
            creationflags=creation_flags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
            )
            
            logger.info(f"Service restart launched as detached process for {name}")
            logger.info("Check restart log if service doesn't start within 30 seconds")
            _LAST_RESTART_STRATEGY = "native"
            return True
            
        except Exception as script_error:
            logger.error(f"Failed to create/launch restart script: {script_error}")
            # Clean up
            if script_file.exists():
                script_file.unlink()
            # Fall through to Strategy 2
        
    except Exception as e:
        logger.warning(f"Strategy 1 exception: {e}")
    
    # If we reach here, Strategy 1 failed - try Strategy 2
    logger.warning("Strategy 1 failed, attempting Strategy 2")
    try:
        name = _resolve_service_name()
        # Strategy 2: NSSM restart (if available)
        nssm_path = _get_nssm_path()
        if nssm_path:
            try:
                logger.info(f"Strategy 2: Trying NSSM restart command (nssm path: {nssm_path})")
                
                # Launch NSSM as detached process
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                creation_flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                
                subprocess.Popen([
                    nssm_path, "restart", name
                ], 
                creationflags=creation_flags,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
                )
                logger.info(f"Service restart via NSSM sent for {name}")
                _LAST_RESTART_STRATEGY = "nssm-restart"
                return True
            except Exception as e2:
                logger.error(f"Strategy 2 failed: {e2}")
                
                # Strategy 3: NSSM stop + start (last resort)
                try:
                    logger.info(f"Strategy 3: Trying NSSM stop + start sequence (nssm path: {nssm_path})")
                    
                    # Create temporary script for NSSM stop+start
                    temp_dir = Path(tempfile.gettempdir())
                    script_file = temp_dir / f"pstt_nssm_restart_{int(time.time())}.ps1"
                    
                    ps_nssm = f"""
# NSSM Stop+Start Sequence
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

Write-Host "Stopping service via NSSM..."
& '{nssm_path}' stop {name}
Start-Sleep -Seconds 3

Write-Host "Starting service via NSSM..."
& '{nssm_path}' start {name}

Start-Sleep -Seconds 2
Remove-Item -Path '{script_file}' -Force -ErrorAction SilentlyContinue
                    """
                    
                    script_file.write_text(ps_nssm, encoding='utf-8')
                    logger.info(f"NSSM restart script saved to: {script_file}")
                    
                    # Launch as detached process
                    DETACHED_PROCESS = 0x00000008
                    CREATE_NEW_PROCESS_GROUP = 0x00000200
                    creation_flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                    
                    subprocess.Popen([
                        "powershell.exe",
                        "-NoProfile",
                        "-ExecutionPolicy", "Bypass",
                        "-WindowStyle", "Hidden",
                        "-File", str(script_file)
                    ],
                    creationflags=creation_flags,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                    )
                    
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
    except Exception as outer_e:
        logger.error(f"Outer exception in Strategy 2/3: {outer_e}")
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


def _schedule_hot_restart(delay_sec: int = 2):
    """
    Riavvia il processo Python terminandolo con exit code 0.
    NSSM rileverà l'uscita e riavvierà automaticamente il servizio.
    Funziona senza privilegi amministratore.
    """
    def _do_hot_restart():
        try:
            logger.info("Executing hot restart - terminating process for NSSM auto-restart")
            logger.info("NSSM will automatically restart the service in 5 seconds")
            # Exit with code 0 so NSSM restarts the service
            # NSSM is configured with AppRestartDelay=5000ms
            os._exit(0)
        except Exception as e:
            logger.error(f"Hot restart failed: {e}")
            os._exit(1)
    
    logger.info(f"Hot restart scheduled in {delay_sec} seconds (NSSM will auto-restart)")
    t = threading.Timer(delay_sec, _do_hot_restart)
    t.daemon = True
    t.start()


@router.post("/restart", tags=["system"], summary="Riavvia l'applicazione")
def restart_app(prefer_nssm: bool = False, strategy: str | None = None, hot_restart: bool = True):
    """Prova a riavviare l'app.
    
    Controllo di sicurezza: il riavvio è abilitato solo se enable_app_restart=true nel file .env
    
    - hot_restart=True (default): Riavvia solo il processo Python senza toccare il servizio Windows (non richiede admin)
    - hot_restart=False: Tenta di riavviare il servizio Windows (richiede privilegi amministratore)
    - Se eseguita come servizio NSSM, effettua il restart del servizio.
    - Altrimenti, pianifica un riavvio avviando start_pstt.bat e terminando il processo corrente.
    """
    from app.core.config import get_settings
    from fastapi import HTTPException
    
    settings = get_settings()
    
    # Controllo di sicurezza: verifica se il riavvio è abilitato
    if not settings.enable_app_restart:
        logger.warning("Tentativo di riavvio app bloccato: enable_app_restart=false")
        raise HTTPException(
            status_code=403,
            detail="Il riavvio dell'applicazione è disabilitato. Impostare enable_app_restart=true nel file .env per abilitarlo."
        )
    
    try:
        # Hot restart: riavvia solo il processo Python (funziona anche senza admin)
        if hot_restart:
            logger.info("Hot restart richiesto: riavvio del processo Python")
            _schedule_hot_restart(delay_sec=2)
            return JSONResponse(content={
                "success": True, 
                "mode": "hot_restart", 
                "message": "Riavvio processo Python in corso (2 secondi)..."
            })
        
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


@router.get("/restart/enabled", tags=["system"], summary="Verifica se il riavvio app è abilitato")
def restart_enabled():
    """Verifica se il pulsante di riavvio è abilitato tramite configurazione"""
    from app.core.config import get_settings
    settings = get_settings()
    return JSONResponse(content={
        "enabled": settings.enable_app_restart,
        "message": "Riavvio abilitato" if settings.enable_app_restart else "Riavvio disabilitato in .env"
    })


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


@router.get("/service/restart-logs", tags=["system"], summary="Ultimi log di restart del servizio")
def restart_logs():
    """Restituisce gli ultimi log di restart generati dagli script temporanei"""
    try:
        temp_dir = Path(tempfile.gettempdir())
        log_files = sorted(temp_dir.glob("pstt_restart_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        logs = []
        for log_file in log_files[:3]:  # Ultimi 3 restart
            try:
                content = log_file.read_text(encoding='utf-8')
                logs.append({
                    "file": log_file.name,
                    "modified": log_file.stat().st_mtime,
                    "content": content
                })
            except Exception:
                pass
        
        return JSONResponse(content={
            "success": True,
            "count": len(logs),
            "logs": logs,
            "temp_dir": str(temp_dir)
        })
    except Exception as e:
        logger.error(f"Read restart logs fallito: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

