# Testing e Demo PSTT Tool

## 🧪 Modalità Test

Per testare l'applicazione senza connessioni database reali:

### 1. Configura Test Mode

Crea un file `.env.test`:

```env
# Configurazione di test
DEBUG=true
LOG_LEVEL=DEBUG
PORT=8001

# Credenziali di test (non funzionanti)
DB_USER_A00-CDG-Collaudo=test_user
DB_PASS_A00-CDG-Collaudo=test_pass
DB_USER_A01-BOSC-Collaudo=test_user
DB_PASS_A01-BOSC-Collaudo=test_pass
DB_USER_A03-TT2_UFFICIO=test_user
DB_PASS_A03-TT2_UFFICIO=test_pass
DB_USER_B00-CDG-Certificazione=test_user
DB_PASS_B00-CDG-Certificazione=test_pass
DB_USER_C00-CDG-Produzione=test_user
DB_PASS_C00-CDG-Produzione=test_pass
```

### 2. Test Senza Database

L'applicazione funziona anche senza connessioni database attive:

- ✅ **Interfaccia Web**: Completamente funzionale
- ✅ **Lista Query**: Mostra tutte le query SQL disponibili
- ✅ **Form Parametri**: Genera dinamicamente i campi
- ✅ **Parsing Query**: Estrae parametri correttamente
- ❌ **Esecuzione Query**: Fallirà ma mostrerà errori informativi

### 3. Demo delle Funzionalità

#### Test Parsing Query
```bash
# Testa il parsing di una query specifica
.venv\Scripts\python.exe -c "
from app.services.query_service import QueryService
qs = QueryService()
query = qs.get_query('CDG-INF-001--Visualizza Legenza Eventi-Tracce.sql')
if query:
    print(f'Titolo: {query.title}')
    print(f'Parametri: {len(query.parameters)}')
    for p in query.parameters:
        print(f'  - {p.name}: {p.parameter_type} ({\"obbligatorio\" if p.required else \"opzionale\"})')
else:
    print('Query non trovata')
"
```

#### Test Connessioni (senza esecuzione)
```bash
# Testa il caricamento delle configurazioni
.venv\Scripts\python.exe -c "
from app.services.connection_service import ConnectionService
cs = ConnectionService()
connections = cs.get_connections()
print(f'Connessioni caricate: {len(connections)}')
for name, conn in connections.items():
    print(f'  - {name}: {conn.db_type} ({conn.environment})')
"
```

### 4. Simulazione Completa

Per una demo completa delle funzionalità:

1. **Avvia l'applicazione**:
   ```bash
   $env:PORT=8001; .venv\Scripts\python.exe main.py
   ```

2. **Apri l'interfaccia**: http://127.0.0.1:8001

3. **Test workflow**:
   - Seleziona una connessione dal dropdown
   - Scegli una query dalla lista
   - Compila i parametri nel form
   - Prova ad eseguire (mostrerà errore di connessione ma tutto il resto funziona)

### 5. Errori Previsti in Modalità Demo

Gli seguenti errori sono **normali** in modalità demo:

```
❌ DPY-6005: cannot connect to database
❌ [WinError 10060] Impossibile stabilire la connessione
❌ Timeout di connessione
```

Questi indicano che:
- ✅ Il parsing delle query funziona
- ✅ La sostituzione parametri funziona  
- ✅ La generazione SQL funziona
- ❌ Solo la connessione database fallisce (normale senza database reali)

### 6. Cosa Osservare Durante i Test

#### Console Output
```
✅ Configurazioni caricate
✅ ConnectionService inizializzato  
✅ Query SQL trovate e parsate
✅ Parametri estratti correttamente
✅ Server web attivo
❌ Errori connessione database (previsti)
```

#### Web Interface
- ✅ Interfaccia carica correttamente
- ✅ Lista query popolata
- ✅ Dropdown connessioni funzionante
- ✅ Form parametri generato dinamicamente
- ✅ Gestione errori user-friendly

### 7. Performance Test

L'applicazione dovrebbe:
- Avviarsi in < 5 secondi
- Caricare l'interfaccia in < 2 secondi
- Parsare tutte le query in < 1 secondo
- Rispondere alle API in < 100ms (eccetto esecuzione query)

---

## 🧭 Suite Test Automatizzati (pytest)

Il progetto include una suite completa di **205 test** con coverage del 76%.

### 📊 Statistiche Test Suite (v1.1.9)

- **Test Totali**: 205 test
- **Coverage**: 76% overall
- **Breakdown per modulo**:
  - Kafka: 111 test (service, metrics, API, scheduler integration)
  - Scheduler: 45 test (retry, timeout, export multi-formato)
  - System: 18 test (restart, service management, hot restart NSSM)
  - API: 31 test (endpoints REST, validazione)

### 🚀 Esecuzione Test Completa

```powershell
# Esegui tutti i test
python -m pytest

# Run compatto (solo risultato)
python -m pytest -q

# Run verboso (con dettagli)
python -m pytest -v

# Test con coverage report
python -m pytest --cov=app --cov-report=html

# Apri report HTML
Start-Process tests/htmlcov/index.html
```

### 🎯 Test per Modulo Specifico

```powershell
# Test Kafka (111 test)
python -m pytest tests/test_kafka_*.py -v

# Test Scheduler (45 test)
python -m pytest tests/test_scheduler*.py -v

# Test API (40 test)
python -m pytest tests/test_api*.py -v

# Test Integrazione
python -m pytest tests/integration/ -v
```

### 🔍 Test Selettivi

```powershell
# Solo test che contengono "retry"
python -m pytest -k "retry" -v

# Solo test Kafka batch
python -m pytest -k "kafka and batch" -v

# Escludi test lenti
python -m pytest -m "not slow" -q

# Ferma al primo fallimento
python -m pytest -x -q
```

### 📈 Test Coverage Dettagliato

```powershell
# Coverage solo per modulo specifico
python -m pytest --cov=app.services.kafka_service --cov-report=term-missing

# Coverage con soglia minima
python -m pytest --cov=app --cov-fail-under=75

# Report XML per CI
python -m pytest --cov=app --cov-report=xml
```

### 🧪 Test per Funzionalità Chiave

#### Test Kafka Integration
```powershell
# Test connessione e publishing
python -m pytest tests/test_kafka_service.py::test_send_message -v
python -m pytest tests/test_kafka_service.py::test_send_batch -v

# Test metriche e monitoring
python -m pytest tests/test_kafka_metrics.py -v

# Test performance (>100 msg/sec)
python -m pytest tests/test_kafka_performance.py -v
```

#### Test Scheduler Avanzato
```powershell
# Test retry automatico
python -m pytest tests/test_scheduler_service.py::test_retry_on_timeout -v

# Test export multi-formato
python -m pytest tests/test_scheduler_service.py::test_kafka_export -v

# Test cron normalization
python -m pytest tests/test_scheduler_api_crud.py::test_cron_normalization -v
```

#### Test UI e Frontend
```powershell
# Test API Log Viewer
python -m pytest tests/test_logs_api.py -v

# Test API Impostazioni
python -m pytest tests/test_settings_api.py -v

# Test API Report
python -m pytest tests/test_daily_report.py -v
```

### 🎨 Flag Pytest Utili

- **`-q` / `--quiet`**: Output compatto (utile per CI)
- **`-v` / `--verbose`**: Output dettagliato con nomi test
- **`-vv`**: Output molto dettagliato con assert details
- **`-x` / `--exitfirst`**: Ferma al primo fallimento
- **`-k EXPRESSION`**: Filtra test per nome
- **`-m MARKER`**: Filtra test per marker
- **`--lf` / `--last-failed`**: Riesegui solo test falliti
- **`--ff` / `--failed-first`**: Esegui prima test falliti

### 🔧 Best Practices Testing

1. **Pre-commit**: Esegui test rapidi
   ```powershell
   python -m pytest -q --lf
   ```

2. **Full run locale**: Con coverage
   ```powershell
   python -m pytest --cov=app --cov-report=html
   ```

3. **CI Pipeline**: Output compatto + coverage
   ```powershell
   python -m pytest -q --cov=app --cov-report=xml --cov-fail-under=75
   ```

4. **Debug test fallito**: Verbose + stop al primo errore
   ```powershell
   python -m pytest -vv -x
   ```

### 📝 Test Performance Benchmark

```powershell
# Benchmark Kafka (tools/kafka_benchmark.py)
python tools/kafka_benchmark.py --messages 1000 --mode batch

# Test mixed load (60 secondi)
python tools/kafka_benchmark.py --mode mixed --duration 60

# Test completo (single + batch + mixed)
python tools/kafka_benchmark.py --mode all
```


## 🔧 Troubleshooting Demo

### Problema: "Nessuna query trovata"
**Soluzione**: Verifica che i file .sql siano nella directory `Query/`

### Problema: "Errori di encoding"
**Soluzione**: ✅ Risolto automaticamente con multi-encoding support

### Problema: "Porta già in uso"
**Soluzione**: Cambia porta con `$env:PORT=8002`

### Problema: "Import errors"
**Soluzione**: Verifica che il virtual environment sia attivo

---

## 📊 Metriche Sistema (v1.1.7)

Dopo il test, dovresti vedere:

```
📁 Query SQL processate: ~30+ file
🔌 Connessioni configurate: 5+ database
🔌 Connessioni Kafka: Multi-cluster support
⚙️  Parametri estratti: ~50+ totali
📝 Log entries: ~200-500 per sessione
🌐 API endpoints REST: 50+ attivi
📊 Dashboard UI: 5 pagine (Home, Scheduler, Kafka, Logs, Settings)
✅ Test automatizzati: 201 test (76% coverage)
🔄 Scheduler jobs: Supporto retry automatico
📧 Email reports: Report giornalieri configurabili
⚡ Kafka throughput: >100 msg/sec
```

### 🎯 Test Funzionalità Principali

**✅ Core Features**
- Multi-database support (Oracle, PostgreSQL, SQL Server)
- Query parametrizzate con parsing automatico
- Export multi-formato (Excel, CSV)
- Filtri e ordinamento risultati

**✅ Scheduling Avanzato**
- Schedulazioni cron e interval
- Export automatico (filesystem, email, Kafka)
- Retry automatico su errori
- Timeout configurabili (query e scrittura)

**✅ Kafka Integration**
- Multi-cluster support
- Publishing batch con retry
- Metriche real-time (throughput, latency, success rate)
- Dashboard monitoring

**✅ Monitoring & Operations**
- Log Viewer con file compressi
- Health check sistema
- Impostazioni configurabili da UI
- Report giornalieri email
- Service restart da UI

Questo dimostra che l'infrastruttura è completa, funzionante e production-ready!
