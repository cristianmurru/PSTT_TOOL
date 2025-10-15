"""
Servizio per la gestione e l'esecuzione delle query SQL
"""
import re
import os
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from app.core.config import get_settings
from app.services.connection_service import ConnectionService
from app.models.queries import (
    QueryInfo, 
    QueryParameter, 
    ParameterType,
    QueryExecutionRequest,
    QueryExecutionResult
)


class QueryService:
    """Servizio per la gestione e l'esecuzione delle query SQL"""
    
    def __init__(self):
        self.settings = get_settings()
        self.connection_service = ConnectionService()
        
        # Pattern per identificare parametri nelle query
        self.define_pattern = re.compile(r"define\s+(\w+)\s*=\s*['\"]([^'\"]*)['\"](?:\s*--\s*(.*))?", re.IGNORECASE)
        self.parameter_pattern = re.compile(r"&(\w+)", re.IGNORECASE)
        
        logger.info(f"QueryService inizializzato - directory query: {self.settings.query_dir}")
    
    def get_queries(self) -> List[QueryInfo]:
        """Ottiene la lista di tutte le query disponibili"""
        try:
            queries = []
            
            if not self.settings.query_dir.exists():
                logger.warning(f"Directory query non trovata: {self.settings.query_dir}")
                return queries
            
            # Scansiona tutti i file SQL nella directory
            for sql_file in self.settings.query_dir.glob("*.sql"):
                try:
                    query_info = self._parse_sql_file(sql_file)
                    if query_info:
                        queries.append(query_info)
                except Exception as e:
                    logger.error(f"Errore nel parsing del file {sql_file}: {e}")
                    continue
            
            # Ordina per nome file
            queries.sort(key=lambda q: q.filename)
            
            logger.info(f"Trovate {len(queries)} query SQL")
            return queries
            
        except Exception as e:
            logger.error(f"Errore nel recupero delle query: {e}")
            return []
    
    def get_query(self, filename: str) -> Optional[QueryInfo]:
        """Ottiene i dettagli di una query specifica"""
        try:
            sql_file = self.settings.query_dir / filename
            
            if not sql_file.exists():
                logger.error(f"File query non trovato: {filename}")
                return None
            
            return self._parse_sql_file(sql_file)
            
        except Exception as e:
            logger.error(f"Errore nel recupero della query {filename}: {e}")
            return None
    
    def _parse_sql_file(self, sql_file: Path) -> Optional[QueryInfo]:
        """Parsa un file SQL ed estrae le informazioni"""
        try:
            # Prova diverse codifiche per i file SQL
            content = None
            encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    with open(sql_file, 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.debug(f"File {sql_file.name} letto con encoding {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                logger.error(f"Impossibile leggere il file {sql_file.name} con nessuna codifica supportata")
                return None
            
            # Informazioni base del file
            file_stats = sql_file.stat()
            
            # Estrai titolo dal nome del file
            title = self._extract_title_from_filename(sql_file.name)
            
            # Estrai parametri dalla query
            parameters = self._extract_parameters(content)
            
            # Estrai descrizione dai commenti iniziali
            description = self._extract_description(content)
            
            return QueryInfo(
                filename=sql_file.name,
                full_path=str(sql_file),
                title=title,
                description=description,
                parameters=parameters,
                sql_content=content,
                modified_at=datetime.fromtimestamp(file_stats.st_mtime),
                size_bytes=file_stats.st_size
            )
            
        except Exception as e:
            logger.error(f"Errore nel parsing del file {sql_file}: {e}")
            return None
    
    def _extract_title_from_filename(self, filename: str) -> str:
        """Estrae un titolo leggibile dal nome del file"""
        try:
            # Rimuovi estensione
            name = filename.replace('.sql', '')
            
            # Pattern tipico: "BOSC-NXV--001--Accessi operatori.sql"
            # Prende l'ultima parte dopo l'ultimo "--"
            if '--' in name:
                parts = name.split('--')
                if len(parts) > 1:
                    title = parts[-1].strip()
                    # Capitalizza la prima lettera di ogni parola
                    return ' '.join(word.capitalize() for word in title.split())
            
            # Fallback: usa il nome completo
            return name.replace('_', ' ').replace('-', ' ').title()
            
        except Exception as e:
            logger.error(f"Errore nell'estrazione del titolo da {filename}: {e}")
            return filename
    
    def _extract_description(self, content: str) -> Optional[str]:
        """Estrae la descrizione dai commenti iniziali della query"""
        try:
            lines = content.split('\n')
            description_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('--'):
                    desc_line = line[2:].strip()
                    # Ignora commenti step
                    if desc_line and not desc_line.upper().startswith('STEP') and not desc_line.startswith('$STEP'):
                        description_lines.append(desc_line)
                elif description_lines:
                    break
                elif any(keyword in line.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'DEFINE']):
                    break
            if description_lines:
                return ' '.join(description_lines)
            return None
        except Exception as e:
            logger.error(f"Errore nell'estrazione della descrizione: {e}")
            return None
    
    def _extract_parameters(self, content: str) -> List[QueryParameter]:
        """Estrae i parametri dalla query SQL"""
        try:
            parameters = []
            found_params = set()  # Per evitare duplicati
            
            # Trova tutti i parametri 'define'
            for match in self.define_pattern.finditer(content):
                param_name = match.group(1)
                default_value = match.group(2) or ""
                comment = match.group(3) or ""
                
                # Determina se è obbligatorio dal commento
                required = True
                if comment and any(opt in comment.lower() for opt in ['opzionale', 'optional', 'facoltativo']):
                    required = False
                elif comment and any(req in comment.lower() for req in ['obbligatorio', 'required', 'mandatory']):
                    required = True
                
                # Determina il tipo dal valore di default o dal nome
                param_type = self._infer_parameter_type(param_name, default_value)
                
                parameter = QueryParameter(
                    name=param_name,
                    parameter_type=param_type,
                    required=required,
                    default_value=default_value if default_value else None,
                    description=comment if comment else None
                )
                
                parameters.append(parameter)
                found_params.add(param_name)
            
            # Trova parametri aggiuntivi nel corpo della query (&PARAM)
            for match in self.parameter_pattern.finditer(content):
                param_name = match.group(1)
                
                # Salta se già trovato nei define
                if param_name in found_params:
                    continue
                
                # Crea parametro generico
                parameter = QueryParameter(
                    name=param_name,
                    parameter_type=ParameterType.STRING,
                    required=True,  # Default obbligatorio se non specificato
                    default_value=None,
                    description=f"Parametro {param_name} (non definito esplicitamente)"
                )
                
                parameters.append(parameter)
                found_params.add(param_name)
            
            logger.debug(f"Trovati {len(parameters)} parametri nella query")
            return parameters
            
        except Exception as e:
            logger.error(f"Errore nell'estrazione dei parametri: {e}")
            return []
    
    def _infer_parameter_type(self, param_name: str, default_value: str) -> ParameterType:
        """Inferisce il tipo del parametro dal nome e valore di default"""
        try:
            param_name_lower = param_name.lower()
            # Controlla per date
            if any(date_keyword in param_name_lower for date_keyword in ['data', 'date', 'inizio', 'fine', 'start', 'end']):
                return ParameterType.DATE
            # Controlla per timestamp/datetime
            if any(ts_keyword in param_name_lower for ts_keyword in ['timestamp', 'datetime', 'time']):
                return ParameterType.DATETIME
            # Alcuni nomi tipo ENABLED/ACTIVE/FLAG sono booleani
            if any(k in param_name_lower for k in ['enabled', 'active', 'flag', 'is_']):
                if default_value and default_value.lower() in ['1', '0', 'true', 'false', 'yes', 'no']:
                    return ParameterType.BOOLEAN
                # If no default, assume boolean for these prefixed names
                if not default_value:
                    return ParameterType.BOOLEAN

            # Controlla per numeri
            if any(num_keyword in param_name_lower for num_keyword in ['id', 'count', 'num', 'qty', 'amount']):
                # Prova a interpretare come float
                try:
                    if default_value and '.' in default_value:
                        float(default_value)
                        return ParameterType.FLOAT
                    elif default_value:
                        int(default_value)
                        return ParameterType.INTEGER
                except ValueError:
                    pass
                # Se non c'è valore di default, preferisci INTEGER
                return ParameterType.INTEGER
            # Controlla il valore di default
            if default_value:
                # Prova a interpretare come data (formato dd/mm/yyyy)
                if re.match(r'\d{2}/\d{2}/\d{4}', default_value):
                    return ParameterType.DATE
                # Prova a interpretare come float
                try:
                    if '.' in default_value:
                        float(default_value)
                        return ParameterType.FLOAT
                    else:
                        int(default_value)
                        return ParameterType.INTEGER
                except ValueError:
                    pass
                # Controlla per valori booleani
                if default_value.lower() in ['true', 'false', '1', '0', 'yes', 'no']:
                    return ParameterType.BOOLEAN
            # Alcuni nomi tipo ENABLED/ACTIVE/FLAG sono booleani anche se default è '1'/'0'
            if any(k in param_name_lower for k in ['enabled', 'active', 'flag', 'is_']):
                if default_value and default_value.lower() in ['1', '0', 'true', 'false', 'yes', 'no']:
                    return ParameterType.BOOLEAN
            # Default: string
            return ParameterType.STRING
        except Exception as e:
            logger.error(f"Errore nell'inferenza del tipo parametro {param_name}: {e}")
            return ParameterType.STRING
    
    def _sanitize_sql_for_oracle(self, sql: str) -> str:
        """Rimuove caratteri speciali non validi alla fine della query per Oracle."""
        # Rimuove spazi, tab, newline e altri caratteri non stampabili alla fine
        return sql.rstrip()

    def execute_query(self, request: QueryExecutionRequest) -> QueryExecutionResult:
        start_time = time.time()
        try:
            query_info = self.get_query(request.query_filename)
            if not query_info:
                return QueryExecutionResult(
                    query_filename=request.query_filename,
                    connection_name=request.connection_name,
                    success=False,
                    execution_time_ms=0,
                    row_count=0,
                    error_message=f"Query non trovata: {request.query_filename}"
                )
            missing_params = self._validate_parameters(query_info.parameters, request.parameters)
            if missing_params:
                return QueryExecutionResult(
                    query_filename=request.query_filename,
                    connection_name=request.connection_name,
                    success=False,
                    execution_time_ms=0,
                    row_count=0,
                    error_message=f"Parametri obbligatori mancanti: {', '.join(missing_params)}"
                )
            processed_sql = self._substitute_parameters(query_info.sql_content, request.parameters, query_info.parameters)
            engine = self.connection_service.get_engine(request.connection_name)
            if not engine:
                return QueryExecutionResult(
                    query_filename=request.query_filename,
                    connection_name=request.connection_name,
                    success=False,
                    execution_time_ms=0,
                    row_count=0,
                    error_message=f"Impossibile connettersi al database: {request.connection_name}"
                )
            # STEP LOGIC
            steps = self._parse_sql_steps(processed_sql)
            if len(steps) == 1 and steps[0]["description"] == "Query unica":
                # Query semplice, esegui come prima
                with engine.connect() as conn:
                    if request.limit and request.limit > 0:
                        processed_sql = self._add_limit_clause(processed_sql, request.limit, request.connection_name)
                    connection = self.connection_service.get_connection(request.connection_name)
                    db_type = connection.db_type.lower() if connection else None
                    sql_to_execute = processed_sql
                    if db_type == "oracle":
                        sql_to_execute = self._sanitize_sql_for_oracle(sql_to_execute)
                    tmp_dir = Path(self.settings.query_dir) / "tmp"
                    tmp_dir.mkdir(parents=True, exist_ok=True)
                    tmp_file = tmp_dir / "tmp.txt"
                    try:
                        with open(tmp_file, "w", encoding="utf-8") as f:
                            f.write(sql_to_execute)
                    except Exception as e:
                        logger.error(f"Impossibile salvare la query in tmp.txt: {e}")
                    result = conn.execute(text(sql_to_execute))
                    rows = result.fetchall()
                    column_names = list(result.keys()) if result.keys() else []
                    data = []
                    for row in rows:
                        row_dict = {}
                        for i, col_name in enumerate(column_names):
                            value = row[i] if i < len(row) else None
                            if isinstance(value, datetime):
                                row_dict[col_name] = value.isoformat()
                            else:
                                row_dict[col_name] = value
                        data.append(row_dict)
                    execution_time = (time.time() - start_time) * 1000
                    logger.info(f"Query {request.query_filename} eseguita con successo: {len(data)} righe in {execution_time:.2f}ms")
                    return QueryExecutionResult(
                        query_filename=request.query_filename,
                        connection_name=request.connection_name,
                        success=True,
                        execution_time_ms=execution_time,
                        row_count=len(data),
                        column_names=column_names,
                        data=data,
                        parameters_used=request.parameters
                    )
            else:
                # Multi-step
                last_result = None
                with engine.connect() as conn:
                    for step in steps:
                        sql_to_execute = step["sql"]
                        # Sostituisci parametri per ogni step
                        # Prima, crea una copia dei parametri e aggiungi quelli opzionali mancanti come stringa vuota
                        param_values = dict(request.parameters)
                        for param in query_info.parameters:
                            if param.name not in param_values:
                                param_values[param.name] = ""
                        sql_to_execute = self._substitute_parameters(sql_to_execute, param_values, query_info.parameters)
                        # Rimuovi punto e virgola finale
                        sql_to_execute = sql_to_execute.rstrip().rstrip(';')
                        connection = self.connection_service.get_connection(request.connection_name)
                        db_type = connection.db_type.lower() if connection else None
                        if db_type == "oracle":
                            sql_to_execute = self._sanitize_sql_for_oracle(sql_to_execute)
                        tmp_dir = Path(self.settings.query_dir) / "tmp"
                        tmp_dir.mkdir(parents=True, exist_ok=True)
                        tmp_file = tmp_dir / f"tmp_step{step['number']}.txt"
                        try:
                            with open(tmp_file, "w", encoding="utf-8") as f:
                                f.write(sql_to_execute)
                        except Exception as e:
                            logger.error(f"Impossibile salvare la query in tmp_step{step['number']}.txt: {e}")
                        is_select = sql_to_execute.strip().lower().startswith("select") or sql_to_execute.strip().lower().startswith("with")
                        try:
                            result = conn.execute(text(sql_to_execute))
                            if db_type == "oracle" and not is_select:
                                conn.commit()
                        except Exception as e:
                            execution_time = (time.time() - start_time) * 1000
                            return QueryExecutionResult(
                                query_filename=request.query_filename,
                                connection_name=request.connection_name,
                                success=False,
                                execution_time_ms=execution_time,
                                row_count=0,
                                error_message=str(e),
                                parameters_used=request.parameters
                            )
                        if is_select:
                            rows = result.fetchall()
                            column_names = list(result.keys()) if result.keys() else []
                            data = []
                            for row in rows:
                                row_dict = {}
                                for i, col_name in enumerate(column_names):
                                    value = row[i] if i < len(row) else None
                                    if isinstance(value, datetime):
                                        row_dict[col_name] = value.isoformat()
                                    else:
                                        row_dict[col_name] = value
                                data.append(row_dict)
                            execution_time = (time.time() - start_time) * 1000
                            last_result = QueryExecutionResult(
                                query_filename=request.query_filename,
                                connection_name=request.connection_name,
                                success=True,
                                execution_time_ms=execution_time,
                                row_count=len(data),
                                column_names=column_names,
                                data=data,
                                parameters_used=request.parameters
                            )
                if last_result:
                    return last_result
                else:
                    execution_time = (time.time() - start_time) * 1000
                    return QueryExecutionResult(
                        query_filename=request.query_filename,
                        connection_name=request.connection_name,
                        success=True,
                        execution_time_ms=execution_time,
                        row_count=0,
                        column_names=[],
                        data=[],
                        parameters_used=request.parameters
                    )
    
        except Exception as e:
            logger.error(f"Errore generico in execute_query: {e}")
            execution_time = (time.time() - start_time) * 1000
            return QueryExecutionResult(
                query_filename=request.query_filename,
                connection_name=request.connection_name,
                success=False,
                execution_time_ms=execution_time,
                row_count=0,
                error_message=f"Errore generico: {str(e)}",
                parameters_used=request.parameters
            )
    
    def _validate_parameters(self, query_params: List[QueryParameter], provided_params: Dict[str, Any]) -> List[str]:
        """Valida che tutti i parametri obbligatori siano forniti"""
        missing = []
        
        for param in query_params:
            if param.required and param.name not in provided_params:
                # Controlla se ha un valore di default
                if not param.default_value:
                    missing.append(param.name)
        
        return missing
    
    def _substitute_parameters(self, sql_content: str, params: dict, query_params: list) -> str:
        """Sostituisce i parametri nella query SQL"""
        try:
            processed_sql = sql_content
            param_values = {}
            # Prima aggiungi i valori di default
            for param in query_params:
                if param.default_value is not None:
                    param_values[param.name] = param.default_value
            # Poi sovrascrivi con i valori forniti
            for param_name, param_value in params.items():
                param_values[param_name] = str(param_value) if param_value is not None else ""
            # Rimuovi le righe 'define'
            processed_sql = re.sub(r'define\s+\w+\s*=.*?(?=\n|$)', '', processed_sql, flags=re.IGNORECASE | re.MULTILINE)
            # Sostituisci TUTTI i parametri &PARAM con il valore o stringa vuota
            def replace_param(match):
                name = match.group(1)
                return param_values.get(name, "")
            processed_sql = re.sub(r'&([A-Za-z0-9_]+)', replace_param, processed_sql)
            return processed_sql
        except Exception as e:
            logger.error(f"Errore nella sostituzione dei parametri: {e}")
            return sql_content
    
    def _add_limit_clause(self, sql: str, limit: int, connection_name: str) -> str:
        """Esegue la query così come è scritta nel file .sql, senza aggiungere LIMIT/ROWNUM per Oracle."""
        try:
            connection = self.connection_service.get_connection(connection_name)
            if not connection:
                return sql
            db_type = connection.db_type.lower()
            sql_upper = sql.upper()
            # Se il db è Oracle, NON aggiungere nulla
            if db_type == "oracle":
                return sql
            # Per gli altri db mantieni la logica precedente
            if any(keyword in sql_upper for keyword in ['LIMIT', 'ROWNUM', 'TOP', 'FETCH']):
                return sql  # Query ha già limitazioni
            if db_type in ["postgresql", "mysql"]:
                return f"{sql} LIMIT {limit}"
            elif db_type == "sqlserver":
                return re.sub(r'\bSELECT\b', f'SELECT TOP {limit}', sql, count=1, flags=re.IGNORECASE)
            else:
                return f"{sql} LIMIT {limit}"
        except Exception:
            return sql
    
    def _parse_sql_steps(self, sql_content: str):
        pattern = r"--\$STEP\s*(\d+)\$\s*->\s*(.*)"
        matches = list(re.finditer(pattern, sql_content))
        steps = []
        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(sql_content)
            step_sql = sql_content[start:end].strip()
            steps.append({
                "number": int(match.group(1)),
                "description": match.group(2).strip(),
                "sql": step_sql
            })
        if not steps:
            return [{"number": 1, "description": "Query unica", "sql": sql_content.strip()}]
        return steps

    def get_active_jobs_count(self) -> int:
        """Restituisce il numero di job attivi nel scheduler, esclusi quelli di pulizia."""
        return len([job for job in self.scheduler.get_jobs() if not job.name.lower().startswith("cleanup")]) if self.scheduler else 0
