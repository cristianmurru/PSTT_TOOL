"""
Modelli per la gestione delle query e dei parametri
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ParameterType(str, Enum):
    """Tipi di parametri supportati"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"


class QueryParameter(BaseModel):
    """Parametro di una query"""
    name: str = Field(..., description="Nome del parametro")
    parameter_type: ParameterType = Field(default=ParameterType.STRING, description="Tipo del parametro")
    required: bool = Field(default=True, description="Se il parametro è obbligatorio")
    default_value: Optional[str] = Field(default=None, description="Valore di default")
    description: Optional[str] = Field(default=None, description="Descrizione del parametro")
    
    model_config = ConfigDict(use_enum_values=True)


class QueryInfo(BaseModel):
    """Informazioni su una query SQL"""
    filename: str = Field(..., description="Nome del file SQL")
    full_path: str = Field(..., description="Percorso completo del file")
    subdirectory: Optional[str] = Field(default=None, description="Sottodirectory relativa alla cartella Query")
    title: Optional[str] = Field(default=None, description="Titolo estratto dal nome file")
    description: Optional[str] = Field(default=None, description="Descrizione della query")
    parameters: List[QueryParameter] = Field(default=[], description="Parametri della query")
    sql_content: str = Field(..., description="Contenuto SQL")
    modified_at: Optional[datetime] = Field(default=None, description="Data ultima modifica")
    size_bytes: int = Field(default=0, description="Dimensione file in bytes")


class QueryExecutionRequest(BaseModel):
    """Richiesta di esecuzione query"""
    query_filename: str = Field(..., description="Nome del file query da eseguire")
    connection_name: str = Field(..., description="Nome della connessione da usare")
    parameters: Dict[str, Any] = Field(default={}, description="Valori dei parametri")
    limit: Optional[int] = Field(default=None, description="Limite righe risultato (None = nessun limite)")


class QueryExecutionResult(BaseModel):
    """Risultato dell'esecuzione di una query"""
    query_filename: str
    connection_name: str
    success: bool
    execution_time_ms: float
    row_count: int
    column_names: List[str] = Field(default=[])
    data: List[Dict[str, Any]] = Field(default=[])
    error_message: Optional[str] = None
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    parameters_used: Dict[str, Any] = Field(default={})


class QueryListResponse(BaseModel):
    """Risposta API per lista query"""
    queries: List[QueryInfo]
    total_count: int


class ExportRequest(BaseModel):
    """Richiesta di export risultati"""
    query_filename: str
    connection_name: str
    parameters: Dict[str, Any] = Field(default={})
    export_format: str = Field(default="excel", description="Formato export: excel, csv")
    compress: bool = Field(default=True, description="Se comprimere il file")


class ExportResult(BaseModel):
    """Risultato di un export"""
    filename: str
    file_path: str
    size_bytes: int
    row_count: int
    export_format: str
    compressed: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)
