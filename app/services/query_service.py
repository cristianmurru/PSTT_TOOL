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
        """Ottiene la lista di tutte le query disponibili (ricorsiva sulle sottocartelle)."""
        try:
            queries = []
            
            if not self.settings.query_dir.exists():
                logger.warning(f"Directory query non trovata: {self.settings.query_dir}")
                return queries
            
            # Scansiona ricorsivamente tutti i file .sql nelle sottocartelle, includendo radice
            for sql_file in self.settings.query_dir.rglob("*.sql"):
                # Escludi cartelle di lavoro temporanee
                try:
                    # subdir relativa rispetto alla query_dir
                    rel = sql_file.relative_to(self.settings.query_dir)
                    parts = rel.parts[:-1]  # tutte le parti tranne il filename
                    subdir = os.path.join(*parts) if parts else ""
                    # normalizza separatore cartelle in formato unix-like per coerenza
                    subdir = subdir.replace("\\", "/") if subdir else ""
                    # filtra cartelle da escludere (tmp sempre esclusa; altre esclusioni lato UI)
                    if any(p.lower() in ["tmp", "_tmp"] for p in parts):
                        continue
                except Exception:
                    subdir = ""
                try:
                    query_info = self._parse_sql_file(sql_file)
                    # aggiungi subdir metadata
                    if query_info:
                        query_info.subdirectory = subdir
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
        """Ottiene i dettagli di una query specifica (ricerca ricorsiva per nome file)."""
        try:
            # Cerca ricorsivamente il file per nome nelle sottocartelle
            for sql_file in self.settings.query_dir.rglob(filename):
                if sql_file.name.lower() == filename.lower():
                    info = self._parse_sql_file(sql_file)
                    if info:
                        try:
                            rel = sql_file.relative_to(self.settings.query_dir)
                            parts = rel.parts[:-1]
                            subdir = os.path.join(*parts) if parts else ""
                            info.subdirectory = subdir.replace("\\", "/") if subdir else ""
                        except Exception:
                            pass
                    return info
            logger.error(f"File query non trovato: {filename}")
            return None
            
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
        # Inoltre rimuove eventuali punti e virgola finali o slash (usati in script SQL*Plus)
        if not isinstance(sql, str):
            return sql
        s = sql.rstrip()
        # Rimuovi ripetutamente i terminatori espliciti di script (;) o slash (/)
        while s.endswith(';') or s.endswith('/'):
            s = s[:-1].rstrip()
        return s

    def save_query(self, filename: str, new_content: str) -> bool:
        """Salva il contenuto della query nel file corrispondente (ricerca ricorsiva per filename)."""
        try:
            for sql_file in self.settings.query_dir.rglob(filename):
                if sql_file.name.lower() == filename.lower():
                    # Usa UTF-8 e crea backup semplice
                    try:
                        backup = sql_file.with_suffix('.bak')
                        if sql_file.exists():
                            sql_file.replace(backup)
                            # ripristina bak originale se write fallisce
                        with open(sql_file, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        return True
                    except Exception as e:
                        logger.error(f"Errore salvataggio file {sql_file}: {e}")
                        # prova a ripristinare backup
                        try:
                            if backup.exists():
                                backup.replace(sql_file)
                        except Exception:
                            pass
                        return False
            logger.error(f"File query non trovato per salvataggio: {filename}")
            return False
        except Exception as e:
            logger.error(f"Errore save_query {filename}: {e}")
            return False

    def format_sql_basic(self, sql: str) -> str:
        """Formatter minimale: normalizza spazi, uppercase parole chiave comuni, indentazione semplice."""
        if not isinstance(sql, str):
            return sql
        s = sql.replace('\r\n', '\n').replace('\r', '\n')
        lines = [ln.strip() for ln in s.split('\n')]
        # Uppercase parole chiave al inizio riga
        keywords = [
            'select', 'from', 'where', 'group by', 'order by', 'join', 'left join', 'right join',
            'inner join', 'outer join', 'union', 'with', 'having', 'limit', 'offset', 'insert',
            'update', 'delete'
        ]
        def upkw(line: str) -> str:
            l = line.strip()
            low = l.lower()
            for kw in keywords:
                if low.startswith(kw):
                    return kw.upper() + l[len(kw):]
            return l
        lines = [upkw(ln) for ln in lines]
        # Aggiungi nuove linee prima di parole chiave importanti per leggibilità
        joined = '\n'.join(lines)
        for kw in [' FROM ', ' WHERE ', ' GROUP BY ', ' ORDER BY ', ' HAVING ', ' JOIN ', ' UNION ']:
            joined = re.sub(kw, '\n' + kw.strip() + ' ', joined, flags=re.IGNORECASE)
        # Indentazione semplice: aggiungi due spazi alle linee che seguono SELECT fino a FROM
        formatted_lines = []
        indent = False
        for ln in joined.split('\n'):
            low = ln.strip().lower()
            if low.startswith('select'):
                indent = True
                formatted_lines.append(ln)
                continue
            if low.startswith('from'):
                indent = False
            if indent and ln.strip():
                formatted_lines.append('  ' + ln)
            else:
                formatted_lines.append(ln)
        out = '\n'.join(formatted_lines)
        # Rimuovi terminatori finali superflui
        out = self._sanitize_sql_for_oracle(out)
        return out

    def suggest_optimizations(self, sql: str, connection_name: str | None) -> List[str]:
        """Genera suggerimenti di ottimizzazione in base al contenuto SQL e al tipo DB della connessione."""
        suggestions: List[str] = []
        try:
            conn = self.connection_service.get_connection(connection_name) if connection_name else None
            db_type = (conn.db_type.lower() if conn else '').lower()
            s = (sql or '').lower()
            if 'select *' in s:
                suggestions.append("Evita SELECT *: specifica le colonne necessarie.")
            if ' where ' in s and ('like' in s or 'upper(' in s or 'lower(' in s):
                suggestions.append("Evita funzioni sulla colonna in WHERE/LIKE: usa colonne normalizzate o indici dedicati.")
            if ' in (' in s:
                suggestions.append("Valuta EXISTS al posto di IN per subquery pesanti.")
            if ' join ' in s and ' on ' in s and ' where ' in s:
                suggestions.append("Controlla selettività delle condizioni JOIN/WHERE e presenza di indici coerenti.")
            if re.search(r'order\s+by', s):
                suggestions.append("Usa indici che supportino ORDER BY oppure limita righe prima di ordinare.")
            if re.search(r'between\s+\S+\s+and\s+\S+', s):
                suggestions.append("Per range ampi, valuta partizionamento o filtri più selettivi.")
            if db_type == 'oracle':
                suggestions.append("Oracle: assicurati di rimuovere ';' finali e valuta HINT /*+ INDEX(...) */ dove appropriato.")
            if db_type == 'postgresql':
                suggestions.append("PostgreSQL: verifica piani con EXPLAIN ANALYZE e indici su colonne di filtro.")
            if not suggestions:
                suggestions.append("La query sembra semplice; verifica comunque piani di esecuzione e indici.")
        except Exception as e:
            logger.error(f"Errore generazione suggerimenti: {e}")
        return suggestions

    def lint_sql(self, sql: str, connection_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Verifica sintattica base e potenziali problemi senza eseguire la query.
        Restituisce una lista di dict: {"type": "error|warning", "message": str}
        """
        issues: List[Dict[str, Any]] = []
        try:
            s = (sql or '')
            low = s.lower()
            # Empty or trivial
            if not s.strip():
                issues.append({"type": "error", "message": "SQL vuoto"})
                return issues
            # Basic structure checks
            is_select = low.strip().startswith('select') or low.strip().startswith('with')
            if is_select:
                if ' from ' not in f" {low} ":
                    issues.append({"type": "error", "message": "SELECT senza FROM"})
                # ORDER BY without select columns is allowed, but warn if '*' and no index hints
            # Parentheses balance
            if s.count('(') != s.count(')'):
                issues.append({"type": "error", "message": "Parentesi non bilanciate"})
            # Quotes balance (simple heuristic)
            if s.count("'") % 2 != 0:
                issues.append({"type": "error", "message": "Apici singoli non bilanciati"})
            # Trailing terminators
            if s.rstrip().endswith(';') or s.rstrip().endswith('/'):
                issues.append({"type": "warning", "message": "Rimuovi terminatori finali (';' o '/')"})
            # Suspicious ORDER BY on non-selected columns when using '*'
            try:
                if is_select and 'select *' in low and ' order by ' in low:
                    issues.append({"type": "warning", "message": "Usa colonne esplicite con ORDER BY per chiarezza e indici"})
            except Exception:
                pass
            # Potential schema/table check heuristic
            m_from = re.search(r'from\s+([a-z0-9_\.]+)', low)
            if m_from:
                table_ref = m_from.group(1)
                if '.' not in table_ref:
                    issues.append({"type": "warning", "message": "Specifica schema.tabella per evitare ambiguità"})
            # Oracle specific
            try:
                conn = self.connection_service.get_connection(connection_name) if connection_name else None
                db_type = (conn.db_type.lower() if conn else '').lower()
                if db_type == 'oracle':
                    # Warn common Oracle pitfalls
                    if 'rownum' in low and 'order by' in low:
                        issues.append({"type": "warning", "message": "ROWNUM con ORDER BY può produrre ordinamenti inattesi"})
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Errore lint SQL: {e}")
            issues.append({"type": "error", "message": "Errore interno nel lint"})
        return issues

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
            # Log parsed steps for diagnostics (first 200 chars each)
            try:
                for s in steps:
                    preview = s["sql"][:200].replace('\n', ' ')
                    logger.debug(f"[Diag] Step {s['number']} desc='{s['description']}' preview='{preview}'")
            except Exception:
                pass
            if len(steps) == 1 and steps[0]["description"] == "Query unica":
                # Query semplice, ma gestisci comunque multi-statement (ALTER SESSION; WITH/SELECT; ecc.)
                with engine.connect() as conn:
                    # Applica LIMIT solo se è stato esplicitamente fornito un valore numerico
                    if request.limit is not None and request.limit > 0:
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

                    # Suddividi per ';' ed esegui ogni statement separatamente, restituendo l'ultimo SELECT
                    last_select_result: Optional[QueryExecutionResult] = None
                    step_sql_normalized = sql_to_execute.strip()
                    statements = [s.strip() for s in re.split(r";\s*(?=\n|$)|;", step_sql_normalized) if s.strip()]
                    for stmt in statements:
                        stmt = stmt.rstrip().rstrip(';').strip()
                        if not stmt:
                            continue
                        # Rimuovi commenti prima del check SELECT
                        stmt_no_comments = re.sub(r'--[^\n]*', '', stmt)
                        stmt_no_comments = re.sub(r'/\*.*?\*/', '', stmt_no_comments, flags=re.DOTALL)
                        stmt_no_comments = stmt_no_comments.strip()
                        is_select = stmt_no_comments.lower().startswith("select") or stmt_no_comments.lower().startswith("with")
                        try:
                            result = conn.execute(text(stmt))
                            # Per Oracle, commit dopo DML/DDL
                            if db_type == "oracle" and not is_select:
                                try:
                                    conn.commit()
                                except Exception:
                                    pass
                        except Exception as e:
                            execution_time = (time.time() - start_time) * 1000
                            err_msg = f"Statement execute failed: {stmt} - Error: {str(e)}"
                            logger.error(err_msg)
                            # Diagnostica
                            try:
                                stmt_preview = stmt[:100].replace('\n', ' ')
                                diag_file = tmp_dir / "tmp_diagnostics.txt"
                                with open(diag_file, 'a', encoding='utf-8') as df:
                                    df.write(f"STATEMENT_EXECUTE_FAILED | {stmt_preview} | {str(e)}\n")
                            except Exception:
                                pass
                            return QueryExecutionResult(
                                query_filename=request.query_filename,
                                connection_name=request.connection_name,
                                success=False,
                                execution_time_ms=execution_time,
                                row_count=0,
                                error_message=err_msg,
                                parameters_used=request.parameters
                            )
                        if is_select:
                            try:
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
                                last_select_result = QueryExecutionResult(
                                    query_filename=request.query_filename,
                                    connection_name=request.connection_name,
                                    success=True,
                                    execution_time_ms=execution_time,
                                    row_count=len(data),
                                    column_names=column_names,
                                    data=data,
                                    parameters_used=request.parameters
                                )
                            except Exception as e:
                                execution_time = (time.time() - start_time) * 1000
                                stmt_preview = stmt[:100].replace('\n', ' ')
                                logger.error(f"Statement fetch failed: {stmt_preview} - Error: {str(e)}")
                                try:
                                    diag_file = tmp_dir / "tmp_diagnostics.txt"
                                    with open(diag_file, 'a', encoding='utf-8') as df:
                                        df.write(f"STATEMENT_FETCH_FAILED | {stmt_preview} | {str(e)}\n")
                                except Exception:
                                    pass
                                return QueryExecutionResult(
                                    query_filename=request.query_filename,
                                    connection_name=request.connection_name,
                                    success=False,
                                    execution_time_ms=execution_time,
                                    row_count=0,
                                    error_message=f"Statement fetch failed: {str(e)}",
                                    parameters_used=request.parameters
                                )

                    # Se esiste un risultato SELECT, restituiscilo; altrimenti OK senza righe
                    if last_select_result:
                        logger.info(f"Query {request.query_filename} eseguita con successo: {last_select_result.row_count} righe")
                        return last_select_result
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
            else:
                # Multi-step
                last_result = None
                with engine.connect() as conn:
                    for step in steps:
                        original_step_sql = step["sql"]
                        sql_to_execute = original_step_sql
                        # Salva versione raw prima di qualsiasi sostituzione per diagnosi
                        try:
                            tmp_dir = Path(self.settings.query_dir) / "tmp"
                            tmp_dir.mkdir(parents=True, exist_ok=True)
                            raw_file = tmp_dir / f"tmp_step{step['number']}_raw.txt"
                            with open(raw_file, "w", encoding="utf-8") as f_raw:
                                f_raw.write(original_step_sql)
                        except Exception as e:
                            logger.error(f"Impossibile salvare raw step {step['number']}: {e}")
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
                            # Log transformation diff if changed
                            if original_step_sql != sql_to_execute:
                                try:
                                    raw_preview = original_step_sql[:60].replace('\n', ' ')
                                    final_preview = sql_to_execute[:60].replace('\n', ' ')
                                    logger.debug(f"[Diag] Step {step['number']} transformed. Raw starts with: '{raw_preview}' Final starts with: '{final_preview}'")
                                except Exception as log_e:
                                    logger.debug(f"[Diag] Step {step['number']} transformed (preview unavail): {log_e}")
                        except Exception as e:
                            logger.error(f"Impossibile salvare la query in tmp_step{step['number']}.txt: {e}")
                        # Execute each statement inside the step separately.
                        # Some DB drivers (and cx_Oracle) don't accept multi-statement strings,
                        # so split on semicolons and run statements one by one.
                        step_sql_normalized = sql_to_execute.strip()
                        # Split statements by semicolon. Keep simple split — we'll strip empty pieces.
                        statements = [s.strip() for s in re.split(r";\s*(?=\n|$)|;", step_sql_normalized) if s.strip()]
                        for stmt in statements:
                            # remove any trailing semicolon leftovers
                            stmt = stmt.rstrip().rstrip(';').strip()
                            if not stmt:
                                continue
                            # Rimuovi commenti prima del check SELECT
                            stmt_no_comments = re.sub(r'--[^\n]*', '', stmt)
                            stmt_no_comments = re.sub(r'/\*.*?\*/', '', stmt_no_comments, flags=re.DOTALL)
                            stmt_no_comments = stmt_no_comments.strip()
                            is_select = stmt_no_comments.lower().startswith("select") or stmt_no_comments.lower().startswith("with")
                            # Advanced diagnostics: measure execute and fetch times separately
                            exec_time_ms = None
                            fetch_time_ms = None
                            fetch_error = None
                            try:
                                # Execute the statement as-is (no runtime hint stripping)
                                stmt_to_execute = stmt
                                t_exec_start = time.time()
                                result = conn.execute(text(stmt_to_execute))
                                exec_time_ms = (time.time() - t_exec_start) * 1000
                                # For Oracle, commit after DML/DDL statements
                                if db_type == "oracle" and not is_select:
                                    try:
                                        conn.commit()
                                    except Exception:
                                        pass
                            except Exception as e:
                                execution_time = (time.time() - start_time) * 1000
                                err_msg = f"Statement execute failed: {stmt} - Error: {str(e)}"
                                logger.error(err_msg)
                                # Save per-step diagnostics file with statement-level failure
                                try:
                                    stmt_preview = stmt[:100].replace('\n', ' ')
                                    diag_file = tmp_dir / f"tmp_step{step['number']}_diagnostics.txt"
                                    with open(diag_file, 'a', encoding='utf-8') as df:
                                        df.write(f"STATEMENT_EXECUTE_FAILED | {stmt_preview} | {str(e)}\n")
                                except Exception:
                                    pass
                                return QueryExecutionResult(
                                    query_filename=request.query_filename,
                                    connection_name=request.connection_name,
                                    success=False,
                                    execution_time_ms=execution_time,
                                    row_count=0,
                                    error_message=err_msg,
                                    parameters_used=request.parameters
                                )
                            if is_select:
                                try:
                                    t_fetch_start = time.time()
                                    rows = result.fetchall()
                                    fetch_time_ms = (time.time() - t_fetch_start) * 1000
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
                                except Exception as e:
                                    fetch_error = str(e)
                                    execution_time = (time.time() - start_time) * 1000
                                    stmt_preview = stmt[:100].replace('\n', ' ')
                                    logger.error(f"Statement fetch failed: {stmt_preview} - Error: {fetch_error}")
                                    # Append diagnostic info
                                    try:
                                        diag_file = tmp_dir / f"tmp_step{step['number']}_diagnostics.txt"
                                        with open(diag_file, 'a', encoding='utf-8') as df:
                                            df.write(f"STATEMENT_FETCH_FAILED | {stmt_preview} | {fetch_error}\n")
                                    except Exception:
                                        pass
                                    return QueryExecutionResult(
                                        query_filename=request.query_filename,
                                        connection_name=request.connection_name,
                                        success=False,
                                        execution_time_ms=execution_time,
                                        row_count=0,
                                        error_message=f"Statement fetch failed: {fetch_error}",
                                        parameters_used=request.parameters
                                    )
                            else:
                                # Non-select statements: log exec time in diagnostics file
                                try:
                                    stmt_preview = stmt[:100].replace('\n', ' ')
                                    diag_file = tmp_dir / f"tmp_step{step['number']}_diagnostics.txt"
                                    with open(diag_file, 'a', encoding='utf-8') as df:
                                        df.write(f"STATEMENT_EXECUTED | {stmt_preview} | exec_ms={exec_time_ms}\n")
                                except Exception:
                                    pass
                        # --- Diagnostic checks after executing all statements in the step ---
                        try:
                            # If this step references the temporary table, collect diagnostics
                            step_upper = sql_to_execute.upper() if isinstance(sql_to_execute, str) else ''
                            if 'APPO_BARCODE_NO_EMF' in step_upper:
                                diagnostics = []
                                try:
                                    res_user = conn.execute(text("SELECT USER FROM DUAL"))
                                    user = res_user.fetchone()[0] if res_user is not None else None
                                    diagnostics.append(f"SESSION_USER={user}")
                                except Exception as e:
                                    diagnostics.append(f"SESSION_USER_ERROR={str(e)}")
                                try:
                                    res_schema = conn.execute(text("SELECT SYS_CONTEXT('USERENV','CURRENT_SCHEMA') FROM DUAL"))
                                    current_schema = res_schema.fetchone()[0] if res_schema is not None else None
                                    diagnostics.append(f"CURRENT_SCHEMA={current_schema}")
                                except Exception:
                                    diagnostics.append("CURRENT_SCHEMA=UNAVAILABLE")
                                # Try a COUNT on the target table to check persistence
                                try:
                                    cnt_res = conn.execute(text("SELECT COUNT(*) FROM starown.APPO_BARCODE_NO_EMF"))
                                    cnt = cnt_res.fetchone()[0]
                                    diagnostics.append(f"COUNT_starown.APPO_BARCODE_NO_EMF={cnt}")
                                except Exception as e:
                                    diagnostics.append(f"COUNT_ERROR={str(e)}")

                                # Save diagnostics to tmp file
                                try:
                                    diag_file = tmp_dir / f"tmp_step{step['number']}_diagnostics.txt"
                                    with open(diag_file, 'w', encoding='utf-8') as df:
                                        for line in diagnostics:
                                            df.write(line + '\n')
                                    logger.debug(f"[Diag] Wrote diagnostics for step {step['number']}: {'; '.join(diagnostics)}")
                                except Exception as e:
                                    logger.error(f"Impossibile salvare diagnostica per step {step['number']}: {e}")
                        except Exception as e:
                            logger.error(f"Errore durante diagnostica step {step['number']}: {e}")
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
                # Controlla se è un parametro lista (nome contiene LIST o BARCODES)
                if param_name and any(kw in param_name.upper() for kw in ['LIST', 'BARCODES', 'CODES', 'IDS']):
                    param_values[param_name] = self._format_list_parameter(str(param_value) if param_value is not None else "")
                else:
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
    
    def _format_list_parameter(self, value: str) -> str:
        """Formatta un parametro lista per SQL IN clause.
        Supporta input nei formati: 
        - 123,456,789 
        - '123','456','789'
        - 123\n456\n789
        Restituisce: '123','456','789'
        """
        try:
            if not value or not value.strip():
                return "''"
            
            # Rimuovi spazi bianchi iniziali/finali
            value = value.strip()
            
            # Step 1: Se già formattato con apici, rimuovili per normalizzare
            # Pattern: rimuove apici singoli e doppi
            value = re.sub(r"['\"]", '', value)
            
            # Step 2: Split per vari separatori (virgola, newline, spazi multipli)
            # Supporta CR+LF, LF, virgola, spazi
            items = re.split(r'[,\n\r\s]+', value)
            
            # Step 3: Filtra elementi vuoti e rimuovi spazi
            items = [item.strip() for item in items if item.strip()]
            
            # Step 4: Valida lunghezza massima
            if len(items) > 1000:
                logger.warning(f"Lista parametri troppo lunga: {len(items)} elementi (max 1000)")
                items = items[:1000]
            
            # Step 5: Formatta come 'val1','val2','val3'
            # Escape apici interni raddoppiandoli (SQL standard)
            formatted_items = [f"'{item.replace(chr(39), chr(39)+chr(39))}'" for item in items]
            
            result = ','.join(formatted_items)
            logger.debug(f"Formatted list parameter: {len(items)} items")
            return result
            
        except Exception as e:
            logger.error(f"Errore nella formattazione del parametro lista: {e}")
            # Fallback sicuro
            return "''"
    
    def _add_limit_clause(self, sql: str, limit: int, connection_name: str) -> str:
        """Aggiunge una clausola LIMIT/TOP ai DB che la supportano.
        Se `limit` è None o <= 0 la query non viene modificata.
        Per Oracle non viene aggiunta alcuna clausola.
        """
        try:
            connection = self.connection_service.get_connection(connection_name)
            if not connection:
                return sql
            db_type = connection.db_type.lower()
            # Rimuove eventuali terminatori di statement (;) alla fine per evitare
            # di generare "...; LIMIT 1000" che risulta sintatticamente non valido.
            # Non modifica la semantica della query.
            if isinstance(sql, str):
                s = sql.rstrip()
                while s.endswith(';'):
                    s = s[:-1].rstrip()
                sql = s
            sql_upper = sql.upper()
            # Se il db è Oracle, NON aggiungere nulla
            if db_type == "oracle":
                return sql
            # Per gli altri db mantieni la logica precedente
            if any(keyword in sql_upper for keyword in ['LIMIT', 'ROWNUM', 'TOP', 'FETCH']):
                return sql  # Query ha già limitazioni
            # Se per qualche motivo limit non è un numero positivo, non modificare la query
            try:
                if limit is None or int(limit) <= 0:
                    return sql
            except Exception:
                return sql

            if db_type in ["postgresql", "mysql"]:
                # Applica il limite in modo sicuro incapsulando la query in una subselect
                # per evitare qualsiasi interferenza con stringhe o trailing content.
                return f"SELECT * FROM ({sql}) AS _lim LIMIT {int(limit)}"
            elif db_type == "sqlserver":
                return re.sub(r'\bSELECT\b', f'SELECT TOP {int(limit)}', sql, count=1, flags=re.IGNORECASE)
            else:
                return f"{sql} LIMIT {int(limit)}"
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
