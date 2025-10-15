# Changelog

Tutte le modifiche importanti a questo progetto saranno documentate in questo file.

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

## Template per future versioni

## [Unreleased]
### Added
- Tests automatici per parsing e comportamento dello scheduler (skip/esecuzione basati su end_date).

### Fixed
- Scheduler: ora viene rispettata la `end_date`. Il servizio verifica la data di fine prima di eseguire la query e salta job scaduti.

### Changed
- Aggiunto `_today()` helper in `app/services/scheduler_service.py` per test deterministici.
- Parsing `end_date` più robusto (supporto a YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, YYYY/MM/DD e oggetti datetime/date).
- Spostata la verifica `end_date` prima dell'esecuzione della query per evitare esecuzioni non necessarie.

### Added
- Dashboard utente per gestione schedulazioni e monitoring (`/dashboard`)
- API CRUD per schedulazioni (`GET/POST/PUT/DELETE /api/scheduler/scheduling`)
- Test automatici CRUD schedulazioni (`test_scheduler_api_crud.py`)
- Dashboard hardware: Health Check mostra spazio disco, RAM e CPU
- Dipendenza psutil per info hardware
- Uniformato il layout dashboard.
- Gestione script SQL multistep: esecuzione sequenziale di step con parametri e log dedicati
- Gestione asincrona e concorrente dei job schedulati tramite APScheduler AsyncIOExecutor

### Fixed
- Correzione endpoint PUT per modifica schedulazione
- Sostituzione automatica dei parametri opzionali non valorizzati con stringa vuota
- Fix errori ORA-00933 su Oracle per step DML
- Sincronizzazione tra job schedulati/attivi e dashboard
- Risolto problema di job saltati quando una schedulazione è in corso
- Fix selezione query corretta nel form di modifica schedulazione

## [1.0.1] - 2025-08-14
### Fixed
- Export Excel ora funzionante: SheetJS caricata localmente, risolto errore CORB
- Migliorato contrasto righe griglia risultati
- Header tabella risultati colorato blu
- Visualizzazione query: solo gruppo+nome, ordinamento alfabetico, refresh su stato connesso
- Eliminato file base.html non utilizzato
