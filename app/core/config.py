"""
Configurazioni e settings per PSTT Tool
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from loguru import logger
from app.models.scheduling import SchedulingItem


class DatabaseConfig(BaseModel):
    """Configurazione per una connessione database"""
    name: str
    environment: str
    db_type: str
    description: str
    params: Dict[str, Any]
    
    def get_connection_string(self, env_vars: Dict[str, str]) -> str:
        """
        Genera la stringa di connessione sostituendo le variabili d'ambiente
        """
        try:
            # Sostituisce le variabili d'ambiente nei parametri
            resolved_params = {}
            for key, value in self.params.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]  # Rimuove ${ e }
                    resolved_params[key] = env_vars.get(env_var, "")
                    if not resolved_params[key]:
                        logger.warning(f"Variabile d'ambiente {env_var} non trovata per {self.name}")
                else:
                    resolved_params[key] = value
            
            # Genera la stringa di connessione in base al tipo di database
            if self.db_type.lower() == "oracle":
                return self._build_oracle_connection_string(resolved_params)
            elif self.db_type.lower() == "postgresql":
                return self._build_postgresql_connection_string(resolved_params)
            elif self.db_type.lower() == "sqlserver":
                return self._build_sqlserver_connection_string(resolved_params)
            else:
                raise ValueError(f"Tipo database non supportato: {self.db_type}")
                
        except Exception as e:
            logger.error(f"Errore nella generazione connection string per {self.name}: {e}")
            raise
    
    def _build_oracle_connection_string(self, params: Dict[str, Any]) -> str:
        """Costruisce connection string per Oracle"""
        host = params.get("host", "")
        port = params.get("port", 1521)
        service_name = params.get("service_name", "")
        username = params.get("username", "")
        password = params.get("password", "")
        
        return f"oracle+oracledb://{username}:{password}@{host}:{port}/{service_name}"
    
    def _build_postgresql_connection_string(self, params: Dict[str, Any]) -> str:
        """Costruisce connection string per PostgreSQL"""
        host = params.get("host", "")
        port = params.get("port", 5432)
        database = params.get("service_name", "")  # Per PostgreSQL service_name è il database
        username = params.get("username", "")
        password = params.get("password", "")
        
        return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
    
    def _build_sqlserver_connection_string(self, params: Dict[str, Any]) -> str:
        """Costruisce connection string per SQL Server"""
        host = params.get("host", "")
        port = params.get("port", 1433)
        database = params.get("service_name", "")
        username = params.get("username", "")
        password = params.get("password", "")
        
        return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"


class ConnectionsConfig(BaseModel):
    """Configurazione completa delle connessioni"""
    default_environment: str
    default_connection: str
    environments: List[str]
    connections: List[DatabaseConfig]
    
    def get_connection_by_name(self, name: str) -> Optional[DatabaseConfig]:
        """Trova una connessione per nome"""
        for conn in self.connections:
            if conn.name == name:
                return conn
        return None
    
    def get_connections_by_environment(self, environment: str) -> List[DatabaseConfig]:
        """Trova tutte le connessioni per ambiente"""
        return [conn for conn in self.connections if conn.environment == environment]


class Settings(BaseSettings):
    """Configurazioni globali dell'applicazione"""
    
    # Informazioni applicazione
    app_name: str = "PSTT Tool"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    query_dir: Path = base_dir / "Query"
    export_dir: Path = base_dir / "exports"
    log_dir: Path = base_dir / "logs"
    connections_file: Path = base_dir / "connections.json"
    
    # Logging
    log_level: str = "INFO"
    log_retention: str = "30 days"
    log_rotation: str = "1 day"
    
    # Export settings
    export_retention_days: int = 30
    export_compression: bool = True
    
    # Scheduler settings
    scheduler_timezone: str = "Europe/Rome"
    daily_reports_hour: int = 6  # Ora di esecuzione report giornalieri
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")


# Singleton per le configurazioni
_settings: Optional[Settings] = None
_connections_config: Optional[ConnectionsConfig] = None


def get_settings() -> Settings:
    """Ottiene le configurazioni globali (singleton)"""
    global _settings
    if _settings is None:
        try:
            _settings = Settings()
            # Carica scheduling da connections.json
            try:
                with open(_settings.connections_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                scheduling = data.get('scheduling', [])
                # Normalizza ogni entry per includere i nuovi campi e valori di default
                normalized = []
                for s in scheduling:
                    item = {}
                    # copy existing
                    item.update(s)
                    # defaults for new fields
                    item.setdefault('scheduling_mode', 'classic')
                    item.setdefault('cron_expression', None)
                    item.setdefault('days_of_week', s.get('days_of_week'))
                    item.setdefault('hour', s.get('hour'))
                    item.setdefault('minute', s.get('minute'))
                    item.setdefault('end_date', s.get('end_date'))
                    item.setdefault('output_filename_template', s.get('output_filename_template', '{query_name}_{date}.xlsx'))
                    item.setdefault('output_date_format', s.get('output_date_format', '%Y-%m-%d'))
                    item.setdefault('output_offset_days', s.get('output_offset_days', 0))
                    item.setdefault('output_include_timestamp', s.get('output_include_timestamp', False))
                    item.setdefault('sharing_mode', s.get('sharing_mode', 'filesystem'))
                    # default export dir from settings
                    item.setdefault('output_dir', s.get('output_dir', str(_settings.export_dir)))
                    item.setdefault('email_recipients', s.get('email_recipients'))
                    # append normalized
                    normalized.append(item)

                _settings.scheduling = normalized
                logger.info(f"Configurazione scheduling caricata: {len(normalized)} job")
            except Exception as e:
                logger.warning(f"Nessuna configurazione scheduling caricata: {e}")
            logger.info(f"Configurazioni caricate da {_settings.base_dir}")
        except Exception as e:
            logger.error(f"Errore nel caricamento configurazioni: {e}")
            raise
    return _settings


def get_connections_config() -> ConnectionsConfig:
    """Ottiene la configurazione delle connessioni database (singleton)"""
    global _connections_config
    if _connections_config is None:
        try:
            settings = get_settings()
            with open(settings.connections_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            _connections_config = ConnectionsConfig(**data)
            logger.info(f"Configurazioni connessioni caricate: {len(_connections_config.connections)} connessioni")
            
        except FileNotFoundError:
            logger.error(f"File connections.json non trovato: {settings.connections_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Errore nel parsing di connections.json: {e}")
            raise
        except Exception as e:
            logger.error(f"Errore nel caricamento configurazioni connessioni: {e}")
            raise
            
    return _connections_config


def setup_logging() -> None:
    """Configura il sistema di logging"""
    try:
        settings = get_settings()
        
        # Crea la directory dei log se non esiste
        settings.log_dir.mkdir(exist_ok=True)
        
        # Rimuove i logger di default di loguru
        logger.remove()
        
        # Logger per console (sempre attivo per errori, debug opzionale)
        logger.add(
            sink=lambda msg: print(msg, end=""),
            level="ERROR",  # Sempre mostra errori sulla console
            format="<red>ERROR</red> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <red>{message}</red>",
            colorize=True
        )
        
        # Logger console per debug solo in modalità debug
        if settings.debug:
            logger.add(
                sink=lambda msg: print(msg, end=""),
                level=settings.log_level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                colorize=True
            )
        
        # Logger per file applicazione
        logger.add(
            sink=settings.log_dir / "app.log",
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression="gz"
        )
        
        # Logger per errori
        logger.add(
            sink=settings.log_dir / "errors.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression="gz"
        )
        
        # Logger per scheduler
        logger.add(
            sink=settings.log_dir / "scheduler.log",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression="gz",
            filter=lambda record: "scheduler" in record["name"].lower()
        )
        
        logger.info("Sistema di logging configurato correttamente")
        
    except Exception as e:
        print(f"Errore nella configurazione del logging: {e}")
        raise


def get_env_vars() -> Dict[str, str]:
    """Carica le variabili d'ambiente dal file .env"""
    try:
        env_vars = {}
        settings = get_settings()
        env_file = settings.base_dir / ".env"
        
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"\'')
        
        # Aggiungi anche le variabili d'ambiente del sistema
        env_vars.update(dict(os.environ))
        
        return env_vars
        
    except Exception as e:
        logger.error(f"Errore nel caricamento variabili d'ambiente: {e}")
        return {}
