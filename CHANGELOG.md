# Changelog

Tutte le modifiche importanti a questo progetto saranno documentate in questo file.

## [Unreleased] - 2025-12-04

### Changed
- **Export behavior:** Client-side Excel export removed; UI now requests exports from the server API so files are generated server-side (matches scheduler output and reduces client-side memory/size issues).

### Removed
- Removed local SheetJS bundle `app/static/js/xlsx.full.min.js` and related client-side export fallback. Clients must use server-side export endpoint (`POST /api/queries/export`).

### Notes
- Developers: update local environment if needed to run exports (DB connectivity and credentials required).


Il formato è basato su [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-08-12

### Aggiunto
- ✨ Interfaccia web principale con Tailwind CSS
- 🗄️ Supporto multi-database (Oracle, PostgreSQL, SQL Server)
- 🔍 Sistema di parsing delle query SQL con parametri
- ⚙️ Gestione configurazione tramite `connections.json` e `.env`
- 📊 API REST completa con documentazione OpenAPI
- 🎯 Form dinamico per inserimento parametri query
- 📈 Visualizzazione risultati con filtri e ordinamento
- 🔧 Sistema di logging strutturato con Loguru
- 🏥 Health check e monitoring sistema
- 📁 Struttura progetto modulare e scalabile

### Implementato
- **Core Framework**: FastAPI con gestione lifecycle applicazione
- **Database Management**: ConnectionService con pool connessioni SQLAlchemy
- **Query Processing**: QueryService con parsing parametri Oracle define
- **Frontend**: SPA JavaScript con interazioni AJAX
- **Configuration**: Sistema configurazione centralizzato con Pydantic
- **Logging**: Log rotazione e compressione automatica
- **Error Handling**: Gestione errori completa con try/catch

### API Endpoints
- `GET /` - Homepage interfaccia web
- `GET /api/connections/` - Lista connessioni configurate
- `POST /api/connections/test` - Test connettività database
- `POST /api/connections/switch` - Cambio connessione attiva
- `GET /api/queries/` - Lista query SQL disponibili
- `GET /api/queries/{filename}` - Dettagli query specifica
- `POST /api/queries/execute` - Esecuzione query parametrizzata
- `GET /api/monitoring/health` - Health check sistema
- `GET /api/monitoring/stats` - Statistiche sistema

### Configurazione
- Supporto per 5 connessioni database pre-configurate
- Gestione credenziali sicura tramite variabili d'ambiente
- Configurazione pool connessioni ottimizzata per tipo database
- Sistema di routing API modulare

### Frontend Features
- Interfaccia responsive con design professionale
- Selezione connessione database con indicatore stato
- Lista query con descrizioni e conteggio parametri
- Form parametri generato dinamicamente
- Tabella risultati con filtri multi-colonna case-insensitive
- Ordinamento colonne tramite click header
- Barra stato con metriche esecuzione
- Overlay loading e gestione errori user-friendly

### In Sviluppo
- 🔄 Sistema scheduling automatico
- 📤 Export Excel/CSV
- 📧 Sistema notifiche
- 🧪 Test suite completa

### Note Tecniche
- Python 3.11 con virtual environment
- FastAPI + Uvicorn per server ASGI
- SQLAlchemy 2.0 con driver nativi (oracledb, psycopg2-binary, pyodbc)
- Tailwind CSS 3.x per styling
- Font Awesome 6.4 per icone
- Loguru per logging avanzato
- Pydantic per validazione dati

### Requisiti Sistema
- Python 3.11+
- Oracle Instant Client (per connessioni Oracle)
- PostgreSQL client libraries (per connessioni PostgreSQL)
- ODBC Driver 18 for SQL Server (per connessioni SQL Server)
- Memoria RAM: minimo 2GB, consigliato 4GB
- Storage: 500MB per installazione base

### Configurazione Raccomandata
```bash
# .env
LOG_LEVEL=INFO
DEBUG=false
HOST=127.0.0.1
PORT=8000
EXPORT_RETENTION_DAYS=30
```

### Known Issues
- [ ] Export funzionalità non ancora implementata
- [ ] Scheduler in modalità stub
- [ ] Test suite incompleta
- [ ] Documentazione API da completare

### Breaking Changes
N/A - Versione iniziale

---

-## Template per future versions

### Fixed
- Sostituzione automatica dei parametri opzionali non valorizzati con stringa vuota
### Fixed
- Export Excel ora funzionante: SheetJS caricata localmente, risolto errore CORB
- Migliorato contrasto righe griglia risultati
- Header tabella risultati colorato blu
- Visualizzazione query: solo gruppo+nome, ordinamento alfabetico, refresh su stato connesso
- Eliminato file base.html non utilizzato

### 2025-11-10 -  Unreleased / Integration

### Changed
- Tutti gli asset frontend critici ora serviti localmente da `app/static` (Tailwind loader, Font Awesome CSS + webfonts, flatpickr, SheetJS/xlsx). Rimosse dipendenze CDN per migliorare l'affidabilità in ambienti offline/chiusi.
- `scheduler_dashboard.html`: allineata alla home; rimossi loader CDN, aggiunta modal grafica per conferma eliminazione schedulazioni (con supporto ESC per chiusura), fallback inline per icone Font Awesome che non venivano renderizzate.
- `app/main.py`: migliorata la configurazione di logging (timestamp nel formato dei log), aggiunta robustezza encoding per esecuzione come servizio Windows (tentativi di reconfigure stdout/`safe_print`), e aggiunti parametri CLI `--host` e `--port` per avvio parametrizzato.
- Aggiunti script operativi per Windows: `install_service.ps1` e `manage_service.ps1` (integrazione NSSM) per installare/gestire l'app come servizio di sistema.
- `README.md`: aggiunta sezione dettagliata per la distribuzione come servizio Windows (NSSM), comandi di gestione e istruzioni per l'avvio manuale con porta parametrizzata.

### Fixed
- Risolti problemi di caricamento dei webfonts (Content-Type/MIME) registrando i tipi appropriati e aggiornando gli `@font-face` per puntare ai percorsi locali.
- Risolti errori Unicode/Encoding quando l'app veniva eseguita come servizio su Windows (UnicodeEncodeError), garantendo che i messaggi di log non provochino crash del servizio.

### Test
- Eseguita la suite di test automatizzata: `pytest` -> 55 passed, 0 failed.

### VCS
- Raccolte le modifiche locali in branch `feature/unstaged-changes-20251110` e push verso remote (branch creato su origin).

## [2025-11-19] - Multistep & Regression

### Added
- `tools/run_query_regression.py`: nuovo script per eseguire una batteria di test sulle query SQL (supporta filtro per nome e report JSON).

### Changed
- `tools/run_query_regression.py`: ora seleziona la `default_connection` da `connections.json` e mappa automaticamente la connection target dai token presenti nel nome file (es. `CDG`, `BOSC`, `TT2_UFFICIO`).
- `app/services/query_service.py`: rimosso il comportamento temporaneo che a runtime eliminava i hint Oracle `PARALLEL`; ripristinata l'esecuzione delle statement così come sono nei file SQL.
- `README.md`: aggiunta sezione **Nomenclatura dei file query** che descrive la convenzione di naming richiesta per le query e le regole di mapping alla connessione.

### Fixed
- Corrette e migliorate le diagnostiche per gli script SQL multistep: salvataggio di `tmp_stepN_raw.txt`, `tmp_stepN.txt` e `tmp_stepN_diagnostics.txt` per ogni step, con session user/schema e conteggio righe per verifica post-DML.

### Notes
- Le modifiche introdotte servono a stabilizzare l'esecuzione automatica delle query multistep e a permettere esecuzioni di regressione selettive basate sulla nomenclatura dei file.

