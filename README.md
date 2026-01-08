# PSTT Tool

**Strumento per l'esecuzione di query parametrizzate su database multi-vendor con scheduling automatico**

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

## 📋 Caratteristiche

- ✅ **Multi-database**: Supporto per Oracle, PostgreSQL, SQL Server
- ✅ **Query parametrizzate**: Interfaccia dinamica per inserimento parametri
- ✅ **Interfaccia web**: UI professionale con Tailwind CSS
- ✅ **Filtri e ordinamento**: Funzionalità avanzate sui risultati
- ✅ **Export**: Esportazione in Excel e CSV
- 🔄 **Scheduling automatico**: Esecuzione pianificata dei report (in sviluppo)
- 📊 **Monitoraggio**: Sistema di log e statistiche
- ✅ **Gestione script SQL multistep**: Esegui script con più step sequenziali, ciascuno con parametri e log dedicati
- ✅ **Gestione asincrona e concorrente dei job schedulati**: le schedulazioni vengono eseguite in parallelo grazie ad APScheduler con AsyncIOExecutor, evitando job saltati e garantendo performance anche con workflow complessi.

## 🚀 Avvio Rapido

### Prerequisiti

- Python 3.11
- Virtual environment (`.venv` già configurato)
- Driver database installati:
  - Oracle Instant Client (per Oracle)
  - PostgreSQL client (per PostgreSQL)
  - ODBC Driver per SQL Server

### Installazione

1. **Attiva il virtual environment**:
   ```bash
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

2. **Verifica le dipendenze** (già installate):
   ```bash
   pip list
   ```

3. **Configura le variabili d'ambiente**:
   - Modifica il file `.env` con le credenziali database reali
   - Le variabili seguono il pattern: `DB_USER_<NOME_CONNESSIONE>` e `DB_PASS_<NOME_CONNESSIONE>`

5. **Accedi all'interfaccia**:
   - Web UI: http://localhost:8000
   - API Docs: http://localhost:8000/api/docs

## 📁 Struttura Progetto
```
PSTT_Tool/
├── app/                        # Codice applicazione
│   ├── models/                 # Modelli dati
│   ├── services/               # Logica business
│   ├── api/                    # Endpoints REST API
│   ├── templates/              # Template HTML
│   └── static/                 # File statici (CSS, JS)
├── Query/                      # File query SQL
├── Export/                     # File export (esclusi da git)
├── logs/                       # File di log (esclusi da git)
├── tests/                      # Test unitari
├── connections.json            # Configurazione connessioni
├── requirements.txt            # Dipendenze Python
└── main.py                     # Entry point applicazione
```

## 🔧 Configurazione Database
### connections.json

Il file `connections.json` contiene la configurazione delle connessioni database:
```json
{
  "default_environment": "collaudo",
  "default_connection": "A00-CDG-Collaudo",
  "environments": ["collaudo", "certificazione", "produzione"],
    {
      "name": "A00-CDG-Collaudo",
      "environment": "collaudo",
      "db_type": "oracle",
      "description": "Database Oracle Collaudo CDG",
        "host": "10.183.128.21",
        "port": 1521,
        "service_name": "pdbcirccol",
        "username": "${DB_USER_A00-CDG-Collaudo}",
        "password": "${DB_PASS_A00-CDG-Collaudo}"
      }
    }
  ]
}
```
### File .env

Crea/modifica il file `.env` con le credenziali reali:

```bash
# === COLLAUDO ===
DB_USER_A00-CDG-Collaudo=your_oracle_user
DB_PASS_A00-CDG-Collaudo=your_oracle_password

DB_USER_A01-BOSC-Collaudo=your_oracle_user
DB_PASS_A03-TT2_UFFICIO=your_postgres_password


# === PRODUZIONE ===
DB_USER_C00-CDG-Produzione=your_oracle_user
DB_PASS_C00-CDG-Produzione=your_oracle_password
```

## 📝 Query SQL

### Formato Query

Le query SQL devono essere salvate nella directory `Query/` con estensione `.sql`.

### Parametri

I parametri possono essere definiti in due modi:

1. **Define Oracle**:
   define DATAFINE='17/06/2025'     --Opzionale
   ```

2. **Riferimenti parametri**:
   ```sql
   WHERE data >= TO_DATE('&DATAINIZIO', 'dd/mm/yyyy')
   ```


```sql
-- Estrazione accessi operatori
-- Query per estrarre gli accessi degli operatori per ufficio

define OFFICE_PREFIX='77%'  --Obbligatorio: Prefisso ufficio da cercare

SELECT 
    trim(id) as "ID",
    trim(operator_name) as "OPERATOR_NAME",
    trim(status) as "STATUS"
FROM tt_application.operator o
WHERE o.office_id LIKE '&OFFICE_PREFIX';
```

### Nomenclatura dei file query

Per garantire corretta mappatura delle query alle connessioni e al comportamento di scheduling, i file SQL in `Query/` devono seguire la seguente convenzione di naming:

- Struttura generale: `<PREFIX>-<AREA>--<NNN>--<Descrizione>[--TEST].sql`
   - `<PREFIX>`: codice progetto/ambiente funzionale (es. `CDG`, `BOSC`, `TT2_UFFICIO`). Deve comparire nel nome per mappare la query alla connessione corrispondente.
   - `<AREA>`: opzionale, può indicare il sotto-sistema o il gruppo (es. `NXV`, `INF`, `AL`).
   - `--<NNN>--`: numero sequenziale a tre cifre (es. `001`, `005`). Deve essere separato da doppio trattino `--` come nel repository.
   - `<Descrizione>`: titolo breve descrittivo (spazi ammessi, preferibilmente senza caratteri speciali).
   - `--TEST`: tag opzionale da usare per i file di test/integrazione (es. `CDG-TEST-001--...`).

Esempi validi:

- `CDG-TEST-001--Estrai ultimo stato - A2A.sql`
- `BOSC-TEST-001--Accessi operatori.sql`
- `TT2_UFFICIO-PCL-001--Estrai operatori PTL.sql`

Regole operative:

- Il tool di esecuzione proverà a mappare la connessione cercando i token (parte del nome connessione) dentro il nome del file; assicurati che il `PREFIX` sia riconoscibile e corrisponda a una connessione configurata in `connections.json`.
- Per i test automatici puoi utilizzare il suffisso `TEST` (consente di selezionare velocemente i file che devono essere eseguiti in regressione).
- Mantieni il formato dei separatori (`--`) per permettere al parser di riconoscere il numero sequenziale e la descrizione.


*** End Patch


## 🖥️ Interfaccia Web

### Funzionalità Principali

1. **Selezione Connessione**: Dropdown per cambiare database
2. **Lista Query**: Elenco query disponibili con descrizione
3. **Form Parametri**: Generato dinamicamente in base ai parametri
4. **Risultati**: Tabella con funzioni di:
   - Filtro per colonna (case-insensitive)
   - Ordinamento cliccando sull'header
   - Export Excel/CSV
5. **Barra Stato**: Mostra connessione, query, numero righe, tempo esecuzione

### Scorciatoie Tastiera

- `Ctrl + Enter`: Esegui query selezionata
- `Escape`: Chiudi errori/notifiche

## 🔄 Scheduling

Il sistema esegue query in modo programmato tramite APScheduler (con AsyncIOExecutor per esecuzioni concorrenti). Le schedulazioni possono essere configurate tramite UI e API e producono file di output salvati in `Export/`.

- Esempi di query schedulate (configurabili):
   - `BOSC-NXV--001--Accessi operatori.sql`
   - `CDG-NXV--005--Dispacci-Gabbie.sql`
   - `CDG-NXV--006--Mazzetti creati.sql`
   - `CDG-NXV--008--Esiti.sql`

- Output: i file vengono salvati in `Export/` con formato e nome generati dalla logica di rendering: `{query_name}_{YYYY-MM-DD}_{timestamp}.{ext}`. È possibile personalizzare il template di output nella schedulazione (es. includere nome connessione, filtri, ecc.).

- Engine e comportamento:
   - APScheduler gestisce trigger di tipo `cron` e `interval`.
   - Il backend normalizza le cron expression a 5 campi (minuto, ora, giorno, mese, giorno-settimana). Se viene fornita una cron a 6 campi (con seconds) la prima parte (seconds) viene rimossa e la normalizzazione viene riportata nella risposta API (`cron_normalized`).
   - Le schedulazioni sono eseguite in parallelo quando possibile; i job possono essere configurati con retry/timeout e con livello di concorrenza.

Consiglio operativo: quando inserisci una cron, verifica sempre che abbia 5 campi e usa https://crontab.guru per validarla rapidamente.

## 📊 API REST

### Endpoints Principali

- `GET /api/connections/` - Lista connessioni
- `POST /api/connections/test` - Test connessione
- `GET /api/queries/` - Lista query
- `POST /api/queries/execute` - Esegui query
- `GET /api/monitoring/health` - Health check

Documentazione completa: http://localhost:8000/api/docs

## 🗓️ Gestione Schedulazioni

- Interfaccia:
   - Dashboard utente su `/dashboard` per elencare, creare, modificare e rimuovere schedulazioni.
   - Form Add/Edit: i campi si abilitano/disabilitano in funzione del `scheduling_mode` (es. quando la modalità non è `cron`, il campo cron viene disabilitato — non solo nascosto — e la UI applica una leggera opacità alle label/campi disabilitati per rendere evidente lo stato). Vicino al campo `cron` è presente un piccolo help con link a `crontab.guru` e 3 esempi rapidi.

- Campi principali di una schedulazione:
   - `name`: nome descrittivo
   - `query`: file SQL da eseguire (da `Query/`)
   - `interval_seconds`: per modalità interval
   - `output_template`: template per il nome file di output
   - `enabled`: booleano per abilitare/disabilitare la schedulazione

- API (principali):
   - `GET  /api/scheduler/scheduling` — lista schedulazioni
   - `POST /api/scheduler/scheduling` — crea una nuova schedulazione (la API normalizza cron a 5 campi se necessario e risponde con `cron_normalized` quando applicabile)
   - `PUT  /api/scheduler/scheduling/{idx}` — aggiorna
   - `DELETE /api/scheduler/scheduling/{idx}` — elimina
   - `POST /api/scheduler/scheduling/{idx}/preview` — anteprima del nome file renderizzato e simulazione rapida del payload

- Validazioni e UX:
   - Il frontend effettua validazione preventiva delle cron (5 campi). In caso di cron a 6 campi viene mostrato un warning esplicito e l'anteprima viene bloccata fino alla correzione oppure il backend normalizzerà la cron se l'utente conferma il salvataggio.
   - Messaggi e log riportano sempre la `cron_original` e la `cron_normalized` per tracciare modifiche automatiche.

- Test automatici: `tests/test_scheduler_api_crud.py`, `tests/test_scheduler_preview.py`.

## 📊 Metriche Avanzate Scheduler

Il modulo di metriche fornisce visibilità operativa sulle schedulazioni e aiuta nell'individuazione di regressioni o colli di bottiglia.

- Metriche raccolte:
   - Storico (ultime N esecuzioni, default 20): per ogni run vengono salvati `query`, `connection`, `timestamp`, `status` (success/fail), `duration_ms`, `rows`, `error_message`.
   - Conteggio cumulativo di job `success` e `failed` su finestre temporali configurabili (es. 24h, 7gg).
   - Tempo medio e percentili (p50/p90/p99) delle durate di esecuzione.
   - Distribuzione dei timeout e degli errori per query.

- Endpoint e formato:
   "stats": { "avg_duration_ms": 340, "p90_ms": 1200 },
   "recent_runs": [ { "query": "...", "timestamp": "...", "status": "success", "duration_ms": 200 } ]

- Uso operativo:
   - In caso di spike di errori, il sistema registra i log completi in `logs/scheduler.log` con l'ID run per indagine.

Per incrementare i dettagli delle metriche (ad es. storage storico maggiore, esportazione CSV, integrazione Prometheus) si può estendere il servizio che raccoglie gli eventi di scheduler.

## 🐛 Debugging

### Log Files

I log sono salvati in `logs/`:
- `app.log` - Log generale applicazione
- `errors.log` - Solo errori
- `scheduler.log` - Log scheduler

- Pagina dedicata su `/logs` per la consultazione in sola lettura dei log odierni e archiviati/compressi (`.gz`).
- Seleziona il file dal menu e, facoltativamente, imposta `Tail` per mostrare solo le ultime N righe.
- API correlate: `GET /api/logs/list`, `GET /api/logs/read-today`, `GET /api/logs/read`.

## ⚙️ Impostazioni (.env via UI)

- Pagina `/settings` per leggere e aggiornare un sottoinsieme di chiavi `.env` (SMTP e Report giornaliero). Le modifiche vengono scritte in `.env` e possono richiedere il riavvio del servizio per riflettersi nelle schedulazioni.
- API:
   - `GET /api/settings/env`
   - `POST /api/settings/env`
- Chiavi supportate: `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_from`, `DAILY_REPORT_ENABLED`, `DAILY_REPORT_CRON`, `DAILY_REPORTS_HOUR`, `DAILY_REPORT_RECIPIENTS`, `DAILY_REPORT_CC`, `DAILY_REPORT_SUBJECT`, `DAILY_REPORT_TAIL_LINES`.

## 📧 Report giornaliero schedulazioni

- Descrizione: genera un riepilogo HTML delle schedulazioni eseguite nel giorno selezionato e lo invia via email.
- Configurazione in `.env` (modificabile da `/settings`):
   - `DAILY_REPORT_ENABLED=true|false`
   - `DAILY_REPORT_CRON` (se vuoto, fallback su `DAILY_REPORTS_HOUR`)
   - `DAILY_REPORTS_HOUR=6` (esempio)
   - `DAILY_REPORT_RECIPIENTS=a@x|b@y` (pipe come separatore)
   - `DAILY_REPORT_CC=` (opzionale)
   - `DAILY_REPORT_SUBJECT=Report schedulazioni PSTT`
   - `DAILY_REPORT_TAIL_LINES=50`
- SMTP: STARTTLS (porta default 587); configurare `smtp_host`, `smtp_port`, `smtp_from`, eventuali credenziali.
- API:
   - `GET /api/reports/daily?date=YYYY-MM-DD` — anteprima HTML
   - `POST /api/reports/daily/send?date=YYYY-MM-DD` — invio manuale

### Livelli di Log

Configura il livello nel file `.env`:
```bash
```
### Modalità Debug
Per abilitare il reload automatico:
```bash
export DEBUG=true
python main.py
```

## 🧪 Test

```bash
# Esegui tutti i test
pytest

# Test con coverage
pytest --cov=app --cov-report=html
```

## ⚠️ Nota importante: cron expressions e normalizzazione

Il sistema usa il formato cron standard a 5 campi: `minute hour day month day-of-week`.

- Se incolli o generi una cron a 6 campi (che include i secondi, es. `*/2 * * * * *`), questa verrà interpretata come esecuzione ogni N secondi.
- Per evitare esecuzioni indesiderate il backend implementa una normalizzazione/validazione:
   - Il frontend segnala e rifiuta le cron con 6 campi durante l'anteprima/salvataggio.
   - Le API `POST /api/scheduler/scheduling` e `PUT /api/scheduler/scheduling/{idx}` controllano se la cron ha 6 token; in tal caso la prima parte (seconds) viene rimossa automaticamente e la cron salvata come 5-campi. La risposta JSON includerà la chiave `cron_normalized` con `original` e `normalized` per tracciare la modifica.

Consiglio operativo: quando incolli un'espressione cron, verifica sempre che ci siano esattamente 5 campi separati da spazi. Puoi usare https://crontab.guru per validare rapidamente l'espressione.

## 📦 Contribuire (branch, commit, push, PR)

Usiamo lo stile Conventional Commits per i messaggi di commit. Esempi:

- `feat(scheduler): normalize 6-field cron expressions and add validation`
- `fix(frontend): disable cron input when scheduling_mode != cron`
- `chore(docs): update README with cron normalization notes`

Flusso consigliato (PowerShell / Windows):

```powershell
# crea un branch feature
git checkout -b feature/cron-normalization

# aggiungi le modifiche
git add -A

# commit con messaggio conventional
git commit -m "feat(scheduler): normalize 6-field cron expressions and add validation"

# push del branch (remote origin deve essere configurato)
git push -u origin feature/cron-normalization
```

Dopo il push, crea la Pull Request dal branch `feature/cron-normalization` verso `main` su GitHub. Se preferisci usare la CLI GitHub (`gh`):

```bash
gh pr create --base main --head feature/cron-normalization --title "feat(scheduler): normalize 6-field cron expressions" --body "Normalizzazione automatica delle cron a 6 campi; aggiunta validazione client/server."
```

Se il push fallisce per autorizzazione o per assenza del remote, esegui i comandi sopra nel tuo ambiente locale (assicurati che `origin` punti a `https://github.com/cristianmurru/<repo>.git`).

---

Se vuoi, posso ora creare il branch, committare le modifiche qui nel workspace e tentare il push verso `https://github.com/cristianmurru` (ti avviso se serve autenticazione). Vuoi che proceda? 

## 🚢 Deploy Produzione

### Come Servizio Windows

1. Crea un file batch `start_pstt.bat`:
   ```batch
   @echo off
   cd /d "C:\app\PSTT_Tool"
   .venv\Scripts\activate
   python main.py
   ```

2. Configura come servizio Windows usando NSSM o simili.

### Variabili Produzione

Nel file `.env` di produzione:
```bash
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

### Distribuire come servizio Windows (NSSM) - dettagli operativi

Per garantire che l'applicazione sia eseguita in background, si riavvii automaticamente al boot e sia resiliente ai crash, consigliamo di installarla come servizio Windows usando NSSM (Non-Sucking Service Manager).

Passaggi principali (riassunto):

1. Scarica NSSM da https://nssm.cc/download e copia `nssm.exe` nella root del progetto o in una cartella nel `PATH`.
2. Usa lo script `install_service.ps1` fornito nella root del progetto per installare/ricreare il servizio (richiede privilegi amministrativi):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_service.ps1
```

Lo script configura automaticamente i log e il riavvio in caso di failure.

### Comandi utili per la gestione del servizio

I comandi seguenti sono disponibili tramite lo script `manage_service.ps1` incluso nel repository. Esegui sempre PowerShell come amministratore per le operazioni di installazione/disinstallazione e gestione del servizio.

```powershell
# Stato del servizio
.\manage_service.ps1 -Action status

# Avvia
.\manage_service.ps1 -Action start

# Ferma
.\manage_service.ps1 -Action stop

# Riavvia
.\manage_service.ps1 -Action restart

# Mostra gli ultimi log (stdout/stderr)
.\manage_service.ps1 -Action logs

# Disinstalla il servizio (rimuove la registrazione NSSM)
.\manage_service.ps1 -Action uninstall
```

Se preferisci usare `nssm.exe` direttamente (se è nel `PATH` o nella cartella corrente):

```powershell
# Avvia
.\nssm.exe start PSTT_Tool

# Ferma
.\nssm.exe stop PSTT_Tool

# Stato
.\nssm.exe status PSTT_Tool

# Rimuovi
.\nssm.exe remove PSTT_Tool confirm
```

### Avvio manuale con porta parametrizzata (sviluppo / debug)

Per eseguire un'istanza manuale dell'app (utile per sviluppo o debug) su una porta diversa da quella del servizio, usa il parametro `--port` di `main.py`:

```powershell
# Esempio: lancia l'app su porta 8001
.venv\Scripts\Activate.ps1
python main.py --port 8001
```

In questo modo puoi avere contemporaneamente il servizio in background (es. su porta 8000) e una istanza manuale per sviluppo su altra porta.

Se vuoi esporre l'app su tutte le interfacce (ad es. per accesso da rete), passa anche `--host 0.0.0.0`:

```powershell
python main.py --host 0.0.0.0 --port 8001
```

### Note operative

- I file di configurazione e i dati (es. `connections.json`, `Query/`, `Export/`) sono condivisi tra il servizio e le istanze manuali: evita di modificare in parallelo per non creare race condition.
- I log del servizio si trovano in `logs/service_stdout.log` e `logs/service_stderr.log` (configurati da `install_service.ps1`).
- Per mantenere il repository leggero, valuta se tenere `nssm.exe` nella repo o copiarlo sul server in una cartella del `PATH`.


## ❓ Troubleshooting

### Errore "Driver non trovato"

**Oracle**: Installa Oracle Instant Client
```bash
# Download da: https://www.oracle.com/database/technologies/instant-client.html
```

**SQL Server**: Installa ODBC Driver
```bash
# Download da: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

### Errore "Connessione rifiutata"

1. Verifica credenziali nel file `.env`
2. Controlla connettività di rete
3. Verifica che il servizio database sia attivo

### Performance Lente

1. Controlla le query per ottimizzazioni
2. Aumenta il pool di connessioni in `connection_service.py`
3. Monitora log per errori

## 🆕 Novità v1.0.1
- Export Excel ora funzionante: SheetJS caricata localmente, nessun errore CORB
- Migliorato contrasto righe griglia risultati
- Header tabella risultati colorato blu
- Visualizzazione query: solo gruppo+nome, ordinamento alfabetico, refresh su stato connesso
- Eliminato file base.html non utilizzato

## 🖥️ Dashboard Hardware
- Il riquadro Health Check mostra spazio disco, RAM e CPU in tempo reale
- Dipendenza: `psutil` (in requirements.txt)

## 📦 Dipendenze Frontend
- SheetJS (xlsx) ora caricata localmente da `static/js/xlsx.full.min.js` per compatibilità con ambienti aziendali

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT. Vedi il file `LICENSE` per dettagli.

## 👥 Contributi

1. Fork del repository
2. Crea un branch feature (`git checkout -b feature/nuova-funzionalita`)
3. Commit delle modifiche (`git commit -am 'Aggiungi nuova funzionalità'`)
4. Push al branch (`git push origin feature/nuova-funzionalita`)
5. Crea una Pull Request

---

**PSTT Tool** - Sviluppato per semplificare l'esecuzione di query parametrizzate su database enterprise.

## ✨ Funzionalità avanzata: Script SQL multistep

Puoi ora creare script SQL suddivisi in step, ciascuno identificato da commenti speciali:

```
--$STEP 1$ -> Descrizione step
DELETE FROM ...;
--$STEP 2$ -> Altro step
INSERT INTO ...;
--$STEP 3$ -> Estrazione finale
SELECT ...
```

Ogni step viene eseguito in sequenza, con sostituzione automatica dei parametri e feedback in UI. I parametri opzionali non valorizzati vengono sostituiti con stringa vuota.

Questa funzionalità consente di gestire workflow complessi direttamente da file SQL, con feedback e log dettagliati per ogni step.
