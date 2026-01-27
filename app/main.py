"""
PSTT Tool - Applicazione principale FastAPI
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from loguru import logger
import mimetypes
import os
import re

from app.core.config import setup_logging, get_settings, get_connections_config
from app.services.connection_service import ConnectionService
from app.services.scheduler_service import SchedulerService
from app.api import connections, queries, scheduler as scheduler_api, monitoring, logs as logs_api, reports as reports_api, settings as settings_api, system as system_api, kafka as kafka_api
from app.api.queries import setup_error_handlers


# Configurazione logging all'avvio
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestione del ciclo di vita dell'applicazione"""
    logger.info("🚀 Avvio PSTT Tool...")
    
    try:
        # Inizializza i servizi
        settings = get_settings()
        connections_config = get_connections_config()
        
        # Avvia il servizio scheduler
        scheduler_service = SchedulerService()
        await scheduler_service.start()
        
        # Salva i servizi nell'app state
        app.state.scheduler_service = scheduler_service
        app.state.connection_service = ConnectionService()
        
        logger.info("✅ PSTT Tool avviato correttamente")
        logger.info(f"📊 Configurate {len(connections_config.connections)} connessioni database")
        logger.info(f"🌐 Server in ascolto su http://{settings.host}:{settings.port}")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Errore durante l'avvio: {e}")
        raise
    finally:
        # Cleanup
        logger.info("🛑 Arresto PSTT Tool...")
        try:
            if hasattr(app.state, 'scheduler_service'):
                await app.state.scheduler_service.stop()
        except Exception as e:
            logger.error(f"Errore durante l'arresto: {e}")
        logger.info("✅ PSTT Tool arrestato correttamente")


# Inizializza FastAPI
app = FastAPI(
    title="PSTT Tool",
    description="Strumento per l'esecuzione di query parametrizzate su database multi-vendor con scheduling automatico",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Configurazione templates e static files
settings = get_settings()
templates = Jinja2Templates(directory=str(settings.base_dir / "app" / "templates"))
# Ensure common font MIME types are registered (some OS/python installs
# may not include .woff2/.woff mappings, which causes StaticFiles to return
# text/plain and browsers to refuse fonts). Register them before mounting.
mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('font/woff', '.woff')
mimetypes.add_type('font/ttf', '.ttf')

app.mount("/static", StaticFiles(directory=str(settings.base_dir / "app" / "static")), name="static")

# Registra i router API
app.include_router(connections.router, prefix="/api/connections", tags=["connections"])
app.include_router(queries.router, prefix="/api/queries", tags=["queries"])
app.include_router(scheduler_api.router, prefix="/api/scheduler", tags=["scheduler"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["monitoring"])
app.include_router(logs_api.router, prefix="/api/logs", tags=["logs"])
app.include_router(reports_api.router, prefix="/api/reports", tags=["reports"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])
app.include_router(system_api.router, prefix="/api/system", tags=["system"])
app.include_router(kafka_api.router, prefix="/api/kafka", tags=["kafka"])
setup_error_handlers(app)


@app.get("/", response_class=HTMLResponse, name="home")
async def home(request: Request):
    """Homepage dell'applicazione"""
    try:
        connections_config = get_connections_config()
        
        context = {
            "request": request,
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "connections": connections_config.connections,
            "default_connection": connections_config.default_connection,
            "environments": connections_config.environments,
            "current_environment": connections_config.default_environment
        }
        
        return templates.TemplateResponse("index.html", context)
        
    except Exception as e:
        logger.error(f"Errore nella homepage: {e}")
        raise HTTPException(status_code=500, detail="Errore interno del server")


@app.get("/kafka", name="kafka_dashboard")
async def kafka_dashboard(request: Request):
    """Kafka Dashboard UI"""
    try:
        context = {
            "request": request,
            "app_name": settings.app_name,
            "app_version": settings.app_version
        }
        
        return templates.TemplateResponse("kafka_dashboard.html", context)
        
    except Exception as e:
        logger.error(f"Errore nel Kafka dashboard: {e}")
        raise HTTPException(status_code=500, detail="Errore interno del server")


@app.get("/docs/readme", response_class=HTMLResponse, name="readme_page")
async def readme_page(request: Request):
    """Visualizza README.md come pagina HTML"""
    try:
        # Preferisce README.md in root; fallback a docs/README.md
        root_path = settings.base_dir / "README.md"
        alt_path = settings.base_dir / "docs" / "README.md"
        file_path = root_path if root_path.exists() else alt_path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="README non trovato")
        md_text = file_path.read_text(encoding="utf-8")
        return templates.TemplateResponse(
            "markdown_viewer.html",
            {
                "request": request,
                "title": "README",
                "md_content": md_text,
                "app_name": settings.app_name,
                "app_version": settings.app_version,
                "doc_version": None,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nel rendering README: {e}")
        raise HTTPException(status_code=500, detail="Errore interno del server")


@app.get("/docs/changelog", response_class=HTMLResponse, name="changelog_page")
async def changelog_page(request: Request):
    """Visualizza CHANGELOG.md come pagina HTML"""
    try:
        # Preferisce CHANGELOG.md in root; fallback ad eventuale docs/CHANGELOG.md
        root_path = settings.base_dir / "CHANGELOG.md"
        alt_path = settings.base_dir / "docs" / "CHANGELOG.md"
        file_path = root_path if root_path.exists() else alt_path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="CHANGELOG non trovato")
        md_text = file_path.read_text(encoding="utf-8")

        # Evidenzia e uniforma i titoli release (come H2) con spacing
        # Cattura sia linee già con '## ' sia linee senza prefisso
        pattern = r"^\s*(?:##\s*)?\[(\d+\.\d+\.\d+)\]\s*-\s*\[(\d{4}-\d{2}-\d{2})\]\s*-\s*(.+)$"
        def repl(m: re.Match) -> str:
            ver, date, title = m.group(1), m.group(2), m.group(3)
            return f"\n\n## [{ver}] - [{date}] - {title}\n\n"
        md_text_transformed = re.sub(pattern, repl, md_text, flags=re.MULTILINE)

        # Estrae la versione più recente
        doc_version = None
        mver = re.search(r"^##\s*\[(?P<ver>\d+\.\d+\.\d+)\]", md_text, flags=re.MULTILINE)
        if mver:
            doc_version = mver.group("ver")
        else:
            mver2 = re.search(r"^\[(?P<ver>\d+\.\d+\.\d+)\]\s*-\s*\[\d{4}-\d{2}-\d{2}\]", md_text, flags=re.MULTILINE)
            if mver2:
                doc_version = mver2.group("ver")

        return templates.TemplateResponse(
            "markdown_viewer.html",
            {
                "request": request,
                "title": "CHANGELOG",
                "md_content": md_text_transformed,
                "app_name": settings.app_name,
                "app_version": settings.app_version,
                "doc_version": doc_version,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nel rendering CHANGELOG: {e}")
        raise HTTPException(status_code=500, detail="Errore interno del server")


@app.get("/health", name="health_check")
async def health_check():
    """Endpoint per health check"""
    try:
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Errore in health check: {e}")
        raise HTTPException(status_code=500, detail="Servizio non disponibile")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handler per errori 404"""
    # Se la richiesta è verso API, restituisci JSON
    try:
        if request.url.path.startswith('/api'):
            return JSONResponse(status_code=404, content={"detail": str(exc.detail if hasattr(exc, 'detail') else exc)})
    except Exception:
        pass
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 404,
            "error_message": "Pagina non trovata"
        },
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Handler per errori 500"""
    logger.error(f"Errore interno: {exc}")
    # Se la richiesta è verso API, restituisci JSON
    try:
        if request.url.path.startswith('/api'):
            return JSONResponse(status_code=500, content={"detail": str(exc.detail if hasattr(exc, 'detail') else exc)})
    except Exception:
        pass
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 500,
            "error_message": "Errore interno del server"
        },
        status_code=500
    )


@app.get("/dashboard", response_class=HTMLResponse, name="scheduler_dashboard")
async def scheduler_dashboard():
    """Dashboard schedulazioni e monitoring"""
    return FileResponse(str(settings.base_dir / "app" / "frontend" / "scheduler_dashboard.html"))


@app.get("/logs", response_class=HTMLResponse, name="logs_viewer")
async def logs_viewer():
    """Visualizzatore dei log"""
    return FileResponse(str(settings.base_dir / "app" / "frontend" / "logs.html"))


@app.get("/settings", response_class=HTMLResponse, name="settings_page")
async def settings_page():
    """Pagina impostazioni env"""
    return FileResponse(str(settings.base_dir / "app" / "frontend" / "settings.html"))


if __name__ == "__main__":
    import uvicorn
    
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.reload,
            log_level=settings.log_level.lower()
        )
    except Exception as e:
        logger.error(f"Errore nell'avvio del server: {e}")
        raise
