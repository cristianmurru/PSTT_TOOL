# Changelog

Tutte le modifiche importanti a questo progetto saranno documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.1] - [2026-02-11] - Fix connessioni stale Oracle e controllo riavvio produzione

### Fixed
- 🔒 **Oracle connection pool stale connections**: risolto problema timeout notturni schedulazioni
  - **pool_pre_ping abilitato**: validazione connessioni prima dell'uso con `SELECT 1 FROM DUAL`
  - **pool_recycle ridotto**: da 3600s (1h) a 1800s (30min) per prevenire timeout idle Oracle
  - **Cleanup timeout esplicito**: chiusura connessioni stale dopo timeout query
  - **Diagnostics**: aggiunto `get_pool_status()` per monitoraggio pool (size, checked_in, checked_out)
  - File modificati: `app/services/connection_service.py`, `app/services/scheduler_service.py`
- 🔧 **Versione dinamica da CHANGELOG**: `app_version` estratta automaticamente da CHANGELOG.md
  - Elimina necessità di aggiornamento manuale versione in `config.py`
  - Funzione `_extract_version_from_changelog()` in `app/core/config.py`
  - Titolo browser sincronizzato con versione CHANGELOG

### Added
- 🎛️ **Controllo riavvio app configurabile**: nuova variabile `ENABLE_APP_RESTART` in `.env`
  - Disabilita pulsante "Riavvia App" in produzione (`ENABLE_APP_RESTART=false`)
  - Protezione API: endpoint `/restart` ritorna HTTP 403 se disabilitato
  - Nuovo endpoint `/restart/enabled` per verificare stato
  - UI dinamica: pulsante disabilitato con tooltip esplicativo
  - File modificati: `.env.example`, `app/core/config.py`, `app/api/system.py`, `app/templates/settings.html`

### Changed
- ✅ **Test suite aggiornata**: aggiunti test per nuove feature
  - Test `TestRestartEnabledControl` per controllo riavvio (3 test)
  - Fix test `test_retry_scheduled_on_query_timeout` con inizializzazione scheduler
  - 224 test passano (100% success rate)

---

## [1.2.0] - [2026-02-10] - Parametri lista con validazione e supporto multi-formato
  - Funzione `_extract_version_from_changelog()` con fallback a "1.0.0"
  - File modificati: `app/core/config.py`

### Added
- 🔐 **Controllo visibilità riavvio app**: variabile `ENABLE_APP_RESTART` per produzione
  - **Backend protection**: endpoint `/api/system/restart` ritorna HTTP 403 se disabilitato
  - **Frontend control**: pulsante riavvio disabilitato dinamicamente via API check
  - **Status endpoint**: `/api/system/restart/enabled` per verificare configurazione
  - **Configurazione**: `.env` con `ENABLE_APP_RESTART=false` disabilita riavvio in produzione
  - File modificati: `app/core/config.py`, `app/api/system.py`, `app/templates/settings.html`
- ✅ **Test coverage**: aggiunti test per feature `enable_app_restart`
  - Test HTTP 403 quando disabilitato
  - Test funzionamento normale quando abilitato
  - Test endpoint `/restart/enabled` status
  - File modificati: `tests/test_system_restart.py`

### Technical Details
- **Connection Pool Fix**:
  - `pool_pre_ping: True` → SQLAlchemy esegue `SELECT 1 FROM DUAL` prima di usare connessione dal pool
  - `pool_recycle: 1800` → ricicla connessioni ogni 30 min (prima timeout idle Oracle)
  - Timeout cleanup in `scheduler_service.py` linea 311-313: chiusura esplicita dopo timeout
  - Pool diagnostics: `get_pool_status(connection_name)` ritorna metriche pool
- **Dynamic Version**:
  - Funzione `_extract_version_from_changelog()` cerca pattern `## [X.Y.Z]` o `[X.Y.Z] - [YYYY-MM-DD]`
  - `app_version: str = Field(default_factory=_extract_version_from_changelog)` in Settings
  - Supporto fallback a "1.0.0" se CHANGELOG non trovato o parsing fallito
- **Restart Control**:
  - Settings: `enable_app_restart: bool = True` (default abilita per retrocompatibilità)
  - API: controllo in `/api/system/restart` con `HTTPException(403)` se disabilitato
  - Frontend: fetch `/api/system/restart/enabled` all'avvio, disabilita pulsante se `enabled: false`
  - Tooltip esplicativo: "Riavvio disabilitato in configurazione (enable_app_restart=false)"

### Breaking Changes
Nessuno. Tutte le modifiche sono backward compatible con default che preservano comportamento esistente.

---

## [1.2.0] - [2026-02-10] - Parametri lista con validazione e supporto multi-formato

### Added
- 📋 **Parametri lista per query**: gestione intelligente di parametri multipli (fino a 1000 elementi) con auto-detection pattern-based
  - **Auto-detection**: riconoscimento automatico parametri contenenti `LIST`, `BARCODES`, `CODES`, `IDS` nel nome (case-insensitive)
  - **Multi-formato input**: supporto formati diversi nello stesso campo textarea:
    - Virgola: `123,456,789`
    - Newline: `123\n456\n789` (incluso CR+LF Windows)
    - Già formattato: `'123','456','789'`
    - Doppi apici: `"123","456","789"`
  - **Normalizzazione**: tutti i formati vengono trasformati in formato SQL standard `'val1','val2','val3'`
  - **Validazione max 1000**: limite esplicito con contatore live (X/1000) e highlight errori
  - **Troncamento automatico**: oltre 1000 elementi vengono troncati con warning nel log
  - **Supporto valori alfanumerici**: barcode e codici possono contenere lettere e numeri
  - **Supporto lunghezze variabili**: elementi con lunghezza diversa gestiti correttamente
- 🎨 **UI textarea per liste**: interfaccia dedicata per parametri lista con validazione live
  - **Textarea 5 righe** invece di input singola riga (font monospace per leggibilità)
  - **Contatore live**: aggiornamento in tempo reale del numero elementi (X/1000)
  - **Validazione colori**: bordo rosso + contatore rosso bold quando > 1000
  - **Blocco esecuzione**: pre-validazione frontend impedisce submit con liste troppo lunghe
  - **Placeholder descrittivo**: guida utente sui formati supportati

### Changed
- 🔍 **Query multi-statement migliorate**: supporto completo per query con preamble (es. `ALTER SESSION SET...`)
  - Ogni statement separato da `;` viene eseguito in sequenza
  - Commit automatico dopo DML/DDL per database Oracle
  - L'ultimo `SELECT` restituisce il risultato all'utente
  - Diagnostica dettagliata in caso di errore su statement specifico
- 📝 **Query refactoring**: normalizzazione casing SQL in query informative (uppercase SELECT/FROM/WHERE/ORDER BY)
- 🗑️ **Cleanup connections.json**: rimossa schedulazione test DSX obsoleta

### Fixed
- 🐛 **Parametro singolo vs lista**: `BARCODE` != `BARCODE_LIST` - solo parametri con naming pattern specifico vengono trasformati
  - Query CDG-INF-004: usa `BARCODE_LIST` → funziona con input multipli
  - Query CDG-INF-005: usa `BARCODE` → fallisce con input multipli (comportamento corretto)
- ⚙️ **Robustezza scheduler**: aggiunti parametri configurabili per gestione misfire e coalesce
  - `scheduler_coalesce_enabled`: accorpa esecuzioni perse (default: true)
  - `scheduler_misfire_grace_time_sec`: finestra tolleranza per job in ritardo (default: 900s)
  - Applicati a tutti job (cleanup, daily report, export schedulati)

### Technical Details
- Backend/Services: `app/services/query_service.py`
  - Metodo `_format_list_parameter(value)`: normalizzazione input multipli con regex split `[,\n\r\s]+`
  - Escape apici: rimozione nel preprocessing (pattern `re.sub(r"['\"]", '', value)`)
  - Validazione 1000 elementi con troncamento automatico
  - Pattern detection: `any(kw in param_name.upper() for kw in ['LIST', 'BARCODES', 'CODES', 'IDS'])`
  - Multi-statement: split SQL per `;`, esecuzione sequenziale, gestione commit Oracle
- Frontend/UI: `app/static/js/main.js`
  - Funzione `renderParametersForm()`: detection automatica parametri lista via regex `/list|barcodes?|codes?|ids?/i`
  - Render textarea 5 righe con classe `font-mono text-sm` per leggibilità
  - Validazione live con event listener `input` e `blur`
  - Conteggio elementi: split per `[,\n\r\s]+` dopo rimozione apici
  - Highlight errori: `parameter-invalid` class per bordi rossi
  - Pre-execution validation: blocco submit con messaggio errore esplicito
- Frontend/Templates: `app/templates/index.html`
  - Attributo `data-app-env="{{ app_environment }}"` per controlli ambiente
- Backend/API: `app/api/scheduler.py`
  - Helper `_to_int()` per conversione robusta parametri numerici
  - Applicazione settings `misfire_grace_time` e `coalesce_enabled` a tutti job
  - Daily report job ri-aggiunto durante reload_scheduler_jobs per evitare perdita dopo CRUD schedulazioni
- Backend/API: `app/api/settings.py`
  - Aggiunti `scheduler_coalesce_enabled` e `scheduler_misfire_grace_time_sec` in ALLOWED_KEYS
- Backend/Config: `app/core/config.py`
  - Nuovi campi Settings: `scheduler_coalesce_enabled: bool = True` e `scheduler_misfire_grace_time_sec: int = 900`
- Frontend/Settings: `app/templates/settings.html`
  - Sezione "Robustezza Scheduler" con input per coalesce e misfire
- Query: modifiche multiple
  - `Query/Affari Legali/CDG-AL-002--Estrati Tracciatura - tracciato AEG.sql`: `define BARCODE_LIST` con commento formati supportati, preamble `ALTER SESSION SET nls_date_format/nls_timestamp_format`
  - `Query/Informative/CDG-INF-001`, `CDG-INF-002`, `CDG-INF-004`: normalizzazione uppercase keywords
  - `Query/Informative/CDG-INF-005`: nuovo file test con `define BARCODE` (non trasformato)
  - Rimossi file `.lnk` Windows
  - Ripristinato `Query/Affari Legali/CDG-AL-001--Estrai spedizioni da Anagrafica.sql` (erroneamente eliminato)
- Tests: `tests/test_list_parameters.py`
  - 20 nuovi test per funzionalità parametri lista
  - Test `_format_list_parameter()`: 15 test (comma, newline, CR+LF, mixed, alphanumeric, quotes, empty, max 1000, truncation, whitespace)
  - Test `_substitute_parameters()`: 5 test (detection BARCODE_LIST/CODES/IDS, non-list params, case-insensitive)

### Test
- ✅ Suite completa: 225 passed, 0 failed (aggiunti 20 test nuovi)
- ✅ Test parametri lista: copertura completa formati input e edge cases
- ✅ Test regressioni: nessuna regressione su test esistenti (205 test)

### File toccati (principali)
- Backend/Services: `app/services/query_service.py` (metodo `_format_list_parameter`, multi-statement handling, substitution logic)
- Backend/Services: `app/services/scheduler_service.py` (robustezza scheduler: misfire, coalesce, daily report reload fix)
- Backend/API: `app/api/scheduler.py` (helper `_to_int`, applicazione settings scheduler a tutti job)
- Backend/API: `app/api/settings.py` (nuove chiavi: `scheduler_coalesce_enabled`, `scheduler_misfire_grace_time_sec`)
- Backend/Config: `app/core/config.py` (nuovi campi Settings robustezza scheduler)
- Frontend/UI: `app/static/js/main.js` (textarea render, validazione live, pre-execution check)
- Frontend/Templates: `app/templates/index.html` (data-app-env attribute), `app/templates/settings.html` (sezione robustezza)
- Query: `Query/Affari Legali/CDG-AL-002` (BARCODE_LIST + ALTER SESSION), `Query/Informative/CDG-INF-001,002,004,005` (normalizzazione + restore CDG-AL-001)
- Tests: `tests/test_list_parameters.py` (20 test nuovi), `connections.json` (cleanup schedulazione test)

---

## [1.1.9] - [2026-02-06] - Fix restart servizio e conteggio fallimenti report

### Fixed
- 🔄 **Restart applicazione da UI**: risolto problema restart servizio Windows senza privilegi amministratore
  - Implementato "hot restart": terminazione processo con exit code 0 per trigger auto-restart NSSM
  - Script PowerShell salvati su disco come processi completamente detached (sopravvivono al parent)
  - Strategia multi-livello: Windows native → NSSM restart → NSSM stop+start  
  - Configurato NSSM con `AppExit Default Restart` per riavvio automatico
  - Tempo restart totale: ~7 secondi (2 sec delay + 5 sec NSSM)
  - **Ricarica completa**: connections.json, schedulazioni, configurazioni Kafka/SMTP, codice Python
- 📊 **Conteggio fallimenti report**: corretto conteggio fallimenti nel report giornaliero
  - Includeva solo status "fail", ora include anche "retry_scheduled"
  - Report ora mostra correttamente tutti i tentativi falliti
- 📚 **TROUBLESHOOTING nel viewer**: aggiunto TROUBLESHOOTING.md al markdown viewer dell'applicazione
  - Accessibile da menu Help in tutte le pagine (navbar)
  - Link presente in: index, scheduler_dashboard, logs, settings, kafka_dashboard, markdown_viewer

### Changed  
- 🔧 **Sistema restart**: nuovo parametro `hot_restart=true` (default) nell'endpoint `/api/system/restart`
  - `hot_restart=true`: termina processo Python, NSSM riavvia automaticamente (NO admin richiesto)
  - `hot_restart=false`: usa strategie originali Windows service restart (richiede admin)
- 📝 **Nuovo endpoint**: `GET /api/system/service/restart-logs` per consultare log di restart temporanei

### Technical Details
- Backend/API: `app/api/system.py`
  - Funzione `_schedule_hot_restart()`: terminazione controllata con Timer e os._exit(0)
  - Funzione `_restart_as_service()`: script PowerShell salvati in %TEMP% con logging dettagliato
  - Processo detached: flags `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` (0x00000208)
  - Log file temporanei: `%TEMP%\pstt_restart_<timestamp>.ps1` e `.log`
- Backend/Services: `app/services/daily_report_service.py`
  - Logica conteggio: `status in ("fail", "retry_scheduled")` invece di `status == "fail"`
- Frontend: `app/main.py`  
  - Route `GET /docs/troubleshooting`: rendering TROUBLESHOOTING.md con template markdown_viewer.html
- Frontend/Templates: tutti i template HTML aggiornati con link TROUBLESHOOTING in helpDropdown
- NSSM Configuration: servizio configurato con `AppExit Default Restart` e `AppRestartDelay 5000ms`
- Tests: `tests/test_system_restart.py`
  - 18 test totali per restart (3 nuovi per hot_restart)
  - Test per `_schedule_hot_restart()`, exit code 0, Timer scheduling
  - Aggiornati test esistenti per nuovo comportamento (script su file invece di inline)

### Root Cause Analysis
**Problema restart originale:**
1. Script PowerShell inline moriva quando processo Python parent terminava
2. NSSM perdeva traccia del PID dopo os.execv() (sostituiva processo invece di terminare)
3. Comandi `Stop-Service`/`Start-Service` richiedono privilegi amministratore

**Soluzione implementata:**
1. Script salvati su disco: sopravvivono indipendentemente dal parent
2. Exit code 0: NSSM interpreta come "terminazione pulita" e riavvia automaticamente
3. NSSM gestisce il restart: nessun privilegio amministratore richiesto per l'utente

### Test
- ✅ Suite completa: 206 passed, 0 failed
- ✅ Test restart: 18 passed (inclusi 3 nuovi test hot_restart)
- ✅ Test regressioni: nessuna regressione introdotta

### File toccati (principali)
- Backend/API: `app/api/system.py` (hot restart, script detached, endpoint restart-logs)
- Backend/Services: `app/services/daily_report_service.py` (conteggio fallimenti)
- Frontend/Main: `app/main.py` (route /docs/troubleshooting)
- Frontend/Templates: `app/templates/*.html` (6 file: link TROUBLESHOOTING in help menu)
- Docs: `docs/TROUBLESHOOTING.md` (modifiche utente)
- Tests: `tests/test_system_restart.py` (3 nuovi test, 6 test aggiornati)
- Config: NSSM service (configurato AppExit Default Restart)
- Files: `nssm.exe` (ripristinato in root per compatibilità servizio)

---

## [1.1.8] - [2026-02-05] - Compressione export .gz e riorganizzazione script servizio

### Added
- 💾 **Compressione export gzip**: nuovo flag "Comprimi .gz" nelle schedulazioni per salvare file Excel compressi (`.xls.gz`)
  - Riduzione spazio disco ~10-30% con compressione lossless (gzip level 6)
  - Apertura trasparente in Windows Explorer (doppio click apre direttamente Excel)
  - Naming `.xls.gz` invece di `.xlsx.gz` per migliore integrazione Windows
  - Fallback automatico a `.xlsx` non compresso in caso di errore compressione
- ✅ **Test compressione**: nuovo test `test_compress_export.py` che verifica integrità file compressi/decompressi

### Changed
- ♻️ **Rimosso flag "Includi timestamp"**: sostituito dalla funzionalità di compressione (timestamp già disponibile via token `{timestamp}`)
- 🔧 **Script servizio in tools/**: spostati `install_service.ps1`, `manage_service.ps1`, `nssm.exe` dalla root alla cartella `tools/`
  - Aggiornati tutti i riferimenti nella documentazione (README, KAFKA_SETUP, KAFKA_RUNBOOK, TROUBLESHOOTING)
  - Aggiornato script diagnostico `tools/diagnose_restart.ps1`
- 📋 **Cleanup docs**: eliminata cartella `docs/Obsoleti/` (21 file obsoleti), preservati 3 file Kafka essenziali spostati in `docs/`
- 📝 **Documentazione aggiornata**: TESTING.md e TROUBLESHOOTING.md modernizzati con funzionalità v1.1.7

### Fixed
- 🧪 **Test path**: corretto path in `test_system_restart.py` per cercare `install_service.ps1` in `tools/` invece che root

### Technical Details
- Modello: aggiunto campo `output_compress_gz` in `SchedulingItem`, rimosso `output_include_timestamp`
- Scheduler: implementata logica compressione post-export in `scheduler_service.py`
  - Log dettagliati: `COMPRESS_START`, `COMPRESS_OK`, `COMPRESS_FAIL`
  - Cleanup automatico file `.gz` già gestito dal sistema esistente (>30 giorni)
- UI: checkbox "Comprimi .gz" in form ADD/EDIT schedulazioni

### Test
- ✅ Suite completa: 201 passed, 0 failed.

### File toccati (principali)
- Backend/Models: `app/models/scheduling.py` (campo `output_compress_gz`)
- Backend/Services: `app/services/scheduler_service.py` (logica compressione gzip)
- Backend/Config: `app/core/config.py` (normalizzazione scheduling)
- Frontend/Templates: `app/templates/scheduler_dashboard.html` (UI checkbox compressione)
- Tests: `tests/test_compress_export.py` (nuovo), `tests/test_system_restart.py` (path fix), `tests/unit/test_scheduling_item.py` (uso token timestamp)
- Tools: `tools/install_service.ps1`, `tools/manage_service.ps1`, `tools/nssm.exe`, `tools/diagnose_restart.ps1`
- Documentazione: `docs/README.md`, `docs/TESTING.md`, `docs/TROUBLESHOOTING.md`, `docs/KAFKA_SETUP.md`, `docs/KAFKA_RUNBOOK.md`, `docs/CHANGELOG.md`

---

## [1.1.7] - [2026-02-04] - Retry schedulazioni e impostazioni da UI

### Added
- 🔁 **Retry automatico schedulazioni in errore**: su timeout query/scrittura o errori export (incluso Kafka), il sistema pianifica automaticamente un job di retry one‑off tramite `DateTrigger`, con ritardo e numero massimo di tentativi configurabili.
- ⚙️ **Impostazioni da UI estese**: aggiunte chiavi configurabili da pagina Impostazioni per il comportamento del scheduler:
  - `scheduler_retry_enabled`
  - `scheduler_retry_delay_minutes`
  - `scheduler_retry_max_attempts`

### Changed
- 🧭 Storico schedulazioni: eventi di retry tracciati come `retry_scheduled` con dettaglio tentativo e messaggio d'errore.
- 📚 Documentazione aggiornata per chiarire il flusso di retry e le nuove impostazioni.

### Test
- ✅ Suite completa: 201 passed, 0 failed.
- ✅ Estesa suite pytest per coprire i flussi di retry:
  - Retry su timeout query
  - Retry su timeout scrittura
  - Retry su failure export Kafka (success rate basso)
  - Normalizzazione cron a 5 campi durante update API senza alterare `connection`/`query`

### File toccati (principali)
- Backend/Servizi: `app/services/scheduler_service.py` (metodo `_schedule_retry`, integrazione retry in rami failure)
- Frontend/Templates: `app/templates/settings.html` (nuove impostazioni scheduler)
- Documentazione: `docs/CHANGELOG.md`, `docs/README.md`

---

## [1.1.6] - [2026-02-04] - Edit schedulazioni stabile (preserva selezioni)

### Fixed
- 🛠️ **Modifica schedulazioni non cambia più automaticamente connessione e query**: quando si apre il form di modifica, le selezioni correnti vengono preservate e non vengono sovrascritte dalla ripopolazione asincrona.
- 🧯 **Guard repopolazione durante `isEditing`**: la funzione di aggiornamento connessioni evita overwrite; il dropdown query ripristina correttamente il valore preferito/precedente.

### Changed
- 🎚️ Migliorata coerenza dei dropdown in modalità modifica, evitando salti di stato UI.

### Test
- ✅ Suite completa: 196 passed, 0 failed.

### File toccati (principali)
- Frontend/Templates: `app/templates/scheduler_dashboard.html` (preservazione selezioni, guard repopolazione).
- Documentazione: `docs/CHANGELOG.md`, `docs/README.md`.

---

## [1.1.5] - [2026-02-03] - Fix stabilità barra di stato durante filtri

### Fixed
- 🎯 **Barra di stato fissa**: eliminato completamente il reflow verticale che causava lo spostamento della barra di stato durante l'applicazione dei filtri su lista query e tabella risultati.
- 📏 **Altezze fisse container**: container lista query (60vh) e tabella risultati (70vh) ora mantengono dimensioni costanti indipendentemente dal numero di elementi visibili dopo filtro.
- 🚫 **Scroll anchoring**: disabilitato `overflow-anchor` per prevenire salti automatici del viewport durante aggiornamenti DOM dinamici.

### Changed
- 🧹 **Codice pulito**: rimossa logica di compensazione scroll (`_lockScroll`, `_unlockScroll`) non più necessaria con altezze fisse.
- 📐 **CSS inline heights**: altezze ora definite inline per maggiore chiarezza (`height: 60vh; min-height: 60vh`).

### Test
- ✅ Suite completa: 196 passed, 0 failed.

### Comportamento
- Lo scroll automatico avviene **solo** dopo "Esegui Query" o "Torna a selezione", mai durante l'applicazione dei filtri.
- La barra di stato rimane sempre visibile e stabile tra la selezione query e i risultati.

---

## [1.1.4] - [2026-01-29] - Home UX e refactoring UI completo

### Added
- 🔼 **Torna a selezione**: nuovo pulsante nella testata dei risultati per tornare rapidamente alla sezione di selezione query; nasconde la griglia, azzera contatori e porta la vista in cima alla pagina.

### Changed
- 📍 **Barra di stato**: spostata tra la selezione query e i risultati per maggiore visibilità nel flusso operativo.
- 🎯 **Focus risultati**: al termine dell'esecuzione la UI porta il focus sulla tabella/contesto risultati con scroll morbido.
- 🔎 **Filtri dinamici**: limitati ai primi 6 campi del recordset per evitare affollamento UI.
- 🗂️ **Filtro sottocartelle**: selettore sottodirectory in Home con esclusione automatica di `tmp`, `_tmp` e `schedulazioni`.
- ↕️ **Ordine pulsanti**: nella testata risultati l'ordine è ora `Export Excel` → `Export CSV` → `Torna a selezione`.
- 🧰 **Refactoring UI**: unificazione layout/navbar e migrazione delle pagine da `app/frontend` a `app/templates` (Home, Logs, Scheduler, Impostazioni); icone/label attive uniformate, badge ENV allineato.

### Fixed
- ♻️ **Reset stato**: il ritorno alla selezione ripulisce correttamente preview, filtri e conteggi.

### Test
- ✅ Suite completa: 196 passed, 0 failed.

### File toccati (principali)
- Frontend/Templates: `app/templates/index.html`, `app/templates/logs.html`, `app/templates/scheduler_dashboard.html`, `app/templates/settings.html`.
- Static JS: `app/static/js/main.js`.
- Documentazione: `docs/CHANGELOG.md`, `docs/README.md`.

---

## [1.1.3] - [2026-01-28] - Badge ENV sobrio in navbar, report mail su ultime 24 ore, fix log UI

### Added
- 🏷️ **Badge ENV**: etichetta ambiente (`SVILUPPO/COLLAUDO/PRODUZIONE`) visibile ma sobria in alto a destra della navbar, allineata verticalmente ai link.

### Changed
- 📧 **Report mail**: il riepilogo schedulazioni ora, se eseguito senza data esplicita, seleziona le esecuzioni delle ultime 24 ore rispetto al momento di generazione, invece che dalla mezzanotte corrente.
- 🔧 **Posizionamento badge**: l'elemento è figlio diretto di `<nav>` con posizionamento assoluto (`top:50%; right:2cm; transform: translateY(-50%)`) per garantire allineamento coerente su tutte le pagine.

### Fixed
- 🪛 **Logs UI**: rimosso codice JavaScript mostrato in chiaro; loader e toggle sono ora correttamente racchiusi in `<script>`.

### Test
- ✅ Suite completa: 196 passed, 0 failed.

### File toccati (principali)
- Backend/Servizi: `app/services/daily_report_service.py` (finestra default 24h), `app/services/scheduler_service.py` (job giornaliero usa default 24h).
- Frontend/Templates: `app/templates/index.html`, `app/templates/kafka_dashboard.html`, `app/templates/markdown_viewer.html`, `app/frontend/scheduler_dashboard.html`, `app/frontend/logs.html`, `app/frontend/settings.html` (badge ENV in navbar, pulizia script).
- Documentazione: `docs/README.md`, `docs/CHANGELOG.md`.

## [1.1.2] - [2026-01-27] - Menu Aiuto, Viewer Markdown, fix Kafka fields, storico chiarito

### Added
- ❓ **Menu Aiuto in tutte le pagine**: aggiunto un'icona "?" in navbar con collegamenti rapidi a README e CHANGELOG.
- 📰 **Viewer Markdown**: nuova pagina di visualizzazione documentazione con stile GitHub-like, evidenziazione sintassi, embedding JSON sicuro e ricerca per parola chiave.
- 📚 **Route Documentazione**: `GET /docs/readme` (fallback automatico su `docs/README.md`) e `GET /docs/changelog` (normalizzazione headings e spaziatura per migliore leggibilità).

### Changed
- 🎛️ **Navbar pulita**: rimossa label versione evidenziata; icone uniformate (colorazione coerente con i link).
- 🕒 **Storico scheduler più chiaro**: i timeout di query e scrittura vengono registrati con messaggi espliciti; UI semplificata (rimosse badge e testo extra) mantenendo solo informazioni essenziali.

### Fixed
- 🧩 **Caricamento pagina Scheduler**: eliminato frammento template errato che causava errore JS e impediva il rendering.
- 🔧 **Kafka (edit schedulazioni)**: ripristinata corretta precompilazione e persistenza di `kafka_topic` e `kafka_key_field` nelle form di modifica; evitato overwrite con default.
- 🟦 **Toggle menu Aiuto**: script di apertura/chiusura corretti e uniformati su Scheduler, Log e Impostazioni.

### Test
- ✅ Suite completa: 196 passed, 0 failed.

### File toccati (principali)
- Frontend: `app/templates/index.html`, `app/frontend/scheduler_dashboard.html`, `app/frontend/logs.html`, `app/frontend/settings.html`, `app/templates/kafka_dashboard.html`, `app/templates/markdown_viewer.html`.
- Backend/API: `app/main.py` (route docs), `app/api/scheduler.py` (storico, add/put schedulazioni), `app/services/scheduler_service.py` (tracking timeout, export_mode).
- Documentazione: `docs/README.md`, `docs/CHANGELOG.md`.

## [1.1.1] - [2026-01-23] - Kafka UI metriche allineate, consumer diagnostica e usabilità

### Changed
- Dashboard Kafka: metriche aggregate allineate agli output dello scheduler (riepilogo, per‑topic, ultimi errori) con filtri periodo e drill‑down.
- Pulsanti e stati UI: "Leggi Messaggi" ora è disabilitato (grigio) finché la connessione Kafka non è testata; diventa verde quando attiva.

### Added
- Pannello "Consumer Rapido": lettura messaggi con selezione origine offset (`latest`/`earliest`).
- Diagnostica topic: nuovo pulsante "Info Topic" lato UI e relativo endpoint API per partizioni e range offset.
- Suggerimenti topic: datalist con topic di default (es. `PSTT.TEST-COLL`) e suggerimenti contestuali.
- API Kafka:
  - `GET /api/kafka/topic-info/{topic}` — informazioni partizioni e offset.

### Fixed
- `/api/kafka/consume`: rispetto del parametro `period` con seek iniziale coerente e timeout aumentati.
- Script PowerShell `tools/create_kafka_deploy_package.ps1`: rimossa variabile non utilizzata che causava warning dell'analyzer.

### Test
- ✅ Suite completa: 196 passed, 0 failed.

## [1.1.0] - [2026-01-21] - Integrazione completa Kafka per pubblicazione messaggi su topic da schedulazioni

### Added - Kafka Integration (STEP 1-7/8)

#### STEP 1-2: Foundation & Service ✅
  - Dipendenze: `kafka-python-ng==2.2.2` e `aiokafka==0.10.0`
  - Modelli Pydantic completi (`app/models/kafka.py`): `KafkaConnectionConfig`, `KafkaProducerConfig`, `KafkaExportConfig`, `KafkaMetrics`, `BatchResult`, `KafkaHealthStatus`
  - 36 nuove variabili configurazione in `app/core/config.py`
  - Supporto multi-cluster Kafka in `connections.json`
  - Helper `get_kafka_config()` per caricamento configurazione
  - Connection management asincrona con security (PLAINTEXT/SSL/SASL)
  - Message publishing singolo con retry automatico
  - JSON serialization custom per `datetime`, `date`, `Decimal`
  - Health check con verifica connettività broker
  - Metrics tracking: latenza, throughput, success rate
  - Error handling completo per timeout/broker unavailable
  - Context manager per gestione automatica risorse

#### STEP 3: Batch Publishing & Performance ✅
  - `send_batch()`: Invio batch con chunking intelligente (default 100 msg/chunk)
  - Processing parallelo messaggi con `asyncio.to_thread`
  - Flush periodico buffer ogni 10 chunk
  - Auto-reconnect se producer disconnesso
  - Throughput verificato: >100 msg/sec con 1000 messaggi
  - `send_batch_with_retry()`: Retry automatico con backoff esponenziale
  - Success rate threshold configurabile (default 95%)
  - Backoff: 100ms → 200ms → 400ms (max 3 retry)

#### STEP 4: Scheduler Integration ✅
  - Estensione `SchedulingItem`: `SharingMode.KAFKA`, campi `kafka_topic`, `kafka_key_field`, `kafka_batch_size`, `kafka_include_metadata`
  - Metodo `_execute_kafka_export()` in `SchedulerService`
  - Pipeline: query → trasformazione → batch export Kafka
  - Metadata automatici: source_query, source_connection, export_timestamp, export_id
  - Tracking completo in `scheduler_history.json`: kafka_topic, kafka_messages_sent, kafka_messages_failed, kafka_duration_sec

#### STEP 5: API & Metrics ✅
  - `POST /api/kafka/test`: Test connessione broker
  - `POST /api/kafka/send`: Invio messaggio singolo
  - `POST /api/kafka/batch`: Invio batch messaggi
  - `GET /api/kafka/metrics/summary`: Metriche globali aggregate
  - `GET /api/kafka/metrics/hourly`: Metriche ultime 24h
  - `GET /api/kafka/metrics/topics`: Breakdown per topic
  - `GET /api/kafka/health`: Health check producer Kafka
  - Tracciamento temporale con granularità oraria
  - Aggregazione multi-dimensionale (topic, connection, total)
  - Export JSON persistente su disco
  - Reset metriche manuale e automatico

#### STEP 6: UI & Dashboard ✅
  - Overview metriche in tempo reale (last 24h)
  - Grafici throughput e latency con Chart.js
  - Breakdown per topic con tabelle interattive
  - Sezione test: invio messaggi singoli/batch da UI
  - Health status producer con indicatori visivi
  - Opzione "Kafka" in dropdown Condivisione
  - 4 campi specifici: kafka_topic, kafka_key_field, kafka_batch_size, kafka_include_metadata
  - Show/hide dinamico campi in base a modalità selezionata
  - Form submission con costruzione automatica `kafka_config` object

#### STEP 7: Documentation & Testing ✅
  - `docs/KAFKA_SETUP.md` (~400 righe): Setup guide, troubleshooting, performance tuning, security SSL/SASL, FAQ
  - `docs/KAFKA_RUNBOOK.md` (~600 righe): Operational procedures, emergency scenarios, health checks, escalation matrix
  - 3 modalità test: single, batch, mixed load
  - Metriche latenza: avg, p50, p90, p99
  - Calcolo throughput (msg/sec)
  - Command-line interface con argparse
  - 111 test passed (pytest)
  - Coverage: 76% overall (kafka_service: 75%, metrics: 88%, api: 68%)
  - Test validazione modelli, service methods, API endpoints, scheduler integration

### Technical Details

### Next Steps
  - Pre-deploy checklist (credentials, network, topics)
  - Deploy Phase 1: Infrastructure setup
  - Deploy Phase 2: Test in production (1 job, monitor 1 week)
  - Deploy Phase 3: Gradual rollout (20K+ msg/day)
  - Post-deploy monitoring e weekly reviews



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

---
