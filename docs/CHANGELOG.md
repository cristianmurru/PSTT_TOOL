# Changelog

Tutte le modifiche importanti a questo progetto saranno documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - [2026-01-21] - Integrazione completa Kafka per pubblicazione messaggi su topic da schedulazioni

### Added - Kafka Integration (STEP 1-7/8)

#### STEP 1-2: Foundation & Service ✅
- 🚀 **Kafka Integration Foundation**
  - Dipendenze: `kafka-python-ng==2.2.2` e `aiokafka==0.10.0`
  - Modelli Pydantic completi (`app/models/kafka.py`): `KafkaConnectionConfig`, `KafkaProducerConfig`, `KafkaExportConfig`, `KafkaMetrics`, `BatchResult`, `KafkaHealthStatus`
  - 36 nuove variabili configurazione in `app/core/config.py`
  - Supporto multi-cluster Kafka in `connections.json`
  - Helper `get_kafka_config()` per caricamento configurazione
- 📡 **KafkaService Implementation** (`app/services/kafka_service.py`)
  - Connection management asincrona con security (PLAINTEXT/SSL/SASL)
  - Message publishing singolo con retry automatico
  - JSON serialization custom per `datetime`, `date`, `Decimal`
  - Health check con verifica connettività broker
  - Metrics tracking: latenza, throughput, success rate
  - Error handling completo per timeout/broker unavailable
  - Context manager per gestione automatica risorse

#### STEP 3: Batch Publishing & Performance ✅
- ⚡ **Batch Publishing Optimization**
  - `send_batch()`: Invio batch con chunking intelligente (default 100 msg/chunk)
  - Processing parallelo messaggi con `asyncio.to_thread`
  - Flush periodico buffer ogni 10 chunk
  - Auto-reconnect se producer disconnesso
  - Throughput verificato: >100 msg/sec con 1000 messaggi
  - `send_batch_with_retry()`: Retry automatico con backoff esponenziale
  - Success rate threshold configurabile (default 95%)
  - Backoff: 100ms → 200ms → 400ms (max 3 retry)

#### STEP 4: Scheduler Integration ✅
- 🔗 **Scheduler Kafka Export**
  - Estensione `SchedulingItem`: `SharingMode.KAFKA`, campi `kafka_topic`, `kafka_key_field`, `kafka_batch_size`, `kafka_include_metadata`
  - Metodo `_execute_kafka_export()` in `SchedulerService`
  - Pipeline: query → trasformazione → batch export Kafka
  - Metadata automatici: source_query, source_connection, export_timestamp, export_id
  - Tracking completo in `scheduler_history.json`: kafka_topic, kafka_messages_sent, kafka_messages_failed, kafka_duration_sec

#### STEP 5: API & Metrics ✅
- 📊 **Kafka API Endpoints** (`app/api/kafka.py`)
  - `POST /api/kafka/test`: Test connessione broker
  - `POST /api/kafka/send`: Invio messaggio singolo
  - `POST /api/kafka/batch`: Invio batch messaggi
  - `GET /api/kafka/metrics/summary`: Metriche globali aggregate
  - `GET /api/kafka/metrics/hourly`: Metriche ultime 24h
  - `GET /api/kafka/metrics/topics`: Breakdown per topic
  - `GET /api/kafka/health`: Health check producer Kafka
- 📈 **Metrics Service** (`app/services/kafka_metrics.py`)
  - Tracciamento temporale con granularità oraria
  - Aggregazione multi-dimensionale (topic, connection, total)
  - Export JSON persistente su disco
  - Reset metriche manuale e automatico

#### STEP 6: UI & Dashboard ✅
- 🎨 **Kafka Dashboard** (`app/frontend/kafka_dashboard.html`)
  - Overview metriche in tempo reale (last 24h)
  - Grafici throughput e latency con Chart.js
  - Breakdown per topic con tabelle interattive
  - Sezione test: invio messaggi singoli/batch da UI
  - Health status producer con indicatori visivi
- 🔧 **Scheduler UI Enhancement** (`app/frontend/scheduler_dashboard.html`)
  - Opzione "Kafka" in dropdown Condivisione
  - 4 campi specifici: kafka_topic, kafka_key_field, kafka_batch_size, kafka_include_metadata
  - Show/hide dinamico campi in base a modalità selezionata
  - Form submission con costruzione automatica `kafka_config` object

#### STEP 7: Documentation & Testing ✅
- 📚 **Comprehensive Documentation**
  - `docs/KAFKA_SETUP.md` (~400 righe): Setup guide, troubleshooting, performance tuning, security SSL/SASL, FAQ
  - `docs/KAFKA_RUNBOOK.md` (~600 righe): Operational procedures, emergency scenarios, health checks, escalation matrix
- 🛠️ **Benchmark Tool** (`tools/kafka_benchmark.py`)
  - 3 modalità test: single, batch, mixed load
  - Metriche latenza: avg, p50, p90, p99
  - Calcolo throughput (msg/sec)
  - Command-line interface con argparse
- ✅ **Test Coverage**
  - 111 test passed (pytest)
  - Coverage: 76% overall (kafka_service: 75%, metrics: 88%, api: 68%)
  - Test validazione modelli, service methods, API endpoints, scheduler integration

### Technical Details
- **Security**: PLAINTEXT/SSL/SASL_PLAINTEXT/SASL_SSL con meccanismi PLAIN/SCRAM
- **Performance**: Snappy compression, batching, idempotence, throughput >100 msg/sec
- **Reliability**: Retry automatico, backoff esponenziale, success rate monitoring 95%
- **Architecture**: Completamente asincrona (async/await), compatibile FastAPI
- **Multi-cluster**: Supporto connessioni multiple via `connections.json`
- **Zero Breaking Changes**: Tutte le funzionalità esistenti rimangono intatte

### Next Steps
- STEP 8: Deploy produzione e rollout graduale
  - Pre-deploy checklist (credentials, network, topics)
  - Deploy Phase 1: Infrastructure setup
  - Deploy Phase 2: Test in production (1 job, monitor 1 week)
  - Deploy Phase 3: Gradual rollout (20K+ msg/day)
  - Post-deploy monitoring e weekly reviews

---

## [1.0.4] - [2026-01-17] - Service restart reliability multi-strategy

### Fixed
- 🔧 **Service Restart Reliability in Production**
  - Implementata strategia multi-fallback per restart servizio
  - Strategia 1 (preferita): Comandi Windows nativi (`Stop-Service`/`Start-Service`) - funziona senza NSSM nel PATH
  - Strategia 2 (fallback): `nssm restart` se disponibile - gestione automatica da NSSM
  - Strategia 3 (ultimo resort): `nssm stop` + wait + `nssm start` - massimo controllo sulla sequenza
  - Risolve problemi di permessi/policy in ambienti enterprise

### Added
- ✨ **NSSM Availability Check** - Nuova funzione `_check_nssm_available()` per verificare presenza NSSM
- 📊 **Enhanced Restart Logging** - Log dettagliati per ogni strategia tentata per diagnostica

### Changed
- ♻️ **Restart Logic Resilience** - Logica restart più robusta con fallback progressivi
  - Non più dipendente da singola strategia che può fallire
  - Adattamento automatico all'ambiente (permessi, NSSM disponibilità, policy aziendali)

---

## [1.0.3] - [2026-01-15] - Fix critico restart servizio e configurazione NSSM

### Fixed
- 🔧 **CRITICAL: Service Restart Failure**
  - Risolto problema restart da UI in ambienti dove NSSM non è nel PATH
  - Rimossa dipendenza da NSSM per restart: usa solo comandi Windows nativi (`Stop-Service`/`Start-Service`)
  - Script PowerShell inline con retry logic (5 tentativi) per gestire avvii falliti
  - Esecuzione in background con `CREATE_NO_WINDOW` per evitare finestre popup
  - Eliminata chiamata `_exit_process()` in modalità service per prevenire loop infiniti
- 🔧 **NSSM Configuration**
  - Aggiornata configurazione service in `install_service.ps1`
  - Cambiato `AppExit Default Restart` → `AppExit Default Exit`
  - Restart automatico solo su crash reali (exit code != 0), non su terminazione normale
  - Previene loop di restart quando applicazione termina volontariamente

### Changed
- ♻️ **Service Restart Logic**
  - Semplificata implementazione in `app/api/system.py` (da 80+ righe a 50 righe)
  - Migliore logging per troubleshooting: traccia ogni tentativo di restart
  - Compatibilità garantita con installazioni dove NSSM non è configurato nel PATH di sistema

### Added
- ✨ **Diagnostic Tool** - Nuovo script `tools/diagnose_restart.ps1`
  - Verifica completa configurazione (servizio, NSSM, PATH, .env, porte in ascolto)
  - Identifica problemi critici e warning con raccomandazioni automatiche
- ✅ **Test Suite Expansion** - Aggiunti 14 test per restart service
  - Suite test totale: 71 → 85 test

---

## [1.0.2] - [2026-01-14] - Rimozione campo secondo dalla schedulazione

### Changed
- Dashboard Scheduler: rimosso il campo "Secondo" da Add/Edit
- Le schedulazioni in modalità classic ora prevedono solo `hour` e `minute`
- Backend: il valore `second` (se presente in elementi legacy di `connections.json`) viene ignorato nella creazione dei trigger APScheduler
- Documentazione: aggiornato README per chiarire che i secondi non sono configurabili da dashboard

### Notes
- Il report giornaliero continua a mostrare l'orario di partenza con precisione al secondo, ma la configurazione dei secondi non è prevista

---

## [1.0.1] - [2026-01-14] - Fix salvataggio impostazioni e robustezza scheduler

### Fixed
- API Settings (`POST /api/settings/env`): corretta la risposta che causava HTTP 500 (NameError)
- Scheduler: coercizione sicura dei timeout `scheduler_query_timeout_sec` e `scheduler_write_timeout_sec` a numeri positivi (float)
- Storico scheduler: caricamento tollerante a file vuoti/corrotti con backup automatico
- History errori: registrazione corretta di `query` e `connection` negli eventi di errore

### Changed
- Settings UI: messaggi di errore più chiari in caso di failure del salvataggio
- Salvataggio atomico tramite file temporaneo in `exports/_tmp`

### Test
- Suite completa: 71 passed, 0 failed

---

## [1.0.0] - [2026-01-12] - Secondi nello scheduling, UX di riavvio, persistenza `.env`, pulizia test automatica

### Added
- Scheduling `classic`: supporto opzionale del campo `second` (SS, 0‑59)
- Endpoint di sistema: `POST /api/system/restart` per riavviare l'applicazione
- Settings UI: pulsante "Riavvia App" con overlay informativo e polling di salute durante down/up
- Timeout configurabili da UI: `scheduler_query_timeout_sec` e `scheduler_write_timeout_sec`

### Changed
- API Settings (`/api/settings/env`): writer `.env` ristrutturato per generare il file secondo template
- Frontend Scheduler: i campi `hour/minute/second` si abilitano/disabilitano coerentemente con `scheduling_mode`
- Test unitari: la porta attesa dall'app viene letta dinamicamente da `get_env_vars()`

### Fixed
- Evitata regressione su `.env`: i nuovi campi non vengono più azzerati al salvataggio
- Pulizia artefatti di test: endpoint `/api/scheduler/cleanup-test` e hook `pytest_sessionfinish`

### Test
- Suite completa: 71 passed, 0 failed

---

## [0.9.0] - [2026-01-08] - Impostazioni UI, Report giornaliero, coerenza navbar

### Added
- Pagina "Impostazioni" raggiungibile via navbar
- API Settings: `GET /api/settings/env`, `POST /api/settings/env`
- Report giornaliero schedulazioni: `GET /api/reports/daily?date=YYYY-MM-DD`, `POST /api/reports/daily/send`

### Changed
- Settings UI: icona gear corretta, titoli di sezione con font più grande
- Navbar coerenza: link "Log" e "Impostazioni" aggiunti in tutte le pagine
- Report giornaliero HTML: aggiunta colonna "Partenza" (data token)
- Email subject del report giornaliero: "Report schedulazioni PSTT"

### Test
- Suite completa: 71 passed, 0 failed

---

## [0.8.0] - [2026-01-07] - Log Viewer + API logs, semplificazioni UI Scheduler

### Added
- Nuova pagina "Log Viewer" raggiungibile da Home via link "Log"
- API Logs: `GET /api/logs/list`, `GET /api/logs/read-today`, `GET /api/logs/read`
- Supporto lettura log compressi (`.gz`)

### Changed
- `app/frontend/logs.html`: UI semplificata con caricamento automatico
- `app/frontend/scheduler_dashboard.html`: precompilazione default in oggetto/corpo email

### Test
- Suite completa: 62 passed, 0 failed

---

## [0.7.0] - [2025-12-29] - Refinement Scheduler UI + API delete fix

### Changed
- Scheduler UI: ulteriori affinamenti layout Aggiungi/Modifica schedulazioni
- UI elenco schedulazioni: anteprima "Data fine validità" evidenziata in rosso se scaduta

### Fixed
- `app/api/scheduler.py`: `DELETE /api/scheduler/scheduling/{idx}` rimuove solo la schedulazione selezionata

### Test
- Suite completa: 62 passed, 0 failed

---

## [0.6.0] - [2025-12-24] - Scheduler UI allineata, filtro Query per Connessione

### Changed
- Scheduler UI: campo Query si popola dinamicamente solo con query compatibili con connessione selezionata
- Layout coerente tra Aggiungi e Modifica

### Fixed
- Scheduler Service: risolto `UnboundLocalError` in `run_scheduled_query()`
- Config: disabilitata schedulazione legacy `test_query.sql`

### Test
- Suite completa: 62 passed, 0 failed

---

## [0.5.0] - [2025-12-23] - Token Replacement in Email Subject/Body

### Added
- Scheduler Token Replacement: token disponibili per filename ora utilizzabili anche in oggetto/corpo email
- Nuovo metodo `render_string()` in `SchedulingItem`

### Changed
- `app/models/scheduling.py`: refactoring del metodo `render_filename()`
- `app/services/scheduler_service.py`: subject e body email processati tramite `render_string()`

### Example
- Subject: `"IV dopo Rerouting del {date-1}"` → `"IV dopo Rerouting del 2025-12-22"`

---

## [0.4.0] - [2025-12-19] - Campi Email nello Scheduler e storico schedulazioni ripristinato

### Added
- Scheduler UI: aggiunti campi email (email_to, email_cc, email_subject, email_body)
- Default corpo email applicato

### Changed
- Modello `SchedulingItem`: nuovi campi email
- API `/api/scheduler/history`: applica filtro "ultimi 30 giorni" lato API

### Fixed
- Storico schedulazioni: non viene più troncato all'avvio del servizio
- Invio email CC: destinatari in `email_cc` inclusi nell'envelope SMTP

### Test
- Suite completa: 62 passed, 0 failed

---

## [0.3.0] - [2025-12-18] - Preview sicuro PostgreSQL/SQL Server, timeout scheduler aumentato

### Changed
- UI: spostata barra di stato sotto la barra superiore
- UI: tempo mostrato in millisecondi e secondi
- Backend: `_add_limit_clause()` rimuove `;` finali prima di applicare limiti
- Scheduler: aumentato `scheduler_query_timeout_sec` a 900s (15 minuti)

### Fixed
- Query `TT2_STAMPA-PCL-001`: rimossa `;` finale
- `connections.json`: corretta struttura per voce `C02-TT2_STAMPA`

### Test
- Suite completa: 62 passed, 0 failed

---

## [0.2.0] - [2025-12-04] - Export Excel/CSV server-side

### Changed
- Export behavior: Client-side Excel export removed; UI richiede exports dall'API server

### Fixed
- Risolto blocco esportazione file excel a 1000 righe

### Removed
- Rimosso bundle SheetJS locale `app/static/js/xlsx.full.min.js`

---

## [0.1.0] - [2025-11-19] - Multistep & Regression

### Added
- `tools/run_query_regression.py`: script per test sulle query SQL

### Changed
- `tools/run_query_regression.py`: selezione automatica `default_connection`
- `app/services/query_service.py`: ripristinata esecuzione statement senza rimozione hint Oracle `PARALLEL`

### Fixed
- Corrette diagnostiche per script SQL multistep

---

## [0.0.1] - [2025-08-12] - Release iniziale

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
- Core Framework: FastAPI con gestione lifecycle applicazione
- Database Management: ConnectionService con pool connessioni SQLAlchemy
- Query Processing: QueryService con parsing parametri Oracle define
- Frontend: SPA JavaScript con interazioni AJAX
- Configuration: Sistema configurazione centralizzato con Pydantic
- Logging: Log rotazione e compressione automatica
- Error Handling: Gestione errori completa

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
