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

## [2025-12-04] - Le esportazioni Excel/CSV vengono ora generate dall'API (POST /api/queries/export) per allineare i file prodotti dall'interfaccia con quelli generati dallo scheduler e ridurre carico/size sul browser

### Changed
- **Export behavior:** Client-side Excel export removed; UI now requests exports from the server API so files are generated server-side (matches scheduler output and reduces client-side memory/size issues).

### Fixed
- L'intervento risolve il blocco in fase di esportazione dei file excel a 1000 righe.

### Removed
- Removed local SheetJS bundle `app/static/js/xlsx.full.min.js` and related client-side export fallback. Clients must use server-side export endpoint (`POST /api/queries/export`).

## [2025-12-18] - Preview sicuro su PostgreSQL/SQL Server, barra di stato migliorata, timeout scheduler aumentato a 10 minuti

### Changed
- UI: spostata la barra di stato immediatamente sotto la barra superiore per visibilità immediata; allineati i margini laterali con il resto della UI.
- UI: la barra di stato mostra il tempo in millisecondi e tra parentesi in secondi (es. `2337ms (2.337s)`).
- UI: quando si cambia connessione, la barra di stato e i risultati vengono ripuliti; il nome query viene nascosto se non selezionata.
- UI: eliminata la duplicazione del nome query nella barra di stato.
- Backend: `_add_limit_clause()` ora rimuove eventuali `;` finali prima di applicare limiti, evitando errori sintattici.
- Backend: per PostgreSQL/MySQL il limite di preview viene applicato incapsulando la query (`SELECT * FROM (<sql>) AS _lim LIMIT N`), prevenendo l’iniezione del `LIMIT` dentro stringhe letterali.
- Scheduler: aumentato `scheduler_query_timeout_sec` a 900s (15 minuti) per ridurre timeout frequenti in produzione.

### Fixed
- Query `TT2_STAMPA-PCL-001--Ristampe
- Scheduler: aumentato `scheduler_query_timeout_sec` a 900s (15 minuti) per ridurre timeout frequenti in produzione.

### Fixed
- Query `TT2_STAMPA-PCL-001--RistampeLDV post rerouting.sql`: rimossa `;` finale e normalizzata il filtro `LIKE` per compatibilità con preview limit.
- `connections.json`: corregta struttura per voce `C02-TT2_STAMPA` (JSON valido).

### Test
- Esecuzione completa suite: 62 passed, 0 failed.

### Notes
- Export via UI continua a usare l’endpoint server-side (`POST /api/queries/export`) garantendo dataset completi (senza limiti), allineato al comportamento dello scheduler.

## [2025-12-23] - Token Replacement in Email Subject/Body

### Added
- **Scheduler Token Replacement**: I token disponibili per il filename (`{query_name}`, `{date}`, `{date-1}`, `{timestamp}`) ora possono essere utilizzati anche nell'oggetto e nel corpo delle email
  - Nuovo metodo `render_string()` in `SchedulingItem` per sostituzione token in stringhe generiche
  - Metodo helper `_build_token_replacements()` per centralizzare la logica di generazione token
  - Sostituzione automatica applicata a `email_subject` e `email_body` prima dell'invio email

### Changed
- `app/models/scheduling.py`: refactoring del metodo `render_filename()` per riutilizzare la logica comune con helper `_build_token_replacements()`
- `app/services/scheduler_service.py`: subject e body email ora processati tramite `render_string()` prima dell'invio

### Example
- Subject: `"IV dopo Rerouting del {date-1}"` → `"IV dopo Rerouting del 2025-12-22"`
- Body: `"Estrazione del {date} per {query_name}"` → `"Estrazione del 2025-12-23 per TEST_REPORT"`

## [2025-12-19] - Campi Email nello Scheduler e storico schedulazioni ripristinato

### Added
- Scheduler UI: aggiunti campi email per invio via scheduler — `Destinatari A (email_to)`, `Destinatari CC (email_cc)`, `Oggetto (email_subject)`, `Corpo (email_body)`.
- Default corpo email: applicato lo standard richiesto.

### Changed
- Modello `SchedulingItem`: introdotti i nuovi campi; `email_recipients` mantenuto per compatibilità come fallback.
- Config loader: normalizzazione dei nuovi campi da `connections.json`, con preferenza per `email_to` se presente.
- SchedulerService: l’invio email usa To/CC/Subject/Body; subject di default basato sul filename se non fornito.
- API `/api/scheduler/history`: applica il filtro “ultimi 30 giorni” lato API.

### Fixed
- Storico schedulazioni: non viene più troncato all’avvio del servizio; ora viene mantenuto integralmente su file e filtrato solo in risposta API.
- Invio email CC: i destinatari in `email_cc` sono ora inclusi nell’envelope SMTP (oltre che nell’header) garantendo la consegna; logging migliorato (To + Cc).

### UI
- `scheduler_dashboard.html`: form “Aggiungi/Modifica” aggiornata con i nuovi campi email e placeholder con il testo standard.
- Lista schedulazioni: visualizza la modalità di condivisione (Filesystem/Email) con icona.
- Modifica schedulazione: i campi Email sono visibili immediatamente quando la schedulazione è in modalità Email.
- Layout: campo “Data fine” allineato a destra; dropdown Query più largo; elenco giorni della settimana con altezza sufficiente per mostrarli tutti; textarea “Corpo mail” più alta per visibilità completa del testo di default.

### Test
- Suite completa: 62 passed, 0 failed.

### Ops
- Aggiornata guida di deploy con note per email (SMTP) e nuovi campi di schedulazione.
- Documentazione setup consolidata: ripristinato `Setup/Update R20251218.md`; `Setup/Update R20251219.md` presente per test/manuale, contenente riepilogo delle novità.

## [2025-12-24] - Scheduler UI allineata, filtro Query per Connessione, fix stabilità

### Changed
- Scheduler UI: il campo Query in Aggiungi/Modifica ora si popola dinamicamente solo con le query compatibili con la connessione selezionata (matching token `CDG`, `BOSC`, `TT2_UFFICIO`, ecc.).
- Layout coerente tra Aggiungi e Modifica: prima riga (Connessione, Query, Data fine) resa con la stessa griglia; uniformati label e help di "Cron expression"; rimossi ID errati che causavano stili incoerenti.
- UI minori: i `select` rispettano la larghezza della colonna evitando sovrapposizioni.

### Fixed
- Scheduler Service: risolto `UnboundLocalError` in `run_scheduled_query()` dovuto a import locale di `SchedulingItem`. Ora l'import è a livello di modulo e il rendering del filename usa sempre il modello.
- Config: disabilitata la schedulazione legacy `test_query.sql` in `connections.json` per evitare errori di runtime quando il file di test non è presente (la suite di test genera un file temporaneo quando necessario).

### Test
- Suite completa: 62 passed, 0 failed.

### Notes
- Il filtro Query per Connessione replica il comportamento della home: il token nel nome connessione determina le query mostrate.

## [2025-12-29] - Refinement Scheduler UI + API delete fix (feature/R20251219)

### Changed
- `app/frontend/scheduler_dashboard.html`: ulteriori affinamenti layout Aggiungi/Modifica schedulazioni.
  - "Output directory" spostata più vicino a "Condivisione" e allineata a sinistra con "Query"; si estende fino al bordo destro allineato alla listbox "Giorni della settimana".
  - In modalità Email, i campi `email_to`, `email_cc`, `email_subject`, `email_body` occupano tutta la colonna destra fino al bordo, mantenendo l'allineamento con Query.
  - Campo "Data fine" allineato a destra con bordo che coincide con quello della listbox "Giorni della settimana".
  - Spaziature migliorate tra la colonna "Condivisione" e i campi a destra per maggiore leggibilità.
- UI elenco schedulazioni: anteprima "Data fine validità" evidenziata in rosso se scaduta.

### Fixed
- `app/api/scheduler.py`: l'endpoint `DELETE /api/scheduler/scheduling/{idx}` ora rimuove esclusivamente la schedulazione selezionata (per indice) senza eliminare altre schedulazioni con la stessa query. Evita cancellazioni multiple indesiderate quando esistono modalità diverse (classic/cron) per la stessa query.

### Test
- Pytest: suite completa verde (62 passed).
- Aggiunte verifiche di non‑regressione per l'allineamento dei bordi destri e per le spaziature tra colonne nella dashboard scheduler.

### Branch
- Lavoro svolto e integrato su `feature/R20251219`.

## [2026-01-07] - Log Viewer + API logs, semplificazioni UI Scheduler (feature/R20251230)

### Added
- Nuova pagina "Log Viewer" raggiungibile da Home via link "Log": [app/frontend/logs.html](app/frontend/logs.html).
- API Logs:
  - `GET /api/logs/list` — elenca tutti i file in `logs/` (sia `.log` sia `.gz`, ordinati per mtime).
  - `GET /api/logs/read-today?kind=app|errors|scheduler[&tail=N]` — lettura log odierno.
  - `GET /api/logs/read?file=<nome>[&tail=N]` — lettura di log archiviate/compressi.
- Router registrato in [app/main.py](app/main.py) e route HTML `/logs`.

### Changed
- `app/frontend/logs.html`: UI semplificata — rimosso i bottoni, caricamento automatico del contenuto in base al file selezionato; supporto campo Tail per mostrare solo le ultime N righe.
- `app/frontend/scheduler_dashboard.html`: precompilazione dei default in oggetto/corpo email anche in Modifica quando si passa alla modalità Email o quando i campi sono vuoti.

### Test
- Suite completa `pytest` verde: 62 passed.

### Note
- I file di log ruotano e vengono compressi (`.gz`) con retention/rotation da configurazione; il viewer supporta lettura trasparente dei compressi.
- Nessuna modifica obbligatoria a `connections.json` o `.env` per questa release.