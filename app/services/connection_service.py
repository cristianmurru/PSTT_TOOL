"""
Servizio per la gestione delle connessioni database
"""
import time
from typing import Dict, Optional, Any
from datetime import datetime
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from loguru import logger

from app.core.config import get_connections_config, get_env_vars
from app.models.connections import (
    DatabaseConnection, 
    ConnectionStatus, 
    ConnectionTest,
    DatabaseType
)


class ConnectionService:
    """Servizio per la gestione delle connessioni database"""
    
    def __init__(self):
        self._engines: Dict[str, Engine] = {}
        self._current_connection: Optional[str] = None
        self._connections_config = None
        self._env_vars: Dict[str, str] = {}
        
        try:
            self._connections_config = get_connections_config()
            self._env_vars = get_env_vars()
            self._current_connection = self._connections_config.default_connection
            logger.info(f"ConnectionService inizializzato - connessione di default: {self._current_connection}")
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione ConnectionService: {e}")
            raise
    
    def get_connections(self) -> Dict[str, DatabaseConnection]:
        """Ottiene tutte le connessioni disponibili"""
        try:
            connections = {}
            for conn_config in self._connections_config.connections:
                # Determina lo status della connessione
                status = ConnectionStatus.DISCONNECTED
                last_connected = None
                last_error = None
                
                if conn_config.name in self._engines:
                    status = ConnectionStatus.CONNECTED
                    last_connected = datetime.utcnow()
                
                connection = DatabaseConnection(
                    name=conn_config.name,
                    environment=conn_config.environment,
                    db_type=conn_config.db_type,
                    description=conn_config.description,
                    params=conn_config.params,
                    status=status,
                    last_connected=last_connected,
                    last_error=last_error
                )
                connections[conn_config.name] = connection
            
            return connections
            
        except Exception as e:
            logger.error(f"Errore nel recupero delle connessioni: {e}")
            raise
    
    def get_connection(self, connection_name: str) -> Optional[DatabaseConnection]:
        """Ottiene una connessione specifica per nome"""
        try:
            connections = self.get_connections()
            return connections.get(connection_name)
        except Exception as e:
            logger.error(f"Errore nel recupero della connessione {connection_name}: {e}")
            return None
    
    def get_current_connection(self) -> Optional[str]:
        """Ottiene il nome della connessione corrente"""
        return self._current_connection
    
    def set_current_connection(self, connection_name: str) -> bool:
        """Imposta la connessione corrente"""
        try:
            if connection_name in [conn.name for conn in self._connections_config.connections]:
                self._current_connection = connection_name
                logger.info(f"Connessione corrente impostata a: {connection_name}")
                return True
            else:
                logger.error(f"Connessione non trovata: {connection_name}")
                return False
        except Exception as e:
            logger.error(f"Errore nell'impostazione della connessione corrente: {e}")
            return False
    
    def get_engine(self, connection_name: Optional[str] = None) -> Optional[Engine]:
        """Ottiene l'engine SQLAlchemy per una connessione"""
        try:
            target_connection = connection_name or self._current_connection
            
            if not target_connection:
                logger.error("Nessuna connessione specificata o corrente disponibile")
                return None
            
            # Se l'engine esiste già, restituiscilo
            if target_connection in self._engines:
                return self._engines[target_connection]
            
            # Crea un nuovo engine
            return self._create_engine(target_connection)
            
        except Exception as e:
            logger.error(f"Errore nel recupero dell'engine per {target_connection}: {e}")
            return None
    
    def _create_engine(self, connection_name: str) -> Optional[Engine]:
        """Crea un nuovo engine SQLAlchemy per la connessione"""
        try:
            # Trova la configurazione della connessione
            conn_config = None
            for config in self._connections_config.connections:
                if config.name == connection_name:
                    conn_config = config
                    break
            
            if not conn_config:
                logger.error(f"Configurazione connessione non trovata: {connection_name}")
                return None
            
            # Gestione speciale per Oracle con oracledb
            if conn_config.db_type.lower() == "oracle":
                return self._create_oracle_engine(conn_config, connection_name)
            else:
                # Per PostgreSQL, SQL Server, etc. usa la connection string standard
                connection_string = conn_config.get_connection_string(self._env_vars)
                logger.info(f"🔗 Connection string per {connection_name}: {self._safe_connection_string(connection_string)}")
                
                # Configurazione pool in base al tipo di database
                pool_config = self._get_pool_config(conn_config.db_type)
                
                # Crea l'engine
                engine = create_engine(
                    connection_string,
                    **pool_config,
                    echo=False,  # Disabilita il logging SQL automatico
                    future=True  # Usa la nuova API di SQLAlchemy 2.0
                )
                
                self._engines[connection_name] = engine
                logger.info(f"✅ Engine creato per connessione: {connection_name}")
                
                return engine
            
        except Exception as e:
            logger.error(f"❌ Errore nella creazione dell'engine per {connection_name}: {e}")
            logger.error(f"Tipo errore: {type(e).__name__}")
            logger.error(f"Dettagli completi: {e}")
            return None
    
    def _create_oracle_engine(self, conn_config, connection_name: str) -> Optional[Engine]:
        """Crea engine Oracle usando oracledb con DSN approach - versione semplificata"""
        try:
            import oracledb
            
            # Risolvi variabili ambiente nei parametri
            resolved_params = {}
            for key, value in conn_config.params.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    resolved_params[key] = self._env_vars.get(env_var, value)
                else:
                    resolved_params[key] = value
            
            # Parametri Oracle
            host = resolved_params.get('host', 'localhost')
            port = int(resolved_params.get('port', 1521))
            service_name = resolved_params.get('service_name', 'XE')
            username = resolved_params.get('username')
            password = resolved_params.get('password')
            
            if not username or not password:
                raise ValueError("Username e password Oracle sono obbligatori")
            
            logger.info(f"🔗 Connessione Oracle a {host}:{port}")
            logger.info(f"🌐 Service Name: {service_name}")
            logger.info(f"👤 Utente: {username}")
            
            # Costruisci DSN con oracledb.makedsn
            dsn = oracledb.makedsn(host, port, service_name=service_name)
            logger.debug(f"🌐 DSN Oracle: {dsn}")
            
            # Test connessione DIRETTA con oracledb (senza SQLAlchemy)
            try:
                test_conn = oracledb.connect(
                    user=username,
                    password=password,
                    dsn=dsn
                )
                with test_conn:
                    cursor = test_conn.cursor()
                    cursor.execute("SELECT 1 FROM DUAL")
                    cursor.fetchone()
                logger.info("✅ Test connessione Oracle diretta riuscita")
            except Exception as e:
                logger.error(f"❌ Test connessione Oracle diretta fallita: {e}")
                raise
            
            # Costruisci connection string SQLAlchemy per oracledb - SENZA parametri extra
            connection_string = f"oracle+oracledb://{username}:{password}@{dsn}"
            
            # Configurazione pool Oracle OTTIMIZZATA - previene connessioni stale
            pool_config = {
                "poolclass": QueuePool,
                "pool_size": 3,
                "max_overflow": 5,
                "pool_pre_ping": True,  # CRITICO: testa connessioni prima dell'uso
                "pool_recycle": 1800,   # 30min invece di 1h per evitare stale connections
                "pool_timeout": 30,      # Timeout attesa connessione dal pool
                # NO connect_args per evitare conflitti con oracledb
            }
            
            # Crea l'engine con configurazione ottimizzata
            engine = create_engine(
                connection_string,
                **pool_config,
                echo=False,
                echo_pool="debug",  # Log operazioni pool per diagnostica
                future=True
            )
            
            self._engines[connection_name] = engine
            logger.info(f"✅ Engine Oracle creato con successo per {connection_name}")
            
            return engine
            
        except ImportError:
            logger.error("❌ Libreria oracledb non installata. Installa con: pip install oracledb")
            return None
        except Exception as e:
            logger.error(f"❌ Errore creazione engine Oracle per {connection_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _safe_connection_string(self, connection_string: str) -> str:
        """Oscura password nella connection string per logging sicuro"""
        if ":" in connection_string and "@" in connection_string:
            parts = connection_string.split("@")
            if len(parts) >= 2:
                user_pass_part = parts[0]
                if ":" in user_pass_part:
                    user_part = user_pass_part.rsplit(":", 1)[0]
                    return f"{user_part}:***@{parts[1]}"
        return connection_string
    
    def _get_pool_config(self, db_type: str) -> Dict[str, Any]:
        """Ottiene la configurazione del pool per tipo di database"""
        base_config = {
            "poolclass": QueuePool,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,
            "pool_recycle": 1800,  # 30min invece di 1h
            "pool_timeout": 30
        }
        
        if db_type.lower() == "oracle":
            base_config.update({
                "pool_size": 3,
                "max_overflow": 5,
                "pool_pre_ping": True,  # CRITICO per Oracle
                "pool_recycle": 1800,   # 30min
                "pool_timeout": 30,
                # oracledb moderno NON supporta encoding/nencoding
                "connect_args": {}
            })
        elif db_type.lower() == "postgresql":
            base_config.update({
                "connect_args": {
                    "client_encoding": "utf8",
                    "connect_timeout": 30
                }
            })
        elif db_type.lower() == "sqlserver":
            base_config.update({
                "connect_args": {
                    "timeout": 30,
                    "TrustServerCertificate": "yes"
                }
            })
        
        return base_config
    
    def test_connection(self, connection_name: str) -> ConnectionTest:
        """Testa una connessione database"""
        start_time = time.time()
        
        try:
            # Ottiene l'engine (creandolo se necessario)
            engine = self._create_engine(connection_name)
            
            if not engine:
                return ConnectionTest(
                    connection_name=connection_name,
                    success=False,
                    error_message="Impossibile creare l'engine database"
                )
            
            # Esegue una query di test
            test_query = self._get_test_query(connection_name)
            
            with engine.connect() as conn:
                result = conn.execute(text(test_query))
                result.fetchone()  # Forza l'esecuzione
            
            response_time = (time.time() - start_time) * 1000
            
            # Salva l'engine se il test ha successo
            self._engines[connection_name] = engine
            
            logger.info(f"Test connessione riuscito per {connection_name} in {response_time:.2f}ms")
            
            return ConnectionTest(
                connection_name=connection_name,
                success=True,
                response_time_ms=response_time
            )
            
        except SQLAlchemyError as e:
            response_time = (time.time() - start_time) * 1000
            error_msg = f"Errore database: {str(e)}"
            
            logger.error(f"Test connessione fallito per {connection_name}: {error_msg}")
            logger.error(f"Tipo errore SQLAlchemy: {type(e).__name__}")
            logger.error(f"Dettagli: {e}")
            
            # Rimuovi l'engine se esiste
            if connection_name in self._engines:
                del self._engines[connection_name]
            
            return ConnectionTest(
                connection_name=connection_name,
                success=False,
                response_time_ms=response_time,
                error_message=error_msg
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_msg = f"Errore generico: {str(e)}"
            
            logger.error(f"Test connessione fallito per {connection_name}: {error_msg}")
            logger.error(f"Tipo errore: {type(e).__name__}")
            logger.error(f"Dettagli completi: {e}")
            
            return ConnectionTest(
                connection_name=connection_name,
                success=False,
                response_time_ms=response_time,
                error_message=error_msg
            )
    
    def _get_test_query(self, connection_name: str) -> str:
        """Ottiene la query di test appropriata per il tipo di database"""
        try:
            conn_config = None
            for config in self._connections_config.connections:
                if config.name == connection_name:
                    conn_config = config
                    break
            
            if not conn_config:
                return "SELECT 1"
            
            db_type = conn_config.db_type.lower()
            
            if db_type == "oracle":
                return "SELECT 1 FROM DUAL"
            elif db_type == "postgresql":
                return "SELECT 1"
            elif db_type == "sqlserver":
                return "SELECT 1"
            else:
                return "SELECT 1"
                
        except Exception as e:
            logger.error(f"Errore nella determinazione query di test: {e}")
            return "SELECT 1"
    
    def close_connection(self, connection_name: str) -> bool:
        """Chiude una connessione specifica"""
        try:
            if connection_name in self._engines:
                self._engines[connection_name].dispose()
                del self._engines[connection_name]
                logger.info(f"Connessione chiusa: {connection_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Errore nella chiusura della connessione {connection_name}: {e}")
            return False
    
    def close_all_connections(self):
        """Chiude tutte le connessioni aperte"""
        try:
            for connection_name in list(self._engines.keys()):
                self.close_connection(connection_name)
            logger.info("Tutte le connessioni sono state chiuse")
        except Exception as e:
            logger.error(f"Errore nella chiusura delle connessioni: {e}")
    
    def get_pool_status(self, connection_name: str) -> Dict[str, Any]:
        """Ottiene lo stato del connection pool per diagnostica"""
        try:
            if connection_name not in self._engines:
                return {"error": "Connessione non trovata"}
            
            engine = self._engines[connection_name]
            pool = engine.pool
            
            return {
                "connection_name": connection_name,
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "status": "healthy" if pool.checkedin() > 0 else "warning"
            }
        except Exception as e:
            logger.error(f"Errore nel recupero stato pool {connection_name}: {e}")
            return {"error": str(e)}
    
    def __del__(self):
        """Destructor - chiude tutte le connessioni"""
        try:
            self.close_all_connections()
        except:
            pass
