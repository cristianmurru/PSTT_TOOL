"""
Modelli per la schedulazione automatica delle query
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, date, timedelta
from enum import Enum
import re


class SharingMode(str, Enum):
    FILESYSTEM = "filesystem"
    EMAIL = "email"


class SchedulingItem(BaseModel):
    query: str = Field(..., description="Nome file query da schedulare")
    connection: str = Field(..., description="Nome connessione database")
    enabled: bool = Field(default=True, description="Job attivo/disattivo")
    description: Optional[str] = Field(None, description="Descrizione job")

    # Pianificazione: modalità 'classic' (giorni,hour,minute) o 'cron'
    scheduling_mode: Literal['classic', 'cron'] = Field('classic', description="Modalità di scheduling: 'classic' o 'cron'")
    # Classic fields
    days_of_week: Optional[List[int]] = Field(None, description="Giorni della settimana (0=Mon .. 6=Sun)")
    hour: Optional[int] = Field(None, description="Ora di esecuzione (0-23)")
    minute: Optional[int] = Field(None, description="Minuto di esecuzione (0-59)")
    # Cron expression (se scheduling_mode == 'cron')
    cron_expression: Optional[str] = Field(None, description="Espressione cron in formato standard (5 campi)")

    # Data fine (spostato come campo principale)
    end_date: Optional[date] = Field(None, description="Data di fine esecuzione del job (YYYY-MM-DD)")

    # Configurazione nome file output
    output_filename_template: Optional[str] = Field("{query_name}_{date}.xlsx", description="Template nome file output, usa {query_name}, {date}, {date-1}, {timestamp}")
    output_date_format: Optional[str] = Field("%Y-%m-%d", description="Formato data per {date}")
    output_offset_days: Optional[int] = Field(0, description="Offset giorni applicato per {date}, es: -1 per ieri")
    output_include_timestamp: Optional[bool] = Field(False, description="Includi timestamp completo nel nome file")

    # Condivisione file
    sharing_mode: SharingMode = Field(SharingMode.FILESYSTEM, description="Modalità di condivisione: filesystem o email")
    output_dir: Optional[str] = Field(None, description="Percorso directory di esportazione (se filesystem)")
    # Email fields
    email_recipients: Optional[str] = Field(None, description="[DEPRECATO] Usa email_to. Destinatari email separati da pipe | (compatibilità)")
    email_to: Optional[str] = Field(None, description="Destinatari A (To), separati da pipe |")
    email_cc: Optional[str] = Field(None, description="Destinatari CC, separati da pipe |")
    email_subject: Optional[str] = Field(None, description="Oggetto email personalizzabile")
    email_body: Optional[str] = Field(None, description="Corpo email plain text")

    def _build_token_replacements(self, exec_dt: Optional[datetime] = None) -> dict:
        """Costruisce dizionario di sostituzione token comuni.

        Supportati: {query_name}, {date}, {date-1}, {timestamp}
        """
        dt = exec_dt or datetime.now()
        # apply offset
        target_date = (dt + timedelta(days=self.output_offset_days)).date()
        # preserva trattini e underscore, rimuovi altri caratteri non alfanumerici
        qname = self.query.replace('.sql', '')
        qname = re.sub(r"[^0-9A-Za-z_\-]+", "_", qname)
        
        replacements = {
            "query_name": qname,
            "date": target_date.strftime(self.output_date_format or "%Y-%m-%d"),
            "timestamp": dt.strftime('%Y-%m-%d_%H-%M')
        }
        
        # support {date-1} pattern
        d_minus_1 = (dt + timedelta(days=self.output_offset_days - 1)).date()
        replacements["date-1"] = d_minus_1.strftime(self.output_date_format or "%Y-%m-%d")
        
        return replacements

    def render_string(self, template: str, exec_dt: Optional[datetime] = None) -> str:
        """Sostituisce i token in una stringa generica.

        Supportati: {query_name}, {date}, {date-1}, {timestamp}
        """
        if not template:
            return template
        
        replacements = self._build_token_replacements(exec_dt)
        result = template
        for k, v in replacements.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result

    def render_filename(self, exec_dt: Optional[datetime] = None) -> str:
        """Genera il filename sostituendo i placeholder nel template.

        Supportati: {query_name}, {date}, {date-1}, {timestamp}
        """
        replacements = self._build_token_replacements(exec_dt)
        tpl = self.output_filename_template or "{query_name}_{date}.xlsx"
        
        # simple replacement
        fname = tpl
        for k, v in replacements.items():
            fname = fname.replace(f"{{{k}}}", str(v))
        
        # if timestamp requested but not in template, append if flag set
        if self.output_include_timestamp and "{timestamp}" not in fname:
            fname = f"{fname.rstrip('.xlsx')}_{replacements['timestamp']}.xlsx"
        return fname


class SchedulingHistoryItem(BaseModel):
    query: str
    connection: str
    timestamp: datetime
    status: str  # success, fail
    duration_sec: Optional[float] = None  # in secondi
    row_count: Optional[int] = None
    error: Optional[str] = None
