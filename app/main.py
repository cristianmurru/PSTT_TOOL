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

from app.core.config import setup_logging, get_settings, get_connections_config
from app.services.connection_service import ConnectionService
from app.services.scheduler_service import SchedulerService
from app.api import connections, queries, scheduler as scheduler_api, monitoring
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
