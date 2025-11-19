"""Script di utilità per eseguire una batteria di test di regressione sulle query SQL.

Esegue tutte le query `.sql` presenti nella directory `Query/` usando la connessione
di default definita in `connections.json`. Salva i risultati in `tools/regression_results.json`.
"""
import json
from pathlib import Path
from datetime import datetime

from app.core.config import get_settings, get_connections_config
from app.services.query_service import QueryService
from app.services.connection_service import ConnectionService
from app.models.queries import QueryExecutionRequest


def main():
    settings = get_settings()
    qs = QueryService()
    query_dir = Path(settings.query_dir)
    out_file = Path(__file__).parent / "regression_results.json"

    if not query_dir.exists():
        print(f"Directory query non trovata: {query_dir}")
        return

    sql_files = sorted([p.name for p in query_dir.glob("*.sql")])
    if not sql_files:
        print("Nessun file .sql trovato in Query/")
        return

    # Load connections config and available connection names
    connections_config = get_connections_config()
    available = [c.name for c in connections_config.connections]
    preferred = connections_config.default_connection if hasattr(connections_config, 'default_connection') else None
    if preferred and preferred in available:
        default_connection = preferred
    else:
        default_connection = available[0] if available else None
        if preferred and preferred not in available:
            print(f"Preferred default connection '{preferred}' not found in connections.json. Using '{default_connection}' for regression tests.")

    # Only run queries containing 'TEST' in the filename (case-insensitive)
    sql_files = [f for f in sql_files if 'TEST' in f.upper()]

    results = []
    for fname in sql_files:
        # Determine target connection from filename by matching tokens from available connection names.
        # Strategy: for each connection name, extract meaningful token(s) (parts after first dash) and
        # check if they appear in the SQL filename (case-insensitive). If none match, use default_connection.
        target_conn = default_connection
        fname_upper = fname.upper()
        matched = None
        for conn_name in available:
            # Example conn_name: 'A00-CDG-Collaudo' -> tokens ['A00', 'CDG', 'Collaudo']
            parts = conn_name.upper().split('-')
            # consider all parts except the first (which is environment code)
            for part in parts[1:]:
                if part and part in fname_upper:
                    matched = conn_name
                    break
            if matched:
                break

        if matched:
            target_conn = matched

        print(f"Running: {fname}  -> connection: {target_conn}")
        req = QueryExecutionRequest(
            query_filename=fname,
            connection_name=target_conn,
            parameters={},
            limit=None
        )
        try:
            res = qs.execute_query(req)
            entry = {
                'query': fname,
                'success': bool(res.success),
                'row_count': int(res.row_count) if res.row_count is not None else None,
                'execution_time_ms': float(res.execution_time_ms) if res.execution_time_ms is not None else None,
                'error_message': res.error_message,
                'columns': res.column_names[:10] if res.column_names else [],
                'sample_rows': (res.data[:3] if res.data else []),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        except Exception as e:
            entry = {
                'query': fname,
                'success': False,
                'row_count': None,
                'execution_time_ms': None,
                'error_message': str(e),
                'columns': [],
                'sample_rows': [],
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        results.append(entry)
        print(f" -> {fname}: success={entry['success']} rows={entry['row_count']} time_ms={entry['execution_time_ms']}")

    # Save results to file
    try:
        with open(out_file, 'w', encoding='utf-8') as f:
            # Use default=str to serialize dates and other non-JSON types safely
            json.dump({'generated_at': datetime.utcnow().isoformat() + 'Z', 'results': results}, f, ensure_ascii=False, indent=2, default=str)
        print(f"Saved results to {out_file}")
    except Exception as e:
        print(f"Impossibile salvare i risultati: {e}")


if __name__ == '__main__':
    main()
