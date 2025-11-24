"""
Entry point principale per PSTT Tool
"""
import sys
import argparse
import logging
import uvicorn
from app.main import app
from app.core.config import get_settings


def safe_print(text):
    """Print con fallback per encoding Windows service (cp1252)"""
    try:
        print(text)
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback: rimuovi emoji e caratteri non-ASCII
        safe_text = text.encode('ascii', errors='ignore').decode('ascii')
        print(safe_text)


def is_service_mode():
    """Rileva se stiamo girando come Windows Service"""
    import os
    # Se stdout/stderr puntano a file o se non c'è terminale interattivo, siamo probabilmente un servizio
    return not sys.stdout.isatty() or os.environ.get('NSSM_SERVICE_NAME') is not None


if __name__ == "__main__":
    # Parse argomenti da CLI
    parser = argparse.ArgumentParser(description="PSTT Tool - Query Scheduler")
    parser.add_argument('--port', type=int, help='Porta su cui avviare il server (default: da config o 8000)')
    parser.add_argument('--host', type=str, help='Host su cui avviare il server (default: 127.0.0.1)')
    args = parser.parse_args()
    
    try:
        # Fix encoding per Windows Service
        if sys.stdout.encoding != 'utf-8':
            try:
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            except AttributeError:
                # Python < 3.7 fallback
                import io
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        
        # Configura formato log Uvicorn con timestamp (come loguru)
        log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            datefmt=date_format
        )
        
        # Configura anche i logger specifici di uvicorn
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
            logger.addHandler(handler)
            logger.propagate = False
        
        settings = get_settings()
        
        # Override con argomenti CLI se forniti
        host = args.host if args.host else settings.host
        port = args.port if args.port else settings.port
        
        # Usa messaggi semplici se in modalità servizio
        if is_service_mode():
            safe_print(f"[START] {settings.app_name} v{settings.app_version}")
            safe_print(f"[SERVER] http://{host}:{port}")
            safe_print(f"[API DOCS] http://{host}:{port}/api/docs")
            safe_print("=" * 50)
        else:
            safe_print(f"🚀 Avvio {settings.app_name} v{settings.app_version}")
            safe_print(f"🌐 Server: http://{host}:{port}")
            safe_print(f"📊 API Docs: http://{host}:{port}/api/docs")
            safe_print("=" * 50)
        
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=settings.debug,
            log_level="info"
        )
        
    except Exception as e:
        safe_print(f"❌ Errore nell'avvio dell'applicazione: {e}")
        raise
