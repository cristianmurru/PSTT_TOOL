"""
API endpoints per la gestione e l'esecuzione delle query
"""
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Request
from loguru import logger

from app.services.query_service import QueryService
from app.models.queries import (
    QueryListResponse,
    QueryInfo,
    QueryExecutionRequest,
    QueryExecutionResult
)
from app.models.queries import ExportRequest
import io
import pandas as pd
from datetime import datetime
from app.core.config import get_settings


class UpdateQueryPayload(dict):
    pass


router = APIRouter()


def get_query_service():
    """Dependency injection per QueryService"""
    return QueryService()


@router.get("/", response_model=QueryListResponse, summary="Lista query")
async def get_queries(
    query_service: QueryService = Depends(get_query_service)
):
    """
    Ottiene la lista di tutte le query SQL disponibili
    """
    try:
        queries = query_service.get_queries()
        
        return QueryListResponse(
            queries=queries,
            total_count=len(queries)
        )
        
    except Exception as e:
        logger.error(f"Errore nel recupero delle query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nel recupero delle query"
        )


@router.get("/{filename}", response_model=QueryInfo, summary="Dettagli query")
async def get_query(
    filename: str,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Ottiene i dettagli di una query specifica
    """
    try:
        query_info = query_service.get_query(filename)
        
        if not query_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query non trovata: {filename}"
            )
        
        return query_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nel recupero della query {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nel recupero della query"
        )


@router.post("/execute", response_model=QueryExecutionResult, summary="Esegui query")
async def execute_query(
    request: QueryExecutionRequest,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Esegue una query con i parametri specificati
    """
    try:
        logger.info(f"Esecuzione query {request.query_filename} su connessione {request.connection_name}")
        
        result = query_service.execute_query(request)
        
        if not result.success:
            # Restituisce l'errore ma non solleva un'eccezione HTTP
            # in modo che il client possa gestire il messaggio di errore
            logger.warning(f"Query {request.query_filename} fallita: {result.error_message}")
        
        return result
        
    except Exception as e:
        logger.error(f"Errore nell'esecuzione della query {request.query_filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nell'esecuzione della query"
        )


@router.put("/{filename}/update", summary="Aggiorna contenuto query")
async def update_query(filename: str, payload: Dict[str, Any], query_service: QueryService = Depends(get_query_service)):
    try:
        # Block edits in production environment
        try:
            settings = get_settings()
            env = (getattr(settings, 'app_environment', '') or '').lower()
            if 'produzione' in env or 'production' in env:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Modifica disabilitata in ambiente di Produzione")
        except HTTPException:
            raise
        except Exception:
            pass
        new_sql = str(payload.get('sql_content', ''))
        if not new_sql:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sql_content mancante")
        ok = query_service.save_query(filename, new_sql)
        if not ok:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Salvataggio fallito")
        info = query_service.get_query(filename)
        return {"success": True, "query": info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore update query {filename}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno aggiornamento query")


@router.post("/{filename}/format", summary="Formatta SQL (visualizzazione)")
async def format_query(filename: str, payload: Dict[str, Any], query_service: QueryService = Depends(get_query_service)):
    try:
        sql = str(payload.get('sql_content', ''))
        formatted = query_service.format_sql_basic(sql)
        return {"formatted": formatted}
    except Exception as e:
        logger.error(f"Errore format SQL {filename}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno formatting")


@router.post("/{filename}/suggest", summary="Suggerimenti ottimizzazione SQL")
async def suggest_query(filename: str, payload: Dict[str, Any], query_service: QueryService = Depends(get_query_service)):
    try:
        sql = str(payload.get('sql_content', ''))
        conn = str(payload.get('connection_name', ''))
        suggestions = query_service.suggest_optimizations(sql, conn)
        # Include lint issues for better guidance
        issues = query_service.lint_sql(sql, conn)
        return {"suggestions": suggestions, "issues": issues}
    except Exception as e:
        logger.error(f"Errore suggest SQL {filename}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno suggerimenti")


@router.post("/{filename}/lint", summary="Verifica sintattica SQL")
async def lint_query(filename: str, payload: Dict[str, Any], query_service: QueryService = Depends(get_query_service)):
    try:
        sql = str(payload.get('sql_content', ''))
        conn = str(payload.get('connection_name', ''))
        issues = query_service.lint_sql(sql, conn)
        return {"issues": issues}
    except Exception as e:
        logger.error(f"Errore lint SQL {filename}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno lint")


@router.post("/export", summary="Export query results (server-side)")
async def export_query(
    request: ExportRequest,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Genera e restituisce il file di export (CSV o XLSX) usando pandas sul server.
    """
    try:
        # Esegui la query senza limit per ottenere il dataset completo
        exec_req = QueryExecutionRequest(
            query_filename=request.query_filename,
            connection_name=request.connection_name,
            parameters=request.parameters,
            limit=None
        )
        result = query_service.execute_query(exec_req)
        if not result.success:
            logger.error(f"Export fallito: {result.error_message}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error_message or 'Errore esecuzione query')

        # Costruisci DataFrame pandas dal risultato
        try:
            # result.data is expected to be a list of dicts with column keys
            df = pd.DataFrame(result.data if result.data is not None else [])
            # Ensure columns order matches column_names if provided
            if getattr(result, 'column_names', None):
                cols = result.column_names
                # keep only existing columns in dataframe and in given order
                cols_existing = [c for c in cols if c in df.columns]
                df = df[cols_existing] if cols_existing else df
        except Exception as e:
            logger.exception(f"Errore costruzione DataFrame per export: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Errore trasformazione risultati per export')

        # Usa la stessa logica del SchedulerService: scrive su file in Export/_tmp poi sposta il file
        from app.core.config import get_settings
        from pathlib import Path
        import time
        settings = get_settings()
        export_dir = Path(settings.export_dir)
        tmp_dir = export_dir / '_tmp'
        tmp_dir.mkdir(parents=True, exist_ok=True)
        # filename base
        base_name = request.query_filename.replace('.sql', '')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')

        if request.export_format and request.export_format.lower() == 'csv':
            # scrivi CSV su file temporaneo e poi sposta
            temp_path = tmp_dir / f"{base_name}_{timestamp}.csv.tmp.csv"
            final_path = export_dir / f"{base_name}_{timestamp}.csv"
            csv_text = df.to_csv(index=False, sep=';', encoding='utf-8')
            logger.info(f"[EXPORT] START_WRITE temp={temp_path}")
            with open(temp_path, 'w', encoding='utf-8', newline='') as f:
                f.write(csv_text)
            size = temp_path.stat().st_size
            logger.info(f"[EXPORT] END_WRITE duration=0 size={size}B")
            size = temp_path.stat().st_size
            logger.info(f"[EXPORT] START_WRITE temp={temp_path}")
            logger.info(f"[EXPORT] END_WRITE duration=0 size={size}B")
            try:
                temp_path.replace(final_path)
                logger.info(f"[EXPORT] MOVE_OK {temp_path} -> {final_path}")
            except Exception:
                logger.exception("[EXPORT] Errore nel muovere il file csv temporaneo")

            # stream file
            media_type = 'text/csv'
            filename = final_path.name
            headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
            return StreamingResponse(open(final_path, 'rb'), media_type=media_type, headers=headers)
        else:
            temp_path = tmp_dir / f"{base_name}_{timestamp}.xlsx.tmp.xlsx"
            final_path = export_dir / f"{base_name}_{timestamp}.xlsx"
            logger.info(f"[EXPORT] START_WRITE temp={temp_path}")
            try:
                # scrittura su file come fa lo scheduler
                df.to_excel(temp_path, index=False)
                duration = 0.0
                size = temp_path.stat().st_size
                logger.info(f"[EXPORT] END_WRITE duration={duration}s size={size}B")
                try:
                    temp_path.replace(final_path)
                    logger.info(f"[EXPORT] MOVE_OK {temp_path} -> {final_path}")
                except Exception:
                    logger.exception("[EXPORT] Errore nel muovere il file temporaneo xlsx")
            except Exception as e:
                logger.exception(f"Errore generazione file xlsx: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Errore generazione file xlsx')

            media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = final_path.name
            headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
            return StreamingResponse(open(final_path, 'rb'), media_type=media_type, headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Errore nell'export della query {request.query_filename}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Errore interno export')


@router.post("/validate", summary="Valida parametri query")
async def validate_query_parameters(
    request: Request,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Valida i parametri per una query specifica
    """
    try:
        filename = None
        parameters = {}
        try:
            body = await request.json()
        except Exception:
            body = None

        if body:
            filename = body.get('filename')
            parameters = body.get('parameters', {})
        else:
            # fallback to query params (tests use params)
            qs = request.query_params
            filename = qs.get('filename')
            params_raw = qs.get('parameters')
            if params_raw:
                # parameters could be passed as JSON string or empty
                try:
                    import json as _json
                    parameters = _json.loads(params_raw)
                except Exception:
                    parameters = {}
        query_info = query_service.get_query(filename)

        if not query_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query non trovata: {filename}"
            )
        
        # Valida parametri obbligatori
        missing_params = []
        invalid_params = []
        warnings = []
        
        for param in query_info.parameters:
            if param.required and param.name not in parameters:
                if not param.default_value:
                    missing_params.append(param.name)
            
            # Valida tipo se il parametro è fornito
            if param.name in parameters:
                value = parameters[param.name]
                if value is not None and value != "":
                    # Qui potresti aggiungere validazioni specifiche per tipo
                    # Per ora solo controlli base
                    if param.parameter_type == "integer":
                        try:
                            int(value)
                        except (ValueError, TypeError):
                            invalid_params.append(f"{param.name} deve essere un numero intero")
                    elif param.parameter_type == "float":
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            invalid_params.append(f"{param.name} deve essere un numero")
        
        # Controlla parametri non riconosciuti
        recognized_params = {param.name for param in query_info.parameters}
        unrecognized = [name for name in parameters.keys() if name not in recognized_params]
        if unrecognized:
            warnings.append(f"Parametri non riconosciuti: {', '.join(unrecognized)}")
        
        validation_result = {
            "valid": len(missing_params) == 0 and len(invalid_params) == 0,
            "missing_parameters": missing_params,
            "invalid_parameters": invalid_params,
            "warnings": warnings
        }
        
        return validation_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nella validazione parametri per {filename or '<unknown>'}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nella validazione"
        )


@router.get("/{filename}/preview", summary="Anteprima query")
async def preview_query(
    filename: str,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Mostra un'anteprima della query con i parametri sostituiti
    """
    try:
        query_info = query_service.get_query(filename)
        
        if not query_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query non trovata: {filename}"
            )
        
        # Per ora mostra solo la query originale senza sostituzione parametri
        # I parametri verranno passati dal frontend via POST se necessario
        return {
            "filename": filename,
            "original_sql": query_info.sql_content,
            "processed_sql": query_info.sql_content,
            "parameters_used": {}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nell'anteprima della query {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nell'anteprima"
        )


@router.get("/stats/summary", summary="Statistiche query")
async def get_query_statistics(
    query_service: QueryService = Depends(get_query_service)
):
    """
    Ottiene statistiche generali sulle query disponibili
    """
    try:
        queries = query_service.get_queries()
        
        if not queries:
            return {
                "total_queries": 0,
                "total_size_bytes": 0,
                "parameters_stats": {},
                "file_types": {}
            }
        
        # Calcola statistiche
        total_size = sum(q.size_bytes for q in queries)
        total_params = sum(len(q.parameters) for q in queries)
        
        # Statistiche parametri
        param_types = {}
        required_params = 0
        optional_params = 0
        
        for query in queries:
            for param in query.parameters:
                param_type = param.parameter_type
                param_types[param_type] = param_types.get(param_type, 0) + 1
                
                if param.required:
                    required_params += 1
                else:
                    optional_params += 1
        
        # Raggruppa per prefisso (es: BOSC-NXV, CDG-NXV, etc.)
        prefixes = {}
        for query in queries:
            if '-' in query.filename:
                prefix = query.filename.split('-')[0]
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
        
        return {
            "total_queries": len(queries),
            "total_size_bytes": total_size,
            "total_parameters": total_params,
            "parameters_stats": {
                "by_type": param_types,
                "required": required_params,
                "optional": optional_params
            },
            "queries_by_prefix": prefixes,
            "average_parameters_per_query": round(total_params / len(queries), 2) if queries else 0
        }
        
    except Exception as e:
        logger.error(f"Errore nel calcolo delle statistiche: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nel calcolo delle statistiche"
        )


def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

def unprocessable_handler(request: Request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

def setup_error_handlers(app):
    app.add_exception_handler(404, not_found_handler)
    app.add_exception_handler(422, unprocessable_handler)
