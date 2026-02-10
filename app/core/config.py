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


class KafkaConnectionConfig(BaseModel):
    """Configurazione per una connessione Kafka (in connections.json)"""
    name: str
    bootstrap_servers: str
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    default_topic: str = "pstt-data"


class ConnectionsConfig(BaseModel):
    """Configurazione completa delle connessioni"""
    default_environment: str
    default_connection: str
    environments: List[str]
    connections: List[DatabaseConfig]
    kafka_connections: Optional[Dict[str, KafkaConnectionConfig]] = None
    
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
    # Ambiente di esecuzione (SVILUPPO | COLLAUDO | PRODUZIONE)
    app_environment: str = "SVILUPPO"
    
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
    # Robustezza scheduler: coalesce (accorpa esecuzioni perse) e finestra misfire (tolleranza in secondi)
    scheduler_coalesce_enabled: bool = True
    scheduler_misfire_grace_time_sec: int = 900
    # Daily report configurazione (recap giornaliero schedulazioni)
    daily_report_enabled: bool = False
    daily_report_cron: str | None = None  # es. "0 19 * * *"; se assente usa daily_reports_hour
    daily_report_recipients: str | None = None  # pipe-separated (a@x.com|b@y.com)
    daily_report_cc: str | None = None  # pipe-separated
    daily_report_subject: str = "Report schedulazioni PSTT"
    
    # Kafka settings
    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_sasl_mechanism: Optional[str] = None
    kafka_sasl_username: Optional[str] = None
    kafka_sasl_password: Optional[str] = None
    kafka_ssl_cafile: Optional[str] = None
    kafka_ssl_certfile: Optional[str] = None
    kafka_ssl_keyfile: Optional[str] = None
    
    # Kafka Producer settings
    kafka_compression_type: str = "snappy"
    kafka_batch_size: int = 16384
    kafka_linger_ms: int = 10
    kafka_max_request_size: int = 1048576
    kafka_request_timeout_ms: int = 30000
    kafka_enable_idempotence: bool = True
    kafka_retry_backoff_ms: int = 100
    kafka_max_in_flight_requests: int = 5
    kafka_acks: str = "all"
    
    # Kafka Application settings
    kafka_default_topic: str = "pstt-data"
    kafka_message_batch_size: int = 100
    kafka_max_retries: int = 3
    kafka_health_check_interval_sec: int = 60
    kafka_log_level: str = "INFO"
    kafka_log_payload: bool = False
    daily_report_tail_lines: int = 50

    # SMTP settings (per invio email)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    # Timeout esecuzione query schedulatore (secondi)
    scheduler_query_timeout_sec: int = 900  # default 15 minuti
    # Timeout scrittura export (secondi) - se non configurato, il servizio usa un default interno
    scheduler_write_timeout_sec: int = 180
    # Scheduler retry settings
    scheduler_retry_enabled: bool = True
    scheduler_retry_delay_minutes: int = 30
    scheduler_retry_max_attempts: int = 3
    
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
                    item.setdefault('second', s.get('second'))
                    item.setdefault('end_date', s.get('end_date'))
                    item.setdefault('output_filename_template', s.get('output_filename_template', '{query_name}_{date}.xlsx'))
                    item.setdefault('output_date_format', s.get('output_date_format', '%Y-%m-%d'))
                    item.setdefault('output_offset_days', s.get('output_offset_days', 0))
                    item.setdefault('output_compress_gz', s.get('output_compress_gz', False))
                    item.setdefault('sharing_mode', s.get('sharing_mode', 'filesystem'))
                    # default export dir from settings
                    item.setdefault('output_dir', s.get('output_dir', str(_settings.export_dir)))
                    # Email new fields with backward compatibility
                    # Prefer explicit email_to; if missing, fall back to legacy email_recipients
                    legacy_recipients = s.get('email_recipients')
                    item.setdefault('email_to', s.get('email_to', legacy_recipients))
                    item.setdefault('email_cc', s.get('email_cc'))
                    item.setdefault('email_subject', s.get('email_subject'))
                    item.setdefault('email_body', s.get('email_body'))
                    # keep legacy field to avoid breaking existing configs
                    item.setdefault('email_recipients', legacy_recipients)
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
            
            # Log Kafka connections se presenti
            if _connections_config.kafka_connections:
                logger.info(f"Configurazioni Kafka caricate: {len(_connections_config.kafka_connections)} connessioni")
            
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


def get_kafka_config() -> Optional[Dict[str, Any]]:
    """
    Ottiene la configurazione Kafka combinando settings e connections.json
    
    Returns:
        Dict con configurazione Kafka completa o None se Kafka non abilitato
    """
    try:
        settings = get_settings()
        
        if not settings.kafka_enabled:
            return None
        
        from app.models.kafka import KafkaConnectionConfig, KafkaProducerConfig

        def _none_if_blank(v: Optional[str]) -> Optional[str]:
            if isinstance(v, str) and v.strip() == "":
                return None
            return v
        
        # Configurazione connessione
        connection_config = KafkaConnectionConfig(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            security_protocol=settings.kafka_security_protocol,
            sasl_mechanism=_none_if_blank(settings.kafka_sasl_mechanism),
            sasl_username=_none_if_blank(settings.kafka_sasl_username),
            sasl_password=_none_if_blank(settings.kafka_sasl_password),
            ssl_cafile=_none_if_blank(settings.kafka_ssl_cafile),
            ssl_certfile=_none_if_blank(settings.kafka_ssl_certfile),
            ssl_keyfile=_none_if_blank(settings.kafka_ssl_keyfile)
        )
        
        # Configurazione producer
        producer_config = KafkaProducerConfig(
            compression_type=settings.kafka_compression_type,
            batch_size=settings.kafka_batch_size,
            linger_ms=settings.kafka_linger_ms,
            max_request_size=settings.kafka_max_request_size,
            request_timeout_ms=settings.kafka_request_timeout_ms,
            enable_idempotence=settings.kafka_enable_idempotence,
            retry_backoff_ms=settings.kafka_retry_backoff_ms,
            max_in_flight_requests=settings.kafka_max_in_flight_requests,
            acks=settings.kafka_acks
        )
        
        return {
            "connection": connection_config,
            "producer": producer_config,
            "default_topic": settings.kafka_default_topic,
            "message_batch_size": settings.kafka_message_batch_size,
            "max_retries": settings.kafka_max_retries,
            "log_payload": settings.kafka_log_payload
        }
        
    except Exception as e:
        logger.error(f"Errore nel caricamento configurazione Kafka: {e}")
        return None


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
