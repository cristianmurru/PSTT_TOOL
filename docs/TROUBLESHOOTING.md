# 🐛 Troubleshooting PSTT Tool

## Errori Comuni e Soluzioni

### ❌ Errori Kafka Integration

#### Problema: Connection timeout ai broker Kafka

**Errore**:
```
KafkaConnectionError: Failed to connect to kafka broker
```

**Cause possibili**:
1. Broker non raggiungibili dalla rete
2. Porta Kafka chiusa da firewall
3. Bootstrap servers non corretti

**Soluzioni**:

1. **Verifica connettività broker**:
   ```powershell
   Test-NetConnection kafka-server -Port 9092
   ```

2. **Controlla configurazione in connections.json**:
   ```json
   "kafka_connections": [
     {
       "name": "kafka-prod",
       "bootstrap_servers": ["kafka1.prod:9093", "kafka2.prod:9093"],
       "security_protocol": "PLAINTEXT"
     }
   ]
   ```

3. **Test connessione da UI**:
   - Vai su `/kafka`
   - Usa il pulsante "Test Connessione"
   - Verifica output nel log

4. **Health check API**:
   ```powershell
   Invoke-RestMethod -Uri 'http://localhost:8000/api/kafka/health'
   ```

#### Problema: SSL/SASL Authentication failures

**Errore**:
```
AuthenticationFailedError: SASL authentication failed
```

**Soluzioni**:

1. **Verifica credenziali in .env**:
   ```env
   KAFKA_PROD_PASSWORD=your_secure_password
   ```

2. **Controlla security_protocol in connections.json**:
   ```json
   "security_protocol": "SASL_SSL",
   "sasl_mechanism": "SCRAM-SHA-512",
   "sasl_username": "pstt_user",
   "sasl_password": "${KAFKA_PROD_PASSWORD}"
   ```

3. **Verifica certificati SSL** (se richiesti):
   ```json
   "ssl_cafile": "C:/certs/kafka-ca.pem"
   ```

#### Problema: Topic not found

**Errore**:
```
UnknownTopicOrPartitionError: Topic 'pstt-data' does not exist
```

**Soluzioni**:

1. **Verifica esistenza topic**:
   - Usa pulsante "Info Topic" nella dashboard Kafka
   - Controlla log Kafka broker

2. **Crea topic manualmente** (se auto-create disabilitato):
   ```bash
   kafka-topics.sh --create --topic pstt-data --bootstrap-server localhost:9092
   ```

3. **Abilita auto-create** (solo dev/test):
   ```properties
   # Kafka broker config
   auto.create.topics.enable=true
   ```

#### Problema: Producer not ready

**Errore**:
```
KafkaProducerNotReadyError: Producer is not connected
```

**Soluzioni**:

1. **Riavvia servizio**:
   - Da UI: Impostazioni → Riavvia App
   - Da PowerShell: `Restart-Service PSTT_Tool`

2. **Controlla metriche Kafka**:
   ```powershell
   Invoke-RestMethod -Uri 'http://localhost:8000/api/kafka/metrics/summary'
   ```

3. **Verifica log**:
   ```powershell
   Get-Content logs\app.log -Tail 50 | Select-String "kafka"
   ```

#### Problema: Batch publishing failures

**Errore**:
```
Batch success rate below threshold: 85% < 95%
```

**Soluzioni**:

1. **Verifica timeout in .env**:
   ```env
   KAFKA_TIMEOUT_MS=30000
   KAFKA_REQUEST_TIMEOUT_MS=30000
   ```

2. **Riduci batch size**:
   ```env
   KAFKA_BATCH_SIZE=50  # invece di 100
   ```

3. **Monitora performance da dashboard Kafka**:
   - Throughput (msg/sec)
   - Latency (avg, p90, p99)
   - Success rate per topic

---

### ❌ Errori Connessione Database Oracle

#### Problema: Timeout query schedulazioni notturne (Stale Connections)

**Sintomi**:
- Tutte le schedulazioni notturne vanno in timeout (1200s)
- Query funzionano correttamente se eseguite manualmente da SQL Developer
- Dopo riavvio servizio, tutto riprende a funzionare normalmente
- Logs mostrano pattern ripetuto di timeout consecutivi

**Esempio log**:
```
2026-02-11 00:35:47 | ERROR | TIMEOUT_QUERY superati 1200.0s
2026-02-11 02:00:51 | ERROR | TIMEOUT_QUERY superati 1200.0s
2026-02-11 04:30:55 | ERROR | TIMEOUT_QUERY superati 1200.0s
...
2026-02-11 11:05:00 | INFO | START_QUERY timeout=1200.0s
2026-02-11 11:05:08 | INFO | END_QUERY duration=8.23s rows=125  # Successo dopo restart
```

**Causa principale**: **Connection pool stale connections**
- SQLAlchemy non valida connessioni prima dell'uso (`pool_pre_ping: False`)
- Connessioni nel pool diventano "stale" dopo idle timeout Oracle
- Oracle chiude connessioni idle > 30 minuti (dipende da configurazione DB)
- Application continua a usare connessioni chiuse dal pool → timeout
- Riavvio svuota pool → connessioni fresche → funziona temporaneamente

**Soluzioni** (applicate in v1.2.1):

1. **pool_pre_ping abilitato** (CRITICO):
   ```python
   # app/services/connection_service.py
   "pool_pre_ping": True  # Esegue SELECT 1 FROM DUAL prima di usare connessione
   ```

2. **pool_recycle ridotto**:
   ```python
   "pool_recycle": 1800  # 30 min invece di 60 min
   ```
   - Ricicla connessioni prima del timeout idle Oracle
   - Previene accumulo di connessioni stale

3. **Cleanup esplicito dopo timeout**:
   ```python
   # app/services/scheduler_service.py
   except asyncio.TimeoutError:
       # Chiudi connessione stale dopo timeout
       self.query_service.connection_service.close_connection(connection_name)
   ```

4. **Diagnostics pool** (monitoraggio):
   ```python
   # Verifica stato pool
   status = connection_service.get_pool_status('ORACLE_PROD')
   # Ritorna: pool_size, checked_in, checked_out, overflow
   ```

**Verifica fix applicato**:
```powershell
# 1. Controlla versione (deve essere >= 1.2.1)
Invoke-RestMethod -Uri 'http://localhost:8000/api/monitoring/health'

# 2. Verifica log pool_pre_ping
Get-Content logs\app.log | Select-String "pool_pre_ping: True"

# 3. Monitora schedulazioni overnight
Get-Content logs\scheduler.log -Tail 100 | Select-String "TIMEOUT"
# Non dovrebbero esserci timeout dopo il fix
```

**Workaround temporaneo** (se fix non applicato):
```powershell
# Riavvio programmato notturno (3:00 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-Command Restart-Service PSTT_Tool"
Register-ScheduledTask -TaskName "PSTT_Tool_Nightly_Restart" `
    -Trigger $trigger -Action $action -User "SYSTEM"
```

**Prevenzione problemi simili**:
- Sempre abilitare `pool_pre_ping: True` per database production
- Impostare `pool_recycle` < timeout idle database
- Monitorare pool metrics con `get_pool_status()`
- Configurare alerting su timeout consecutivi (>3)

#### Problema: ORA-12170 TNS:Connect timeout

---

### ❌ Errori Scheduler Avanzato

#### Problema: Timeout query o scrittura

**Errore**:
```
Scheduler timeout: query execution exceeded 900s
```

**Soluzioni**:

1. **Aumenta timeout da UI**:
   - Vai su `/settings`
   - Modifica `scheduler_query_timeout_sec` (default: 900s)
   - Modifica `scheduler_write_timeout_sec` (default: 300s)

2. **Verifica query problematiche**:
   ```powershell
   Get-Content exports\scheduler_history.json | ConvertFrom-Json | Where-Object { $_.status -eq 'timeout' }
   ```

3. **Ottimizza query SQL**:
   - Aggiungi indici su campi filtrati
   - Limita range date
   - Usa EXPLAIN PLAN (Oracle) o EXPLAIN (PostgreSQL)

#### Problema: Retry automatico non funziona

**Errore**:
```
Retry scheduling failed: max attempts reached
```

**Soluzioni**:

1. **Verifica configurazione retry in .env**:
   ```env
   scheduler_retry_enabled=true
   scheduler_retry_delay_minutes=30
   scheduler_retry_max_attempts=3
   ```

2. **Controlla storico retry**:
   - Dashboard Scheduler → Storico
   - Cerca eventi `retry_scheduled`

3. **Verifica log scheduler**:
   ```powershell
   Get-Content logs\scheduler.log -Tail 100
   ```

#### Problema: Cron expression invalida (6 campi)

**Errore**:
```
Invalid cron expression: expected 5 fields, got 6
```

**Causa**: Cron con secondi (formato non supportato)

**Soluzione**:

1. **Usa formato 5 campi**: `minute hour day month day-of-week`
   ```
   # ❌ SBAGLIATO (6 campi con secondi)
   */2 * * * * *
   
   # ✅ CORRETTO (5 campi)
   */2 * * * *
   ```

2. **Validazione online**: https://crontab.guru

3. **Il backend normalizza automaticamente**:
   - API POST/PUT rimuove primo campo se 6 token
   - Risposta include `cron_normalized`

#### Problema: Job sovrapposti (coalesce)

**Errore**:
```
Run 'job_name' skipped: previous run still active
```

**Soluzioni**:

1. **Aumenta intervallo schedulazione**:
   - Distanzia le esecuzioni
   - Considera tempo medio esecuzione query

2. **Usa coalesce=False** (permette sovrapposizioni):
   - Modifica schedulazione da UI
   - Campo "Coalesce" = False

3. **Monitora durata job**:
   ```powershell
   Get-Content exports\scheduler_metrics.json | ConvertFrom-Json | Select-Object -ExpandProperty duration_ms
   ```

---

### ❌ Errori Servizio Windows

#### Problema: Service restart failures

**Errore**:
```
Failed to restart service: Access denied
```

**Causa**: A partire dalla v1.1.9, il riavvio del servizio usa **Hot Restart** che NON richiede privilegi amministratore.

**Come funziona Hot Restart**:

1. **Il processo Python termina con exit code 0**
2. **NSSM rileva l'uscita e riavvia automaticamente il servizio** (dopo 5 secondi)
3. **Tutte le configurazioni vengono ricaricate** dal filesystem

**Vantaggi**:
- ✅ Non richiede privilegi amministratore
- ✅ Funziona da interfaccia web (pulsante "Riavvia App")
- ✅ Ricarica tutte le impostazioni (connections.json, config.scheduling.json, .env)
- ✅ Il servizio rimane in stato "Running" durante il restart

**Soluzioni se il restart fallisce**:

1. **Verifica configurazione NSSM auto-restart**:
   ```powershell
   .\nssm.exe get PSTT_Tool AppExit
   .\nssm.exe get PSTT_Tool AppRestartDelay
   ```
   Dovrebbe mostrare:
   - AppExit Default: Restart
   - AppRestartDelay: 5000 (ms)

2. **Restart manuale con privilegi admin** (fallback):
   ```powershell
   # PowerShell come Administrator
   Restart-Service PSTT_Tool
   ```

3. **Usa NSSM direttamente** (fallback):
   ```powershell
   # PowerShell come Administrator
   .\nssm.exe restart PSTT_Tool
   ```

4. **Verifica log del restart**:
   ```powershell
   # Guarda i log temporanei degli script di restart
   Get-Content "$env:TEMP\pstt_restart_*.log" | Select-Object -Last 30
   ```

#### Problema: NSSM configuration issues

**Errore**:
```
NSSM not found in PATH
```

**Soluzioni**:

1. **Aggiungi NSSM al PATH**:
   ```powershell
   $env:PATH += ";C:\App\PSTT_Tool"
   ```

2. **Reinstalla servizio**:
   ```powershell
   .\tools\install_service.ps1
   ```

3. **Verifica configurazione NSSM**:
   ```powershell
   nssm status PSTT_Tool
   nssm get PSTT_Tool AppDirectory
   nssm get PSTT_Tool AppExit
   ```

---

### ❌ Errori Impostazioni e Report

#### Problema: Salvataggio .env fallito

**Errore**:
```
HTTP 500: Failed to update .env file
```

**Soluzioni**:

1. **Verifica permessi file .env**:
   ```powershell
   icacls .env
   ```

2. **Controlla formato whitelist**:
   - Solo chiavi consentite vengono salvate
   - Credenziali DB (`DB_USER_*`, `DB_PASS_*`) non modificabili da UI

3. **Backup .env prima di modifiche**:
   ```powershell
   Copy-Item .env .env.backup
   ```

#### Problema: Email sending failures

**Errore**:
```
SMTPAuthenticationError: Authentication failed
```

**Soluzioni**:

1. **Verifica SMTP config in .env**:
   ```env
   smtp_host=smtp.gmail.com
   smtp_port=587
   smtp_user=your_email@gmail.com
   smtp_password=your_app_password
   smtp_from=noreply@company.com
   ```

2. **Test SMTP manuale**:
   ```powershell
   # Da UI: Impostazioni → Test Email
   # Oppure API:
   Invoke-RestMethod -Method POST -Uri 'http://localhost:8000/api/reports/daily/send?date=2026-02-05'
   ```

3. **Usa App Password** (Gmail):
   - Abilita 2FA su account Gmail
   - Genera App Password dedicata

#### Problema: Report template rendering issues

**Errore**:
```
TemplateError: Failed to render daily report
```

**Soluzioni**:

1. **Verifica template in .env**:
   ```env
   DAILY_REPORT_SUBJECT=Report schedulazioni PSTT
   DAILY_REPORT_TAIL_LINES=50
   ```

2. **Test anteprima report**:
   ```powershell
   Start-Process 'http://localhost:8000/api/reports/daily?date=2026-02-05'
   ```

3. **Controlla storico schedulazioni**:
   ```powershell
   Get-Content exports\scheduler_history.json
   ```

---

### ❌ Errori Porta di Rete

#### Problema: `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`

**Causa**: La porta 8000 è già in uso da un altro processo.

**Soluzioni**:

1. **Cambia porta temporaneamente**:
   ```bash
   $env:PORT=8001; .venv\Scripts\python.exe main.py
   ```

2. **Configura porta nel file .env**:
   ```env
   PORT=8001
   ```

3. **Trova e termina il processo**:
   ```powershell
   Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
   Stop-Process -Id [PID_DEL_PROCESSO]
   ```

---

### ❌ Errori Import Python

#### Problema: `ModuleNotFoundError: No module named 'app'`

**Causa**: Virtual environment non attivato o path di lavoro scorretto.

**Soluzioni**:

1. **Verifica virtual environment**:
   ```bash
   .venv\Scripts\python.exe --version  # Deve mostrare Python 3.11
   ```

2. **Verifica directory di lavoro**:
   ```bash
   cd C:\app\PSTT_Tool
   ```

3. **Reinstalla dipendenze se necessario**:
   ```bash
   .venv\Scripts\pip.exe install -r requirements.txt
   ```

---

### ❌ Errori Parametri Lista Query

#### Problema: Parametro lista non viene trasformato

**Errore**: Query con clausola `IN` fallisce con messaggio "invalid identifier" o "too many values"

**Esempio query che fallisce**:
```sql
define BARCODE = '123,456,789'
SELECT * FROM table WHERE barcode IN (&BARCODE)
```

**Cause**:
- Il nome del parametro NON contiene le keywords richieste: `LIST`, `BARCODES`, `CODES`, `IDS`
- Il sistema rileva automaticamente solo parametri con naming pattern specifico

**Soluzioni**:

1. **Rinomina parametro** con keyword riconosciuta:
   ```sql
   define BARCODE_LIST = '123,456,789'
   SELECT * FROM table WHERE barcode IN (&BARCODE_LIST)
   ```

2. **Pattern riconosciuti (case-insensitive)**:
   - `BARCODE_LIST` ✅
   - `BARCODES` ✅
   - `CODES` ✅
   - `IDS` ✅
   - `barcode_list` ✅ (minuscolo ok)
   - `BARCODE` ❌ (non riconosciuto)
   - `CODE` ❌ (non riconosciuto)

#### Problema: Lista oltre 1000 elementi

**Sintomi**:
- Contatore UI mostra numero rosso (es. 1523/1000)
- Bordo textarea diventa rosso
- Blocco esecuzione query

**Causa**: Limite tecnico 1000 elementi per prestazioni e sicurezza Oracle

**Soluzioni**:

1. **Ridurre lista** sotto 1000 elementi:
   - Filtra elementi duplicati
   - Suddividi query in batch multipli

2. **Usare tabella temporanea** per liste molto grandi:
   ```sql
   -- Step 1: popola tabella temp
   CREATE GLOBAL TEMPORARY TABLE temp_barcodes (barcode VARCHAR2(50))
   ON COMMIT DELETE ROWS;
   
   INSERT INTO temp_barcodes VALUES ('123');
   INSERT INTO temp_barcodes VALUES ('456');
   -- ... fino a N elementi
   
   -- Step 2: JOIN con tabella temp
   SELECT t.* 
   FROM target_table t
   JOIN temp_barcodes tb ON t.barcode = tb.barcode;
   ```

3. **Backend auto-truncation**: se submit forzato, backend tronca automaticamente a 1000 con warning nel log

#### Problema: Formato input non riconosciuto

**Esempi formati supportati** (tutti validi):
```
# Virgola
123,456,789

# Newline (CR+LF o LF)
123
456
789

# Già formattato
'123','456','789'

# Doppi apici
"123","456","789"

# Misto (virgola + newline + spazi)
123, 456
789 012
```

**Normalizzazione automatica**: tutti i formati vengono convertiti in `'123','456','789'` per SQL

**Caratteri speciali**:
- Apici singoli: rimossi automaticamente durante preprocessing
- Doppi apici: rimossi automaticamente
- Spazi extra: ignorati
- Valori alfanumerici: supportati (es. `ABC123,XYZ789`)

#### Problema: Parametro lista vuoto causa errore SQL

**Sintomo**: Query fallisce con `WHERE barcode IN ()`

**Causa**: Parametro lista valorizzato a stringa vuota o solo spazi

**Soluzioni**:

1. **Validazione frontend**: textarea richiesta mostra bordo rosso se vuota

2. **Fallback backend**: parametro vuoto restituisce `''` invece di nulla

3. **SQL robusto** con NVL/COALESCE:
   ```sql
   WHERE (&BARCODE_LIST IS NOT NULL AND barcode IN (&BARCODE_LIST))
      OR &BARCODE_LIST IS NULL
   ```

### ❌ Errori Query SQL

#### Problema: Query con parametri Oracle non funzionano

**Diagnostica**: Controlla i log sulla console per dettagli specifici:
- Parametri mancanti
- Sintassi SQL non valida
- Connessione database non disponibile

**Debug**:
```sql
-- Verifica che i parametri siano definiti correttamente
define DATAINIZIO='17/06/2022'   --Obbligatorio
define DATAFINE='17/06/2025'     --Opzionale

-- Verifica che siano utilizzati nella query
WHERE data >= TO_DATE('&DATAINIZIO', 'dd/mm/yyyy')
AND data < TO_DATE('&DATAFINE', 'dd/mm/yyyy')
```

---

### 🔧 Diagnostic Commands Completi

#### Test Configurazione Base
```powershell
# Test settings
.venv\Scripts\python.exe -c "from app.core.config import get_settings; print('✅ Config OK')"

# Test connessioni DB
.venv\Scripts\python.exe -c "from app.services.connection_service import ConnectionService; cs = ConnectionService(); print(f'✅ {len(cs.get_connections())} connessioni DB caricate')"

# Test query
.venv\Scripts\python.exe -c "from app.services.query_service import QueryService; qs = QueryService(); print(f'✅ {len(qs.get_queries())} query trovate')"
```

#### Health Checks API (con app in esecuzione)

```powershell
# Health check generale
Invoke-RestMethod -Uri 'http://localhost:8000/health'

# Health check Kafka
Invoke-RestMethod -Uri 'http://localhost:8000/api/kafka/health'

# Metriche scheduler
Invoke-RestMethod -Uri 'http://localhost:8000/api/scheduler/metrics'

# Metriche Kafka summary
Invoke-RestMethod -Uri 'http://localhost:8000/api/kafka/metrics/summary'
```

#### Test Connessioni Specifiche

```powershell
# Test connessione database
$body = @{ connection_name = 'A00-CDG-Collaudo' } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri 'http://localhost:8000/api/connections/test' -ContentType 'application/json' -Body $body

# Test connessione Kafka
$kafkaBody = @{ 
    connection_name = 'kafka-prod'
    bootstrap_servers = @('kafka1.prod:9093')
    security_protocol = 'SASL_SSL'
} | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri 'http://localhost:8000/api/kafka/test' -ContentType 'application/json' -Body $kafkaBody
```

#### Diagnostica Servizio Windows

```powershell
# Tool diagnostico completo
.\tools\diagnose_restart.ps1

# Status servizio
Get-Service PSTT_Tool | Format-List *

# Verifica NSSM
nssm status PSTT_Tool
nssm get PSTT_Tool AppDirectory
nssm get PSTT_Tool AppExit

# Log servizio
Get-Content logs\service_stdout.log -Tail 50
Get-Content logs\service_stderr.log -Tail 50
```

#### Analisi Log Avanzata

```powershell
# Errori recenti
Get-Content logs\errors.log -Tail 50

# Solo errori Kafka
Get-Content logs\app.log | Select-String "kafka" | Select-Object -Last 20

# Solo errori scheduler
Get-Content logs\scheduler.log -Tail 100

# Cerca errori specifici
Get-Content logs\app.log | Select-String "timeout|error|failed" -Context 2
```

#### Verifica Metriche e Storico

```powershell
# Storico schedulazioni (ultimi 10)
Get-Content exports\scheduler_history.json | ConvertFrom-Json | Select-Object -Last 10 | Format-Table query, status, duration_sec

# Metriche Kafka
Get-Content exports\kafka_metrics.json | ConvertFrom-Json | Select-Object -ExpandProperty summary

# Schedulazioni attive
Invoke-RestMethod -Uri 'http://localhost:8000/api/scheduler/scheduling' | Select-Object -ExpandProperty schedulings
```

#### Performance Monitoring

```powershell
# Kafka benchmark
python tools\kafka_benchmark.py --messages 1000 --mode batch

# Test throughput
python tools\kafka_benchmark.py --mode mixed --duration 60

# Statistiche sistema
Invoke-RestMethod -Uri 'http://localhost:8000/api/monitoring/stats'
```

---

### 📋 Log Files

I log sono salvati in `logs/`:
- **`app.log`**: Log generale dell'applicazione
- **`errors.log`**: Solo errori (utile per debug)
- **`scheduler.log`**: Log del sistema di scheduling

#### Visualizza log recenti:
```bash
Get-Content logs\errors.log -Tail 20
```

---

### 🚨 Modalità Debug

Per abilitare logging dettagliato, aggiungi nel file `.env`:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

Poi riavvia l'applicazione. Vedrai molto più dettaglio sui log.

---

### 📞 Supporto

Se i problemi persistono:

1. ✅ Controlla i log in `logs/errors.log`
2. ✅ Verifica la configurazione in `connections.json` e `.env`
3. ✅ Testa la connettività database con gli endpoint `/api/connections/test`
4. ✅ Usa la modalità debug per maggiori dettagli

Tutti gli errori sono ora visibili sia sulla console che nei file di log per un debugging più efficace.
