"""
Entry point principale per PSTT Tool
"""
import uvicorn
from app.main import app
from app.core.config import get_settings


if __name__ == "__main__":
    try:
        settings = get_settings()
        
        print(f"🚀 Avvio {settings.app_name} v{settings.app_version}")
        print(f"🌐 Server: http://{settings.host}:{settings.port}")
        print(f"📊 API Docs: http://{settings.host}:{settings.port}/api/docs")
        print("=" * 50)
        
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ Errore nell'avvio dell'applicazione: {e}")
        raise
