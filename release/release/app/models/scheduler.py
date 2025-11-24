"""
Modelli per il sistema di scheduling
"""
from datetime import datetime, time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ScheduleStatus(str, Enum):
    """Stati delle schedule"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class JobStatus(str, Enum):
    """Stati dei job"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduledQuery(BaseModel):
    """Query schedulata"""
    id: str = Field(..., description="ID univoco della schedule")
    query_filename: str = Field(..., description="Nome del file query")
    connection_name: str = Field(..., description="Nome connessione da usare")
    description: Optional[str] = Field(default=None, description="Descrizione della schedule")
    
    # Parametri scheduling
    cron_expression: str = Field(..., description="Espressione cron per scheduling")
    timezone: str = Field(default="Europe/Rome", description="Timezone per l'esecuzione")
    
    # Parametri query
    parameters: Dict[str, Any] = Field(default={}, description="Parametri fissi della query")
    
    # Export settings
    export_format: str = Field(default="excel", description="Formato export")
    compress: bool = Field(default=True, description="Se comprimere l'output")
    
    # Stato
    status: ScheduleStatus = Field(default=ScheduleStatus.ACTIVE, description="Stato della schedule")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data creazione")
    last_run: Optional[datetime] = Field(default=None, description="Ultima esecuzione")
    next_run: Optional[datetime] = Field(default=None, description="Prossima esecuzione")
    
    model_config = ConfigDict(use_enum_values=True)


class JobExecution(BaseModel):
    """Esecuzione di un job schedulato"""
    id: str = Field(..., description="ID univoco del job")
    schedule_id: str = Field(..., description="ID della schedule")
    query_filename: str = Field(..., description="Nome file query")
    connection_name: str = Field(..., description="Nome connessione")
    
    # Stato esecuzione
    status: JobStatus = Field(default=JobStatus.PENDING, description="Stato del job")
    started_at: Optional[datetime] = Field(default=None, description="Inizio esecuzione")
    completed_at: Optional[datetime] = Field(default=None, description="Fine esecuzione")
    duration_ms: Optional[float] = Field(default=None, description="Durata in millisecondi")
    
    # Risultati
    row_count: Optional[int] = Field(default=None, description="Numero righe elaborate")
    output_file: Optional[str] = Field(default=None, description="File di output generato")
    file_size_bytes: Optional[int] = Field(default=None, description="Dimensione file output")
    
    # Errori
    error_message: Optional[str] = Field(default=None, description="Messaggio di errore")
    stack_trace: Optional[str] = Field(default=None, description="Stack trace errore")
    
    model_config = ConfigDict(use_enum_values=True)


class ScheduleListResponse(BaseModel):
    """Risposta API per lista schedule"""
    schedules: List[ScheduledQuery]
    total_count: int


class JobListResponse(BaseModel):
    """Risposta API per lista job executions"""
    jobs: List[JobExecution]
    total_count: int


class CreateScheduleRequest(BaseModel):
    """Richiesta creazione schedule"""
    query_filename: str
    connection_name: str
    description: Optional[str] = None
    cron_expression: str
    parameters: Dict[str, Any] = Field(default={})
    export_format: str = Field(default="excel")
    compress: bool = Field(default=True)


class UpdateScheduleRequest(BaseModel):
    """Richiesta aggiornamento schedule"""
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    export_format: Optional[str] = None
    compress: Optional[bool] = None
    status: Optional[ScheduleStatus] = None


class ScheduleActionRequest(BaseModel):
    """Richiesta azione su schedule"""
    action: str = Field(..., description="Azione: start, stop, run_now")


class RetentionPolicySettings(BaseModel):
    """Impostazioni politica retention"""
    enabled: bool = Field(default=True, description="Se abilitare la pulizia automatica")
    retention_days: int = Field(default=30, description="Giorni di retention")
    check_interval_hours: int = Field(default=24, description="Intervallo controllo in ore")
    last_cleanup: Optional[datetime] = Field(default=None, description="Ultima pulizia eseguita")
