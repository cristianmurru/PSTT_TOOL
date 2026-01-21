# Piano di Integrazione Kafka per PSTT Tool

**Documento di Progettazione**  
**Data:** 17 Gennaio 2026  
**Versione:** 1.0  
**Autore:** GitHub Copilot

---

## 📋 Indice

1. [Obiettivo](#obiettivo)
2. [Contesto e Vincoli](#contesto-e-vincoli)
3. [Analisi dell'Esistente](#analisi-dellesistente)
4. [Architettura Proposta](#architettura-proposta)
5. [Layout del Progetto](#layout-del-progetto)
6. [Piano di Implementazione](#piano-di-implementazione)
7. [Configurazione](#configurazione)
8. [Monitoraggio e Metriche](#monitoraggio-e-metriche)
9. [Test Strategy](#test-strategy)
10. [Stima Tempi](#stima-tempi)
11. [Rischi e Mitigazioni](#rischi-e-mitigazioni)

---

## 🎯 Obiettivo

Implementare un sistema per:
- Estrarre dati da database Oracle CDG (e successivamente SQL Server e PostgreSQL)
- Trasformare i dati in formato JSON strutturato
- Pubblicare i messaggi su topic Kafka con cadenza giornaliera
- Gestire 20.000 messaggi/giorno inizialmente, scalabile fino a 200.000/giorno
- Garantire robustezza con retry automatici e monitoraggio

---

## 🔍 Contesto e Vincoli

### Contesto Esistente

Il progetto **PSTT Tool** dispone già di:

✅ **Infrastruttura Database**
- Supporto multi-database (Oracle, PostgreSQL, SQL Server)
- Connection pooling con SQLAlchemy
- Query service con parsing parametri

✅ **Sistema di Scheduling**
- APScheduler con AsyncIOExecutor
- Esecuzione parallela di job
- Configurazione via JSON e UI

✅ **Export e Rendering**
- Supporto Excel/CSV
- Template engine per nomi file dinamici
- Gestione storico esecuzioni

✅ **Monitoring**
- Sistema metriche con statistiche (avg, p90, p99)
- Health check endpoints
- Logging strutturato con Loguru

### Vincoli Operativi

🔒 **Tecnologici**
- Soluzioni freeware/opensource
- Compatibilità Python 3.11
- Nessuna regressione sul codice esistente
- Deployment come Windows Service (NSSM)

🔒 **Funzionali**
- Robustezza: retry automatici, idempotenza
- Scalabilità: da 20K a 200K msg/giorno
- Integrazione graduale e testabile
- Zero downtime durante il rollout

🔒 **Operativi**
- Configurazione centralizzata (connections.json + .env)
- Monitoraggio tramite metriche esistenti
- Log strutturati per troubleshooting
- Compatibilità con sistema scheduling esistente

---

## 🏗️ Analisi dell'Esistente

### Struttura Corrente

```
PSTT_Tool/
├── app/
│   ├── models/              # Modelli Pydantic
│   │   ├── queries.py
│   │   ├── scheduling.py
│   │   └── ...
│   ├── services/            # Business logic
│   │   ├── connection_service.py
│   │   ├── query_service.py
│   │   ├── scheduler_service.py
│   │   └── daily_report_service.py
│   ├── api/                 # REST endpoints
│   │   ├── queries.py
│   │   ├── scheduler.py
│   │   └── ...
│   └── core/
│       └── config.py        # Configurazione centralizzata
├── connections.json         # Config connessioni DB
├── requirements.txt         # Dipendenze Python
└── exports/                 # Output schedulazioni
```

### Punti di Integrazione Identificati

1. **SchedulerService** (`app/services/scheduler_service.py`)
   - Già gestisce esecuzioni periodiche
   - Supporta retry e timeout configurabili
   - Salva history in JSON

2. **QueryService** (`app/services/query_service.py`)
   - Esecuzione query parametrizzate
   - Restituisce risultati come dizionari Python
   - Gestisce multi-step SQL

3. **Config System** (`app/core/config.py`)
   - Gestione variabili ambiente
   - Configurazione database esistente
   - Estendibile per Kafka config

4. **Monitoring** (metriche esistenti)
   - Sistema già traccia durate, errori, retry
   - Facilmente estendibile per metriche Kafka

---

## 🎨 Architettura Proposta

### Diagramma Architetturale

```
┌─────────────────────────────────────────────────────────────────┐
│                        PSTT Tool Core                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │  Scheduler   │─────▶│ Query Service│─────▶│  Connection  │  │
│  │   Service    │      │              │      │   Service    │  │
│  └──────┬───────┘      └──────────────┘      └──────┬───────┘  │
│         │                                             │          │
│         │ triggers                              executes        │
│         │                                             │          │
│  ┌──────▼──────────────────────────────────────────▼────────┐  │
│  │           Kafka Export Job (NEW)                          │  │
│  │                                                            │  │
│  │  1. Execute Query → ResultSet                             │  │
│  │  2. Transform to JSON Messages                            │  │
│  │  3. Batch Messages (configurable size)                    │  │
│  │  4. Publish to Kafka Topic (with retry)                   │  │
│  │  5. Update Metrics & History                              │  │
│  └───────────────────────────┬────────────────────────────────┘  │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Kafka Producer      │
                    │   (kafka-python-ng)   │
                    └──────────┬────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Kafka Cluster      │
                    │   (Topic: pstt-data) │
                    └──────────────────────┘
```

### Componenti Nuovi

#### 1. **KafkaService** (`app/services/kafka_service.py`)

Responsabilità:
- Gestione producer Kafka con connection pooling
- Pubblicazione messaggi singoli o batch
- Retry automatico con backoff esponenziale
- Serializzazione JSON con gestione date/timestamp
- Metriche di pubblicazione (latenza, throughput, errori)

Interfaccia:
```python
class KafkaService:
    async def send_message(topic: str, key: str, value: dict) -> bool
    async def send_batch(topic: str, messages: List[Tuple[str, dict]]) -> BatchResult
    async def health_check() -> bool
    def get_metrics() -> KafkaMetrics
```

#### 2. **KafkaExportJob** (nuovo tipo di job in SchedulerService)

Responsabilità:
- Esecuzione query configurata
- Trasformazione risultati in messaggi JSON
- Batching messaggi (configurabile: es. 100 msg/batch)
- Invio a Kafka con gestione errori
- Logging dettagliato per troubleshooting

Flusso:
```
1. Trigger schedulazione (es. 02:00 AM)
2. Execute query con parametri (es. date=yesterday)
3. Fetch risultati in chunks (per gestire grandi volumi)
4. Per ogni chunk:
   a. Transform row → JSON message
   b. Accumula in batch
   c. Send batch to Kafka
   d. Log success/failure
5. Update metrics e history
```

#### 3. **KafkaConfig** (estensione `app/core/config.py`)

Nuove configurazioni:
```python
# Kafka Connection
KAFKA_BOOTSTRAP_SERVERS: str
KAFKA_SECURITY_PROTOCOL: str (PLAINTEXT/SSL/SASL_SSL)
KAFKA_SASL_MECHANISM: Optional[str]
KAFKA_SASL_USERNAME: Optional[str]
KAFKA_SASL_PASSWORD: Optional[str]

# Producer Settings
KAFKA_BATCH_SIZE: int = 16384  # bytes
KAFKA_LINGER_MS: int = 10
KAFKA_COMPRESSION_TYPE: str = "snappy"
KAFKA_MAX_REQUEST_SIZE: int = 1048576  # 1MB
KAFKA_REQUEST_TIMEOUT_MS: int = 30000

# Application Settings
KAFKA_DEFAULT_TOPIC: str = "pstt-data"
KAFKA_MESSAGE_BATCH_SIZE: int = 100  # messaggi per batch
KAFKA_ENABLE_IDEMPOTENCE: bool = True
KAFKA_RETRY_BACKOFF_MS: int = 100
KAFKA_MAX_IN_FLIGHT_REQUESTS: int = 5
```

#### 4. **Modelli Dati** (estensione `app/models/`)

Nuovi modelli Pydantic:

```python
# app/models/kafka.py

class KafkaConnectionConfig(BaseModel):
    bootstrap_servers: str
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None
    # ... altri parametri

class KafkaExportConfig(BaseModel):
    """Configurazione per export Kafka in scheduling"""
    enabled: bool = False
    topic: str
    message_key_field: str  # Campo da usare come key (es. "barcode")
    batch_size: int = 100
    include_metadata: bool = True  # Aggiunge timestamp, source, etc.

class KafkaMetrics(BaseModel):
    messages_sent: int
    messages_failed: int
    bytes_sent: int
    avg_latency_ms: float
    last_error: Optional[str]
    last_success_timestamp: Optional[datetime]
```

#### 5. **API Endpoints** (estensione `app/api/`)

Nuovi endpoint per gestione Kafka:

```python
# app/api/kafka.py

GET  /api/kafka/health           # Health check producer Kafka
GET  /api/kafka/topics           # Lista topic disponibili
GET  /api/kafka/metrics          # Metriche pubblicazione
POST /api/kafka/test             # Test invio messaggio
POST /api/kafka/send             # Invio manuale messaggio (debug)
```

Estensione endpoint scheduling:

```python
# app/api/scheduler.py (existing)

# Aggiunta campo kafka_config a SchedulingItem
POST /api/scheduler/scheduling
{
  "name": "Export CDG to Kafka",
  "query": "CDG-KAFKA-001--SelezioneTracceGiornaliere.sql",
  "connection": "A00-CDG-Collaudo",
  "cron": "0 2 * * *",
  "export_format": "kafka",  # NEW
  "kafka_config": {           # NEW
    "enabled": true,
    "topic": "pstt-traces",
    "message_key_field": "barcode",
    "batch_size": 100
  }
}
```

---

## 📂 Layout del Progetto

### File Nuovi

```
PSTT_Tool/
├── app/
│   ├── models/
│   │   └── kafka.py                       # [NEW] Modelli Kafka
│   ├── services/
│   │   └── kafka_service.py               # [NEW] Logica Kafka
│   ├── api/
│   │   └── kafka.py                       # [NEW] Endpoints Kafka
│   └── frontend/
│       └── kafka_dashboard.html           # [NEW] UI monitoring Kafka
├── Query/
│   ├── CDG-KAFKA-001--SelezioneTracceGiornaliere.sql  # [NEW] Query esempio
│   └── ...
├── tests/
│   ├── test_kafka_service.py              # [NEW] Test unitari
│   ├── test_kafka_integration.py          # [NEW] Test integrazione
│   └── ...
├── docs/
│   └── KAFKA_SETUP.md                     # [NEW] Guida setup Kafka
├── exports/
│   └── kafka_metrics.json                 # [NEW] Metriche persistite
├── requirements.txt                        # [MODIFIED] Aggiunta kafka-python-ng
└── connections.json                        # [MODIFIED] Aggiunta sezione Kafka
```

### Modifiche a File Esistenti

```
[MODIFIED] app/core/config.py
  └─ Aggiunta KafkaConfig e caricamento da .env

[MODIFIED] app/services/scheduler_service.py
  └─ Supporto export_format="kafka"
  └─ Integrazione KafkaExportJob

[MODIFIED] app/models/scheduling.py
  └─ Aggiunta campo kafka_config in SchedulingItem

[MODIFIED] requirements.txt
  └─ kafka-python-ng==2.2.2
  └─ aiokafka==0.10.0 (alternativa async)

[MODIFIED] .env
  └─ Variabili configurazione Kafka

[MODIFIED] connections.json (opzionale)
  └─ Sezione "kafka_connections" per gestire multi-cluster
```

---

## 📋 Piano di Implementazione

### Principi Guida

✅ **Incrementale**: Ogni step è funzionale e testabile in isolamento  
✅ **Non-breaking**: Zero impatto su funzionalità esistenti  
✅ **Rollback-safe**: Ogni step può essere annullato senza danni  
✅ **Test-driven**: Test automatizzati prima del deploy

---

### **STEP 1: Setup Dipendenze e Configurazione**

#### Obiettivi
- Aggiungere dipendenze Kafka a requirements.txt
- Estendere configurazione per supportare Kafka
- Creare modelli dati Pydantic per Kafka
- Nessun impatto su codice esistente

#### Task Dettagliati

1.1 **Aggiornare requirements.txt**
```bash
# Kafka Client (libreria ufficiale, fork mantenuto)
kafka-python-ng==2.2.2    # Producer/Consumer sincrono

# Alternative async (da valutare)
# aiokafka==0.10.0        # Producer/Consumer asincrono (FastAPI-friendly)

# Supporto
confluent-kafka==2.3.0    # Client Confluent (C-based, più performante)
```

1.2 **Creare `app/models/kafka.py`**
- Modelli Pydantic per configurazione
- Validazione parametri Kafka
- Type hints completi

1.3 **Estendere `app/core/config.py`**
- Classe `KafkaSettings` con validazione
- Caricamento da `.env`
- Default sicuri per sviluppo

1.4 **Aggiornare `.env.example`**
- Documentare tutte le variabili Kafka
- Esempi per diversi scenari (local, prod)

#### Deliverable
- ✅ Dipendenze installabili senza errori
- ✅ Configurazione leggibile da Settings
- ✅ Test: `test_kafka_config.py` (caricamento config, validazione)

#### Stima Pessimistica
**2 giorni** (16 ore)
- Ricerca best practice Kafka + Python: 4h
- Implementazione modelli e config: 6h
- Testing e documentazione: 4h
- Buffer imprevisti: 2h

---

### **STEP 2: Implementazione KafkaService Base**

#### Obiettivi
- Creare servizio per gestione producer Kafka
- Implementare connessione e health check
- Gestire serializzazione JSON custom (date, Decimal)
- Logging strutturato

#### Task Dettagliati

2.1 **Creare `app/services/kafka_service.py`**

Metodi chiave:
```python
class KafkaService:
    def __init__(self, config: KafkaSettings):
        """Inizializza producer con config"""
        
    async def connect(self) -> bool:
        """Stabilisce connessione a Kafka"""
        
    async def send_message(
        self, 
        topic: str, 
        key: str, 
        value: dict,
        headers: Optional[dict] = None
    ) -> bool:
        """Invia singolo messaggio"""
        
    async def health_check(self) -> dict:
        """Verifica connettività Kafka"""
        
    async def close(self):
        """Chiude connessione producer"""
```

2.2 **Serializzazione Custom**
- JSON encoder per `datetime`, `date`, `Decimal`
- Gestione NULL/None
- Encoding UTF-8

2.3 **Error Handling**
- Try/catch su operazioni Kafka
- Logging dettagliato errori
- Classificazione errori (retriable vs fatal)

2.4 **Logging**
```python
logger.info("[KAFKA] Connessione a {bootstrap_servers}")
logger.success("[KAFKA] Messaggio inviato: topic={topic}, key={key}")
logger.error("[KAFKA] Errore invio: {error}")
```

#### Deliverable
- ✅ KafkaService funzionante per invio singolo messaggio
- ✅ Health check testato
- ✅ Test: `test_kafka_service.py` (mock Kafka)

#### Stima Pessimistica
**3 giorni** (24 ore)
- Implementazione core service: 10h
- Gestione errori e retry: 6h
- Testing con mock: 6h
- Documentazione: 2h

---

### **STEP 3: Batch Publishing e Performance**

#### Obiettivi
- Implementare invio batch per performance
- Ottimizzare throughput per 20K+ msg/giorno
- Gestire backpressure e limiti Kafka

#### Task Dettagliati

3.1 **Metodo `send_batch`**
```python
async def send_batch(
    self,
    topic: str,
    messages: List[Tuple[str, dict]],  # [(key, value), ...]
    batch_size: int = 100
) -> BatchResult:
    """
    Invia batch di messaggi con retry automatico
    
    Returns:
        BatchResult(
            total=1000,
            succeeded=998,
            failed=2,
            errors=[...]
        )
    """
```

3.2 **Chunking Intelligente**
- Dividere batch grandi in sub-batch
- Rispettare `max_request_size` di Kafka
- Progress logging per batch lunghi

3.3 **Retry Logic**
- Retry esponenziale su errori retriable
- Max retry configurabile (default: 3)
- Backoff: 100ms, 200ms, 400ms

3.4 **Compressione**
- Abilitare Snappy compression (default)
- Misurare saving su payload reali
- Configurabile via settings

#### Deliverable
- ✅ Batch publishing testato con 1000+ messaggi
- ✅ Performance test: almeno 100 msg/sec
- ✅ Metriche: latenza media, p90, p99

#### Stima Pessimistica
**3 giorni** (24 ore)
- Implementazione batching: 8h
- Ottimizzazione performance: 8h
- Load testing: 6h
- Documentazione: 2h

---

### **STEP 4: Integrazione con SchedulerService**

#### Obiettivi
- Aggiungere supporto `export_format="kafka"` allo scheduler
- Implementare KafkaExportJob
- Mantenere compatibilità con export Excel/CSV esistenti

#### Task Dettagliati

4.1 **Estendere `app/models/scheduling.py`**
```python
class SchedulingItem(BaseModel):
    # ... campi esistenti ...
    export_format: str = "excel"  # Aggiungere: "kafka"
    kafka_config: Optional[KafkaExportConfig] = None
```

4.2 **Modificare `app/services/scheduler_service.py`**

Aggiungere metodo:
```python
async def _execute_kafka_job(
    self,
    scheduling: SchedulingItem,
    kafka_service: KafkaService
) -> dict:
    """
    1. Esegue query
    2. Trasforma risultati in messaggi JSON
    3. Invia a Kafka in batch
    4. Salva metriche
    """
    try:
        # Execute query
        results = await self.query_service.execute_query(...)
        
        # Transform to messages
        messages = []
        for row in results:
            key = row[kafka_config.message_key_field]
            value = {
                "data": row,
                "metadata": {
                    "source": scheduling.connection,
                    "query": scheduling.query,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            messages.append((key, value))
        
        # Send batch
        result = await kafka_service.send_batch(
            topic=kafka_config.topic,
            messages=messages,
            batch_size=kafka_config.batch_size
        )
        
        # Log metrics
        logger.info(f"[KAFKA_JOB] Inviati {result.succeeded}/{result.total}")
        
        return {
            "status": "success",
            "messages_sent": result.succeeded,
            "duration_ms": ...
        }
        
    except Exception as e:
        logger.error(f"[KAFKA_JOB] Errore: {e}")
        return {"status": "error", "error": str(e)}
```

4.3 **Routing Job Type**
```python
def _schedule_job(self, scheduling: SchedulingItem):
    if scheduling.export_format == "kafka":
        job_func = lambda: self._execute_kafka_job(scheduling)
    else:
        job_func = lambda: self._execute_export_job(scheduling)  # Existing
    
    self.scheduler.add_job(...)
```

4.4 **Gestione History**
- Salvare metriche Kafka in `scheduler_history.json`
- Distinguere job Kafka da export normali
- Tracciare: messaggi inviati, falliti, topic

#### Deliverable
- ✅ Job Kafka eseguibile da scheduler
- ✅ Compatibilità con job esistenti (no regressioni)
- ✅ Test: `test_kafka_scheduling.py`

#### Stima Pessimistica
**4 giorni** (32 ore)
- Estensione modelli e scheduler: 12h
- Implementazione job logic: 10h
- Testing integrazione: 8h
- Documentazione: 2h

---

### **STEP 5: API Endpoints e UI**

#### Obiettivi
- Esporre API per gestione Kafka
- Creare UI per configurazione e monitoring
- Integrare in dashboard esistente

#### Task Dettagliati

5.1 **Creare `app/api/kafka.py`**

Endpoints:
```python
@router.get("/kafka/health")
async def kafka_health_check():
    """Verifica connessione Kafka"""
    
@router.get("/kafka/topics")
async def list_topics():
    """Lista topic disponibili"""
    
@router.get("/kafka/metrics")
async def get_kafka_metrics():
    """Metriche pubblicazione Kafka"""
    
@router.post("/kafka/test")
async def test_kafka_connection(config: KafkaConnectionConfig):
    """Test connessione Kafka (simile a test DB)"""
    
@router.post("/kafka/send")
async def send_test_message(topic: str, message: dict):
    """Invio manuale messaggio (debug/test)"""
```

5.2 **Estendere `app/api/scheduler.py`**
- Validazione `kafka_config` in POST/PUT scheduling
- Documentazione OpenAPI completa
- Esempi request/response

5.3 **Creare `app/frontend/kafka_dashboard.html`**

Sezioni:
- **Status**: Connessione Kafka (verde/rosso)
- **Metriche Live**: Messaggi inviati oggi, errori, latenza
- **Job Kafka**: Lista schedulazioni Kafka attive
- **Test Connection**: Form per testare connessione
- **Manual Send**: Form per invio messaggio test

5.4 **Integrare in navbar esistente**
- Aggiungere link "Kafka" in menu principale
- Badge con status (🟢 Connected / 🔴 Disconnected)

#### Deliverable
- ✅ API documentate su `/api/docs`
- ✅ UI funzionale e responsive
- ✅ Test: `test_kafka_api.py`

#### Stima Pessimistica
**4 giorni** (32 ore)
- Implementazione API: 12h
- Frontend UI: 12h
- Integrazione con dashboard esistente: 6h
- Documentazione: 2h

---

### **STEP 6: Monitoring e Metriche**

#### Obiettivi
- Estendere sistema metriche esistente per Kafka
- Dashboard per analisi performance
- Alert su errori critici

#### Task Dettagliati

6.1 **Estendere Metriche Scheduler**

Aggiungere a `scheduler_metrics.json`:
```json
{
  "kafka": {
    "total_messages_sent": 1234567,
    "total_messages_failed": 123,
    "success_rate": 99.99,
    "avg_latency_ms": 45,
    "p90_latency_ms": 120,
    "p99_latency_ms": 350,
    "by_topic": {
      "pstt-traces": {
        "messages_sent": 500000,
        "bytes_sent": 52428800,
        "last_send": "2026-01-17T10:30:00Z"
      }
    },
    "recent_errors": [
      {
        "timestamp": "2026-01-17T10:25:13Z",
        "error": "TimeoutError: Kafka broker not responding",
        "topic": "pstt-traces"
      }
    ]
  }
}
```

6.2 **Endpoint Metriche Aggregate**
```python
GET /api/kafka/metrics/summary
{
  "today": {
    "messages_sent": 18543,
    "errors": 2,
    "avg_latency_ms": 52
  },
  "last_7_days": {
    "messages_sent": 145230,
    "errors": 15,
    "avg_latency_ms": 48
  }
}
```

6.3 **Dashboard Grafici**
- Grafico: Messaggi inviati per giorno (ultimi 30 giorni)
- Grafico: Latenza media/p90/p99 per ora
- Tabella: Top errori per frequenza

6.4 **Alert Email** (opzionale)
- Inviare email su:
  - Tasso errori > 5%
  - Latenza p99 > 5 secondi
  - Producer disconnesso per > 5 minuti

#### Deliverable
- ✅ Metriche Kafka integrate in sistema esistente
- ✅ Dashboard grafici funzionante
- ✅ Test: `test_kafka_metrics.py`

#### Stima Pessimistica
**3 giorni** (24 ore)
- Estensione metriche: 8h
- Dashboard grafici: 10h
- Testing: 4h
- Documentazione: 2h

---

### **STEP 7: Testing Completo e Documentazione**

#### Obiettivi
- Test suite completa (unit, integration, e2e)
- Documentazione operativa
- Runbook per troubleshooting

#### Task Dettagliati

7.1 **Test Unitari**
- `test_kafka_service.py`: Mock Kafka producer
- `test_kafka_config.py`: Validazione configurazione
- `test_kafka_serialization.py`: JSON encoding custom

7.2 **Test Integrazione**
- `test_kafka_integration.py`: Kafka testcontainer
- `test_kafka_scheduling.py`: End-to-end job execution
- `test_kafka_retry.py`: Retry logic con errori simulati

7.3 **Test Performance**
- Benchmark: invio 10K messaggi
- Misurare throughput (msg/sec)
- Profiling memory usage

7.4 **Documentazione**

Creare `docs/KAFKA_SETUP.md`:
- **Prerequisiti**: Kafka cluster setup
- **Configurazione**: Variabili .env
- **Quick Start**: Primo job Kafka
- **Troubleshooting**: Errori comuni
- **Performance Tuning**: Best practice
- **Sicurezza**: SSL/SASL setup

7.5 **Runbook Operativo**
```markdown
# Runbook: Kafka Integration

## Scenario: Producer Disconnesso

Sintomo: Dashboard mostra 🔴 Disconnected

Diagnosi:
1. Verificare connettività rete: `telnet kafka-broker 9092`
2. Controllare log: `grep "KAFKA.*ERROR" logs/pstt_*.log`
3. Testare da API: POST /api/kafka/test

Soluzione:
- Se rete OK: verificare credenziali in .env
- Se timeout: verificare firewall/security groups
- Riavviare servizio: `manage_service.ps1 -action restart`

## Scenario: Alta Latenza (p99 > 5s)

Diagnosi:
1. Verificare load Kafka cluster
2. Controllare dimensione messaggi: GET /api/kafka/metrics
3. Verificare compressione abilitata

Soluzione:
- Ridurre `batch_size` in scheduling config
- Abilitare compressione: `KAFKA_COMPRESSION_TYPE=snappy`
- Aumentare `KAFKA_LINGER_MS` per batching migliore
```

#### Deliverable
- ✅ Coverage test > 80%
- ✅ Documentazione completa
- ✅ Runbook testato con scenari reali

#### Stima Pessimistica
**5 giorni** (40 ore)
- Test unitari: 12h
- Test integrazione: 12h
- Performance testing: 8h
- Documentazione: 6h
- Review e refinement: 2h

---

### **STEP 8: Deploy Produzione e Rollout Graduale**

#### Obiettivi
- Deploy sicuro in ambiente produzione
- Rollout graduale con monitoring
- Piano rollback in caso di problemi

#### Task Dettagliati

8.1 **Pre-Deploy Checklist**
- [ ] Tutti i test passano (unit + integration)
- [ ] Documentazione aggiornata
- [ ] Variabili .env configurate per produzione
- [ ] Backup configurazioni esistenti
- [ ] Piano rollback definito

8.2 **Deploy Fase 1: Infrastruttura** (Settimana 1)
- Installare dipendenze in produzione
- Configurare .env con credenziali Kafka prod
- Testare connettività Kafka da server
- Deploy codice senza attivare job

8.3 **Deploy Fase 2: Test in Produzione** (Settimana 2)
- Creare job test schedulato (es. 1 volta/ora, 100 messaggi)
- Monitorare per 1 settimana:
  - Metriche: latenza, errori, throughput
  - Log: cercare warning/errori
  - Risorse: CPU, memoria, network

8.4 **Deploy Fase 3: Rollout Graduale** (Settimana 3-4)
- Settimana 3: 1 job produzione (query più semplice)
- Settimana 4: Aggiungere job progressivamente
- Obiettivo finale: 20K+ messaggi/giorno

8.5 **Monitoring Post-Deploy**
- Daily check: Dashboard Kafka per 2 settimane
- Weekly review: Metriche aggregate
- Alert configurati e testati

8.6 **Piano Rollback**
```powershell
# In caso di problemi critici:

# 1. Disabilitare job Kafka
POST /api/scheduler/scheduling/{id}/disable

# 2. Verificare impatto su sistema esistente
GET /api/monitoring/health

# 3. Se necessario, rollback codice
git checkout <previous-tag>
.\manage_service.ps1 -action restart

# 4. Analisi root cause
# Analizzare log per identificare problema
# Fix e re-deploy quando ready
```

#### Deliverable
- ✅ Codice deployato in produzione
- ✅ Job test funzionante per 1 settimana
- ✅ Piano rollout completato
- ✅ Documentazione post-deploy

#### Stima Pessimistica
**2 settimane** (80 ore diluite su calendario)
- Setup infrastruttura: 8h
- Deploy e testing: 16h
- Monitoring (daily): 28h (2h/giorno * 14 giorni)
- Rollout graduale: 16h
- Documentazione finale: 8h
- Buffer imprevisti: 4h

---

## 🔧 Configurazione

### connections.json (Estensione)

Aggiungere sezione `kafka_connections`:

```json
{
  "default_environment": "collaudo",
  "connections": [
    // ... existing DB connections ...
  ],
  "kafka_connections": {
    "collaudo": {
      "name": "Kafka Collaudo",
      "bootstrap_servers": "kafka-collaudo.example.com:9092",
      "security_protocol": "SASL_SSL",
      "sasl_mechanism": "PLAIN",
      "default_topic": "pstt-collaudo"
    },
    "produzione": {
      "name": "Kafka Produzione",
      "bootstrap_servers": "kafka-prod.example.com:9093",
      "security_protocol": "SASL_SSL",
      "sasl_mechanism": "SCRAM-SHA-256",
      "default_topic": "pstt-traces"
    }
  }
}
```

### .env (Nuove Variabili)

```bash
# ========================================
# KAFKA CONFIGURATION
# ========================================

# Connection
KAFKA_BOOTSTRAP_SERVERS=kafka-collaudo.example.com:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=pstt-producer
KAFKA_SASL_PASSWORD=secure-password-here

# SSL (se necessario)
KAFKA_SSL_CAFILE=/path/to/ca-cert.pem
KAFKA_SSL_CERTFILE=/path/to/client-cert.pem
KAFKA_SSL_KEYFILE=/path/to/client-key.pem

# Producer Settings
KAFKA_COMPRESSION_TYPE=snappy
KAFKA_BATCH_SIZE=16384
KAFKA_LINGER_MS=10
KAFKA_MAX_REQUEST_SIZE=1048576
KAFKA_REQUEST_TIMEOUT_MS=30000
KAFKA_ENABLE_IDEMPOTENCE=true
KAFKA_RETRY_BACKOFF_MS=100

# Application
KAFKA_DEFAULT_TOPIC=pstt-traces
KAFKA_MESSAGE_BATCH_SIZE=100
KAFKA_MAX_RETRIES=3
KAFKA_HEALTH_CHECK_INTERVAL_SEC=60

# Logging
KAFKA_LOG_LEVEL=INFO
KAFKA_LOG_PAYLOAD=false  # Log completo payload (solo per debug)
```

### Query SQL Esempio

Creare `Query/CDG-KAFKA-001--SelezioneTracceGiornaliere.sql`:

```sql
-- Estrazione tracce giornaliere per Kafka
-- Query ottimizzata per export Kafka

define DATA='2026-01-17'  --Obbligatorio: Data estrazione (YYYY-MM-DD)

SELECT 
    BARCODE,
    TRKDATE,
    OPERATOR,
    MSGTYPE,
    CAUSAL,
    TEST_FLAG,
    PHASE_AT,
    ARRIVETIMESTAMP,
    STATUS,
    TRACK_OFFICE,
    MTF_MTFID,
    DATE_OTHER,
    CANALE,
    CUSTCODE,
    CUST_SPED,
    IDSPED
FROM EXPORT_TABLE
WHERE TRUNC(TRKDATE) = TO_DATE('&DATA', 'YYYY-MM-DD')
  AND TEST_FLAG = 'N'
ORDER BY ARRIVETIMESTAMP;
```

### Scheduling Configuration

Esempio configurazione job Kafka in UI:

```json
{
  "name": "Export CDG Tracce to Kafka",
  "query": "CDG-KAFKA-001--SelezioneTracceGiornaliere.sql",
  "connection": "A00-CDG-Collaudo",
  "scheduling_mode": "cron",
  "cron": "0 2 * * *",
  "enabled": true,
  "parameters": {
    "DATA": "{date-1}"
  },
  "export_format": "kafka",
  "kafka_config": {
    "enabled": true,
    "topic": "pstt-traces",
    "message_key_field": "BARCODE",
    "batch_size": 100,
    "include_metadata": true
  },
  "email_notification": {
    "on_success": false,
    "on_failure": true,
    "recipients": ["admin@example.com"]
  }
}
```

---

## 📊 Monitoraggio e Metriche

### Metriche Chiave da Tracciare

#### Performance
- **Throughput**: messaggi/secondo
- **Latenza**: media, p50, p90, p99
- **Bytes inviati**: totale e per topic
- **Success rate**: % messaggi inviati con successo

#### Affidabilità
- **Errori totali**: count e rate
- **Retry rate**: % messaggi che richiedono retry
- **Timeout rate**: % richieste in timeout
- **Connection uptime**: % tempo producer connesso

#### Business
- **Messaggi per job**: count per schedulazione
- **Tempo esecuzione job**: durata totale job Kafka
- **Record processati**: righe query → messaggi Kafka
- **Latenza end-to-end**: da trigger job a conferma Kafka

### Dashboard Metriche

```
┌─────────────────────────────────────────────────────────────┐
│  KAFKA METRICS DASHBOARD                        🟢 Connected │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📊 Today (17/01/2026)                                       │
│  ├─ Messages Sent:     18,543                                │
│  ├─ Success Rate:      99.98%                                │
│  ├─ Avg Latency:       52ms                                  │
│  └─ Errors:            2                                     │
│                                                               │
│  📈 Last 7 Days                                              │
│  ├─ Total Messages:    145,230                               │
│  ├─ Throughput:        ~20,747 msg/day                       │
│  ├─ p90 Latency:       120ms                                 │
│  └─ p99 Latency:       350ms                                 │
│                                                               │
│  🎯 Active Jobs                                              │
│  ├─ Export CDG Tracce      [Next: 02:00] Topic: pstt-traces │
│  ├─ Export BOSC Accessi    [Next: 03:00] Topic: pstt-access │
│  └─ Export TT2 Stampa      [Next: 04:00] Topic: pstt-print  │
│                                                               │
│  ⚠️  Recent Errors (Last 24h)                                │
│  ├─ 16/01 22:15 - TimeoutError on pstt-traces (retried OK)  │
│  └─ 17/01 08:30 - SerializationError: Invalid date format   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Alert Rules

Configurare alert per:

| Condizione | Threshold | Azione |
|------------|-----------|--------|
| Success Rate < 95% | 5 minuti consecutivi | Email admin + log ERROR |
| p99 Latency > 5000ms | 10 minuti | Email admin + warning |
| Producer Disconnected | 5 minuti | Email critico + SMS (opzionale) |
| Error Rate > 10% | 1 minuto | Email + disabilitare job |
| Memory Usage > 80% | 5 minuti | Warning + garbage collection |

---

## 🧪 Test Strategy

### Livelli di Test

#### 1. Unit Tests (Test Isolati)

**Target Coverage: > 90%**

File: `tests/test_kafka_service.py`
```python
def test_kafka_service_init():
    """Test inizializzazione service con config valida"""
    
def test_kafka_serialize_json():
    """Test serializzazione custom (datetime, Decimal)"""
    
def test_kafka_send_message_success():
    """Test invio messaggio con mock producer (success)"""
    
def test_kafka_send_message_failure():
    """Test gestione errore invio con retry"""
    
def test_kafka_batch_chunking():
    """Test splitting batch grandi in chunk"""
```

#### 2. Integration Tests (Con Kafka Reale)

**Ambiente: Testcontainer o Kafka dev**

File: `tests/test_kafka_integration.py`
```python
@pytest.fixture
async def kafka_testcontainer():
    """Setup Kafka container per test"""
    
async def test_e2e_send_receive():
    """Test end-to-end: produce + consume messaggio"""
    
async def test_batch_publishing():
    """Test invio batch 1000 messaggi"""
    
async def test_retry_on_network_error():
    """Test retry automatico con disconnessione simulata"""
    
async def test_idempotence():
    """Test messaggi duplicati non creano side-effects"""
```

#### 3. Performance Tests

File: `tests/test_kafka_performance.py`
```python
@pytest.mark.benchmark
async def test_throughput_10k_messages():
    """Benchmark: invio 10.000 messaggi, target < 60s"""
    
@pytest.mark.benchmark
async def test_latency_p99():
    """Misura p99 latency sotto load, target < 500ms"""
    
@pytest.mark.benchmark
async def test_memory_usage():
    """Verifica memory leak su 100K messaggi"""
```

#### 4. Regression Tests

File: `tests/test_kafka_regression.py`
```python
async def test_no_impact_on_existing_export():
    """Verifica export Excel/CSV funzionano come prima"""
    
async def test_scheduler_backward_compatibility():
    """Verifica job esistenti continuano a funzionare"""
    
async def test_api_endpoints_unchanged():
    """Verifica endpoint esistenti rispondono correttamente"""
```

### Test Automation

Configurare CI/CD (GitHub Actions / Azure DevOps):

```yaml
# .github/workflows/kafka-tests.yml
name: Kafka Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    services:
      kafka:
        image: confluentinc/cp-kafka:7.5.0
        ports:
          - 9092:9092
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run Kafka tests
        run: pytest tests/test_kafka_*.py -v
```

---

## ⏱️ Stima Tempi (Riepilogo)

### Timeline Complessiva

| Step | Descrizione | Stima Pessimistica | Giorni Lavorativi |
|------|-------------|-------------------|-------------------|
| 1 | Setup Dipendenze e Config | 16h | 2 giorni |
| 2 | KafkaService Base | 24h | 3 giorni |
| 3 | Batch Publishing | 24h | 3 giorni |
| 4 | Integrazione Scheduler | 32h | 4 giorni |
| 5 | API Endpoints e UI | 32h | 4 giorni |
| 6 | Monitoring e Metriche | 24h | 3 giorni |
| 7 | Testing e Documentazione | 40h | 5 giorni |
| 8 | Deploy e Rollout | 80h (diluite) | 10 giorni calendario |
| **TOTALE SVILUPPO** | | **272h** | **34 giorni lavorativi** |

### Gantt Chart (Semplificato)

```
Settimana 1-2:  ████████ Step 1-3 (Setup + Core Service + Batch)
Settimana 3-4:  ████████ Step 4-5 (Scheduler + API/UI)
Settimana 5:    ████     Step 6 (Monitoring)
Settimana 6-7:  ████████ Step 7 (Testing completo)
Settimana 8-10: ████████ Step 8 (Deploy graduale in produzione)
```

### Milestone

- **M1 (Settimana 2)**: KafkaService funzionante standalone ✅
- **M2 (Settimana 4)**: Integrazione scheduler completa ✅
- **M3 (Settimana 5)**: UI e API documentate ✅
- **M4 (Settimana 7)**: Test suite completa e passing ✅
- **M5 (Settimana 10)**: Produzione con 20K msg/giorno ✅

### Assunzioni

- Sviluppatore con esperienza Python/FastAPI: 1 FTE
- Kafka cluster già disponibile e configurato
- Nessun blocco per approvazioni/infrastruttura
- Review codice: max 1 giorno per step
- Buffer 20% per imprevisti già incluso

### Ottimizzazioni Possibili

Se timeline è critica, possibili riduzioni:

- **-5 giorni**: UI semplificata (solo API, niente dashboard grafico)
- **-3 giorni**: Testing ridotto (solo unit + smoke test)
- **-2 giorni**: Monitoring base (no alert, no grafici)

**Totale minimo realistico: ~24 giorni lavorativi (5 settimane)**

---

## ⚠️ Rischi e Mitigazioni

### Rischi Tecnici

#### 1. **Dipendenze Kafka Instabili**

**Rischio**: Libreria kafka-python-ng ha problemi/bug  
**Probabilità**: Media  
**Impatto**: Alto  
**Mitigazione**:
- Valutare alternative: `confluent-kafka`, `aiokafka`
- Test approfonditi in Step 2
- Piano B: wrapper astratto per cambiare client facilmente

#### 2. **Performance Non Adeguata**

**Rischio**: Non raggiungere 100 msg/sec (20K/giorno in 5 min)  
**Probabilità**: Bassa  
**Impatto**: Medio  
**Mitigazione**:
- Benchmark in Step 3 con dati reali
- Ottimizzazione batch size e compressione
- Kafka tuning: `batch.size`, `linger.ms`

#### 3. **Serializzazione Custom Fallisce**

**Rischio**: Tipi Oracle (CLOB, BLOB, custom) non serializzabili  
**Probabilità**: Media  
**Impatto**: Medio  
**Mitigazione**:
- Test con query reali in Step 2
- Fallback: conversione a string per tipi non gestiti
- Documentare limitazioni

#### 4. **Regressioni su Codice Esistente**

**Rischio**: Modifiche a scheduler rompono export Excel/CSV  
**Probabilità**: Bassa  
**Impatto**: Critico  
**Mitigazione**:
- Test regressione completi (Step 7)
- Branch separato per sviluppo
- Review attenta di modifiche a file esistenti
- Rollback plan documentato

### Rischi Operativi

#### 5. **Kafka Cluster Non Disponibile**

**Rischio**: Kafka down/irraggiungibile durante deploy  
**Probabilità**: Media  
**Impatto**: Alto  
**Mitigazione**:
- Health check robusto con retry
- Fallback: log errori ma non bloccare applicazione
- Alert immediato su disconnessione

#### 6. **Credenziali Kafka Non Disponibili**

**Rischio**: Ritardi per ottenere username/password produzione  
**Probabilità**: Alta (burocrazia)  
**Impatto**: Medio  
**Mitigazione**:
- Richiedere credenziali PRIMA di Step 1
- Test con Kafka locale/testcontainer
- Mockup per sviluppo

#### 7. **Throughput Sottostimato**

**Rischio**: In produzione servono 200K msg/giorno subito  
**Probabilità**: Bassa  
**Impatto**: Alto  
**Mitigazione**:
- Architettura scalabile (batch configurable)
- Benchmark con 200K in Step 3
- Piano scaling: aumentare batch size o worker paralleli

### Rischi di Progetto

#### 8. **Timeline Troppo Ottimistica**

**Rischio**: 34 giorni non sufficienti per deploy completo  
**Probabilità**: Media  
**Impatto**: Medio  
**Mitigazione**:
- Stime già pessimistiche (20% buffer)
- Priorità: Step 1-4 critical, Step 5-6 nice-to-have
- Possibile MVP: solo API senza UI (risparmio 4 giorni)

#### 9. **Requisiti Cambiano Durante Sviluppo**

**Rischio**: Nuovi vincoli/requirement non previsti  
**Probabilità**: Alta  
**Impatto**: Variabile  
**Mitigazione**:
- Documentare assunzioni iniziali
- Review milestone con stakeholder
- Architettura modulare permette modifiche

#### 10. **Mancanza Competenze Kafka nel Team**

**Rischio**: Learning curve Kafka rallenta sviluppo  
**Probabilità**: Media  
**Impatto**: Medio  
**Mitigazione**:
- Step 1 include ricerca e formazione
- Documentazione dettagliata inline
- Consulenza esterna se necessario (budget permettendo)

---

## 📚 Riferimenti e Risorse

### Documentazione Tecnica

- **Kafka Python Clients**:
  - [kafka-python-ng](https://github.com/wbarnha/kafka-python-ng) - Fork maintained
  - [aiokafka](https://aiokafka.readthedocs.io/) - Async Kafka client
  - [confluent-kafka-python](https://docs.confluent.io/kafka-clients/python/current/overview.html) - Official Confluent client

- **Kafka Best Practices**:
  - [Kafka Producer Performance](https://kafka.apache.org/documentation/#producerconfigs)
  - [Idempotent Producer](https://kafka.apache.org/documentation/#semantics)
  - [Compression Types](https://kafka.apache.org/documentation/#compression)

### Tool e Utility

- **Testing**:
  - [Testcontainers Python](https://testcontainers-python.readthedocs.io/) - Kafka container per test
  - [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) - Test async

- **Monitoring**:
  - [Kafka Lag Exporter](https://github.com/lightbend/kafka-lag-exporter) - Metriche consumer lag
  - [Prometheus Kafka Exporter](https://github.com/danielqsj/kafka_exporter) - Metriche Kafka

### Esempi Codice

Repository di riferimento con pattern simili:
- [FastAPI + Kafka Example](https://github.com/iwpnd/fastapi-kafka)
- [Python Kafka Producer Patterns](https://github.com/confluentinc/examples/tree/latest/clients/cloud/python)

---

## ✅ Checklist Pre-Implementazione

Prima di iniziare Step 1, verificare:

### Infrastruttura
- [ ] Kafka cluster disponibile (collaudo + produzione)
- [ ] Credenziali Kafka disponibili
- [ ] Rete: connettività server → Kafka (firewall rules)
- [ ] Topic creati o permessi per crearli

### Ambiente Sviluppo
- [ ] Python 3.11 installato
- [ ] Virtual environment attivo
- [ ] Git repository aggiornato
- [ ] Branch feature/kafka-integration creato

### Documentazione
- [ ] README.md letto e compreso
- [ ] CHANGELOG.md aggiornato
- [ ] Questo documento (KAFKA_INTEGRATION_PLAN.md) approvato

### Stakeholder
- [ ] Piano approvato da tech lead
- [ ] Timeline allineata con roadmap progetto
- [ ] Budget confermato (se necessario consulenza)

### Backup
- [ ] Backup database configurazioni
- [ ] Tag Git pre-integrazione creato
- [ ] Piano rollback documentato

---

## 🎯 Prossimi Passi

Una volta approvato questo piano:

1. **Kickoff Meeting** (1h)
   - Review piano con team
   - Assegnazione responsabilità
   - Setup communication channels

2. **Setup Ambiente** (Giorno 1)
   - Creare branch `feature/kafka-integration`
   - Verificare accesso Kafka
   - Setup testcontainer locale

3. **Start Step 1** (Giorno 1-2)
   - Implementare modelli Kafka
   - Estendere configurazione
   - Test caricamento config

4. **Weekly Checkpoint**
   - Ogni venerdì: review progresso vs piano
   - Aggiornare stima restante
   - Escalate blockers

---

## 📝 Note Finali

### Design Principles

Questo piano segue i principi guida del progetto PSTT Tool:

✅ **Modularità**: Ogni componente isolato e testabile  
✅ **Compatibilità**: Zero breaking changes su esistente  
✅ **Osservabilità**: Logging e metriche first-class  
✅ **Resilienza**: Retry, timeout, graceful degradation  
✅ **Semplicità**: Soluzioni semplici > soluzioni complesse

### Success Criteria

Integrazione considerata **successo** quando:

- ✅ Almeno 1 job Kafka in produzione funzionante per 1 settimana
- ✅ 20.000+ messaggi/giorno inviati con success rate > 99%
- ✅ Zero regressioni su funzionalità esistenti
- ✅ Documentazione completa e runbook testato
- ✅ Team formato su troubleshooting base

### Contacts

**Domande tecniche**: [GitHub Issues](https://github.com/your-org/pstt-tool/issues)  
**Escalation**: [Team Lead Contact]  
**Kafka Support**: [Kafka Team Contact]

---

**Documento preparato da**: GitHub Copilot  
**Data creazione**: 17 Gennaio 2026  
**Versione**: 1.0  
**Status**: 🔄 In attesa di approvazione

---

## 📎 Appendici

### Appendice A: Esempio Payload JSON

Formato messaggio Kafka per tracce CDG:

```json
{
  "data": {
    "barcode": "572680001120",
    "trkdate": "2026-01-16",
    "operator": 848,
    "msgtype": "M3",
    "causal": "RKE",
    "test_flag": "N",
    "phase_at": "W",
    "arrivetimestamp": "2026-01-16T11:50:32.665000",
    "status": "N",
    "track_office": "38713",
    "mtf_mtfid": 9,
    "date_other": "2026-01-16",
    "canale": "SGU",
    "custcode": "0030526661",
    "cust_sped": "PS6",
    "idsped": "S2132224"
  },
  "metadata": {
    "source": {
      "system": "PSTT_Tool",
      "version": "1.0.4",
      "connection": "A00-CDG-Collaudo",
      "query": "CDG-KAFKA-001--SelezioneTracceGiornaliere.sql"
    },
    "timestamp": "2026-01-17T10:30:45.123456Z",
    "processing": {
      "extracted_at": "2026-01-17T10:30:30Z",
      "published_at": "2026-01-17T10:30:45Z",
      "latency_ms": 15123
    }
  }
}
```

### Appendice B: Esempio Cron Expressions

Schedulazioni tipiche per job Kafka:

```
# Ogni giorno alle 2:00 AM (post-elaborazione notturna)
0 2 * * *

# Ogni ora (real-time processing)
0 * * * *

# Ogni 15 minuti durante orario lavorativo (8-18)
*/15 8-18 * * 1-5

# Primo giorno del mese (report mensile)
0 3 1 * *
```

### Appendice C: SQL Query Optimization

Best practice per query destinate a Kafka:

```sql
-- ✅ BUONO: Indici, filtri selettivi, nessun sort pesante
SELECT 
    BARCODE,
    TRKDATE,
    ARRIVETIMESTAMP,
    STATUS
FROM EXPORT_TABLE
WHERE TRKDATE >= TRUNC(SYSDATE) - 1
  AND TRKDATE < TRUNC(SYSDATE)
  AND TEST_FLAG = 'N';

-- ❌ EVITARE: Full table scan, sort massivo
SELECT * 
FROM EXPORT_TABLE
ORDER BY ARRIVETIMESTAMP DESC;

-- ✅ OTTIMIZZATO: Partition pruning (se partitioned)
SELECT /*+ PARALLEL(4) */
    BARCODE,
    TRKDATE,
    ARRIVETIMESTAMP
FROM EXPORT_TABLE PARTITION (P_20260116)
WHERE TEST_FLAG = 'N';
```

---

**Fine Documento**
