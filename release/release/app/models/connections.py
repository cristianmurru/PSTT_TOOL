"""
Modelli per la gestione delle connessioni database
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class DatabaseType(str, Enum):
    """Tipi di database supportati"""
    ORACLE = "oracle"
    POSTGRESQL = "postgresql"
    SQLSERVER = "sqlserver"


class ConnectionStatus(str, Enum):
    """Stati delle connessioni"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TESTING = "testing"


class DatabaseConnection(BaseModel):
    """Modello per una connessione database"""
    name: str = Field(..., description="Nome univoco della connessione")
    environment: str = Field(..., description="Ambiente (collaudo, certificazione, produzione)")
    db_type: DatabaseType = Field(..., description="Tipo di database")
    description: str = Field("", description="Descrizione della connessione")
    params: Dict[str, Any] = Field(..., description="Parametri di connessione")
    
    # Campi runtime (non persistiti)
    status: ConnectionStatus = Field(default=ConnectionStatus.DISCONNECTED, description="Stato connessione")
    last_connected: Optional[datetime] = Field(default=None, description="Ultimo collegamento riuscito")
    last_error: Optional[str] = Field(default=None, description="Ultimo errore riscontrato")
    
    model_config = ConfigDict(use_enum_values=True)
    
    def get_connection_string(self, env_vars: Dict[str, str]) -> str:
        """Genera la connection string per SQLAlchemy"""
        # Sostituisci le variabili d'ambiente nei parametri
        resolved_params = {}
        for key, value in self.params.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]  # Rimuovi ${ e }
                resolved_params[key] = env_vars.get(env_var, value)
            else:
                resolved_params[key] = value
        
        if self.db_type == DatabaseType.ORACLE:
            # Oracle connection string - usa formato EZConnect per service_name
            service_name = resolved_params.get('service_name')
            host = resolved_params['host']
            port = resolved_params['port']
            username = resolved_params['username']
            password = resolved_params['password']
            
            if service_name:
                # Formato EZConnect: host:port/service_name
                return f"oracle+oracledb://{username}:{password}@{host}:{port}/{service_name}"
            else:
                # Fallback al formato classico
                return (f"oracle+oracledb://{username}:"
                       f"{password}@{host}:"
                       f"{port}/{resolved_params.get('sid', 'ORCL')}")
                   
        elif self.db_type == DatabaseType.POSTGRESQL:
            # PostgreSQL connection string
            return (f"postgresql+psycopg2://{resolved_params['username']}:"
                   f"{resolved_params['password']}@{resolved_params['host']}:"
                   f"{resolved_params['port']}/{resolved_params['service_name']}")
                   
        elif self.db_type == DatabaseType.SQLSERVER:
            # SQL Server connection string
            return (f"mssql+pyodbc://{resolved_params['username']}:"
                   f"{resolved_params['password']}@{resolved_params['host']}:"
                   f"{resolved_params['port']}/{resolved_params['database']}?"
                   f"driver=ODBC+Driver+17+for+SQL+Server")
        
        else:
            raise ValueError(f"Tipo database non supportato: {self.db_type}")


class ConnectionTest(BaseModel):
    """Risultato di un test di connessione"""
    connection_name: str
    success: bool
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    tested_at: datetime = Field(default_factory=datetime.utcnow)


class ConnectionsResponse(BaseModel):
    """Risposta API per lista connessioni"""
    connections: List[DatabaseConnection]
    default_connection: str
    environments: List[str]
    default_environment: str


class ConnectionTestRequest(BaseModel):
    """Richiesta per testare una connessione"""
    connection_name: str


class ConnectionSwitchRequest(BaseModel):
    """Richiesta per cambiare connessione attiva"""
    connection_name: str
