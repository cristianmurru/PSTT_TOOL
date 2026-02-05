# Guida Setup Kafka - PSTT Tool

**Documentazione Operativa**  
**Data:** 20 Gennaio 2026  
**Versione:** 1.0  
**Autore:** GitHub Copilot

---

## 📋 Indice

1. [Prerequisiti](#prerequisiti)
2. [Configurazione Base](#configurazione-base)
3. [Quick Start](#quick-start)
4. [Configurazione Avanzata](#configurazione-avanzata)
5. [Schedulazione Job Kafka](#schedulazione-job-kafka)
6. [Monitoraggio e Metriche](#monitoraggio-e-metriche)
7. [Troubleshooting](#troubleshooting)
8. [Performance Tuning](#performance-tuning)
9. [Sicurezza SSL/SASL](#sicurezza-sslsasl)
10. [FAQ](#faq)

---

## 🎯 Prerequisiti

### Infrastruttura Kafka

Prima di configurare PSTT Tool, è necessario avere accesso a un cluster Kafka:

✅ **Kafka Cluster**
- Kafka 2.8+ o Confluent Platform 7.0+
- Almeno 3 broker per alta disponibilità (produzione)
- 1 broker sufficiente per sviluppo/test

✅ **Network**
- Connettività dalla macchina PSTT Tool ai broker Kafka
- Porte aperte (default: 9092 per PLAINTEXT, 9093 per SSL)
- Firewall configurato per permettere traffico outbound

✅ **Credenziali**
- Username e password (se SASL abilitato)
- Certificati SSL (se security_protocol = SSL o SASL_SSL)
- Permessi di scrittura sui topic target

✅ **Topic**
- Topic già creati oppure
- Permessi per auto-creazione topic

### Software PSTT Tool

✅ **Dipendenze Python**
```bash
# Già installate dopo step 1-6
kafka-python-ng==2.2.2
```

✅ **Python Environment**
- Python 3.11
- Virtual environment attivo

---

## 🔧 Configurazione Base

### 1. Variabili d'Ambiente (.env)

Aggiungere le seguenti variabili al file `.env`:

```bash
# ========================================
# KAFKA CONFIGURATION - BASE
# ========================================

# Kafka Broker(s)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Security Protocol
# Opzioni: PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL
KAFKA_SECURITY_PROTOCOL=PLAINTEXT

# Topic di default
KAFKA_DEFAULT_TOPIC=pstt-data

# Batch size per messaggi applicativi (numero messaggi)
KAFKA_MESSAGE_BATCH_SIZE=100

# Retry configuration
KAFKA_MAX_RETRIES=3
KAFKA_RETRY_BACKOFF_MS=100

# Logging
KAFKA_LOG_LEVEL=INFO
KAFKA_LOG_PAYLOAD=false
```

### 2. Configurazione connections.json (Opzionale)

Per gestire multiple connessioni Kafka (es. dev, collaudo, produzione):

```json
{
  "default_environment": "collaudo",
  "connections": [
    // ... existing DB connections ...
  ],
  "kafka_connections": {
    "development": {
      "name": "Kafka Development",
      "bootstrap_servers": "localhost:9092",
      "security_protocol": "PLAINTEXT",
      "default_topic": "pstt-dev"
    },
    "collaudo": {
      "name": "Kafka Collaudo",
      "bootstrap_servers": "kafka-collaudo.example.com:9092",
      "security_protocol": "SASL_SSL",
      "sasl_mechanism": "PLAIN",
      "default_topic": "pstt-collaudo"
    },
    "produzione": {
      "name": "Kafka Produzione",
      "bootstrap_servers": "kafka-prod-1.example.com:9093,kafka-prod-2.example.com:9093",
      "security_protocol": "SASL_SSL",
      "sasl_mechanism": "SCRAM-SHA-256",
      "default_topic": "pstt-traces"
    }
  }
}
```

### 3. Verifica Configurazione

Test connessione Kafka:

```bash
# Avvia l'applicazione
python main.py

# Apri browser
http://localhost:8000/kafka

# Oppure testa via API
curl -X POST http://localhost:8000/api/kafka/test \
  -H "Content-Type: application/json" \
  -d '{
    "bootstrap_servers": "localhost:9092",
    "security_protocol": "PLAINTEXT"
  }'
```

**Risposta attesa:**
```json
{
  "status": "success",
  "connected": true,
  "bootstrap_servers": "localhost:9092",
  "test_timestamp": "2026-01-20T10:30:00Z"
}
```

---

## 🚀 Quick Start

### Scenario: Primo Job Kafka in 5 Minuti

#### Step 1: Crea Query SQL

File: `Query/TEST-KAFKA-001--FirstTest.sql`

```sql
-- Test query per primo export Kafka
define DATA='2026-01-20'  --Obbligatorio: Data test

SELECT 
    'TEST-' || ROWNUM as MESSAGE_ID,
    'Test message number ' || ROWNUM as MESSAGE_TEXT,
    SYSDATE as CREATED_AT
FROM DUAL
CONNECT BY LEVEL <= 10;
```

#### Step 2: Configura Job via UI

1. Apri [http://localhost:8000/scheduler](http://localhost:8000/scheduler)
2. Clicca **"Nuova Schedulazione"**
3. Compila il form:

```
Nome: Test Export Kafka
Query: TEST-KAFKA-001--FirstTest.sql
Connessione DB: A00-CDG-Collaudo
Modalità: Manuale (per test)
Export Format: kafka ← IMPORTANTE
```

4. Configurazione Kafka:

```json
{
  "enabled": true,
  "topic": "pstt-test",
  "message_key_field": "MESSAGE_ID",
  "batch_size": 10,
  "include_metadata": true
}
```

5. Clicca **"Salva"** e poi **"Esegui Ora"**

#### Step 3: Verifica Risultato

```bash
# API: Verifica history esecuzione
curl http://localhost:8000/api/scheduler/history?limit=1

# API: Verifica metriche Kafka
curl http://localhost:8000/api/kafka/metrics/summary?period=today
```

**Output atteso:**
```json
{
  "period": "today",
  "total_messages": 10,
  "messages_sent": 10,
  "messages_failed": 0,
  "success_rate": 100.0,
  "total_bytes": 2048,
  "avg_latency_ms": 15.5
}
```

✅ **Congratulazioni!** Hai inviato i primi messaggi su Kafka!

---

## ⚙️ Configurazione Avanzata

### Tuning Producer Kafka

Per ottimizzare le performance, aggiungi queste variabili in `.env`:

```bash
# ========================================
# KAFKA CONFIGURATION - ADVANCED
# ========================================

# Producer Settings - Performance
KAFKA_BATCH_SIZE=16384              # Bytes per batch (default: 16KB)
KAFKA_LINGER_MS=10                  # Attesa per accumulare batch
KAFKA_COMPRESSION_TYPE=snappy       # Compressione: none, gzip, snappy, lz4, zstd
KAFKA_MAX_REQUEST_SIZE=1048576      # Max dimensione singola request (1MB)
KAFKA_REQUEST_TIMEOUT_MS=30000      # Timeout richiesta (30s)

# Producer Settings - Reliability
KAFKA_ENABLE_IDEMPOTENCE=true       # Previene duplicati
KAFKA_ACKS=all                      # Conferma da tutti i replica
KAFKA_MAX_IN_FLIGHT_REQUESTS=5      # Request parallele

# Producer Settings - Retry
KAFKA_RETRIES=3                     # Numero retry automatici
KAFKA_RETRY_BACKOFF_MS=100          # Backoff tra retry

# Buffer e Memory
KAFKA_BUFFER_MEMORY=33554432        # Buffer totale producer (32MB)
KAFKA_MAX_BLOCK_MS=60000            # Tempo max blocco se buffer pieno

# Monitoring
KAFKA_HEALTH_CHECK_INTERVAL_SEC=60  # Intervallo health check
```

### Configurazione per Ambiente

#### Development (Locale)
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SECURITY_PROTOCOL=PLAINTEXT
KAFKA_COMPRESSION_TYPE=none
KAFKA_LINGER_MS=0
```

#### Staging/Collaudo
```bash
KAFKA_BOOTSTRAP_SERVERS=kafka-staging.example.com:9092
KAFKA_SECURITY_PROTOCOL=SASL_PLAINTEXT
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=pstt-staging
KAFKA_SASL_PASSWORD=${KAFKA_PASSWORD_STAGING}
KAFKA_COMPRESSION_TYPE=snappy
KAFKA_LINGER_MS=10
```

#### Produzione
```bash
KAFKA_BOOTSTRAP_SERVERS=kafka-prod-1.example.com:9093,kafka-prod-2.example.com:9093,kafka-prod-3.example.com:9093
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-256
KAFKA_SASL_USERNAME=pstt-producer
KAFKA_SASL_PASSWORD=${KAFKA_PASSWORD_PROD}
KAFKA_SSL_CAFILE=/path/to/ca-cert.pem
KAFKA_COMPRESSION_TYPE=snappy
KAFKA_ENABLE_IDEMPOTENCE=true
KAFKA_ACKS=all
KAFKA_LINGER_MS=10
KAFKA_BATCH_SIZE=32768
```

---

## 📅 Schedulazione Job Kafka

### Configurazione Completa Job

Esempio configurazione JSON per schedulazione:

```json
{
  "name": "Export CDG Tracce to Kafka",
  "description": "Estrazione tracce giornaliere e pubblicazione su Kafka",
  "query": "CDG-KAFKA-001--SelezioneTracceGiornaliere.sql",
  "connection": "A00-CDG-Collaudo",
  "scheduling_mode": "cron",
  "cron": "0 2 * * *",
  "enabled": true,
  "timeout": 3600,
  "max_retries": 3,
  "retry_delay": 300,
  "parameters": {
    "DATA": "{date-1}"
  },
  "export_format": "kafka",
  "kafka_config": {
    "enabled": true,
    "topic": "pstt-traces",
    "message_key_field": "BARCODE",
    "batch_size": 100,
    "include_metadata": true,
    "connection_name": "produzione"
  },
  "email_notification": {
    "enabled": true,
    "on_success": false,
    "on_failure": true,
    "recipients": ["admin@example.com", "kafka-team@example.com"]
  }
}
```

### Campi Kafka Config

| Campo | Tipo | Obbligatorio | Default | Descrizione |
|-------|------|--------------|---------|-------------|
| `enabled` | boolean | Sì | `false` | Abilita export Kafka |
| `topic` | string | Sì | - | Topic Kafka destinazione |
| `message_key_field` | string | Sì | - | Campo da usare come message key |
| `batch_size` | integer | No | `100` | Messaggi per batch |
| `include_metadata` | boolean | No | `true` | Include metadata nel messaggio |
| `connection_name` | string | No | `"default"` | Nome connessione da connections.json |

### Parametri Query Dinamici

PSTT Tool supporta template dinamici nei parametri:

| Template | Esempio | Descrizione |
|----------|---------|-------------|
| `{date}` | `2026-01-20` | Data corrente (YYYY-MM-DD) |
| `{date-1}` | `2026-01-19` | Ieri |
| `{date-7}` | `2026-01-13` | 7 giorni fa |
| `{datetime}` | `2026-01-20 10:30:00` | Data e ora corrente |
| `{timestamp}` | `1737369000` | Unix timestamp |
| `{year}` | `2026` | Anno corrente |
| `{month}` | `01` | Mese corrente (01-12) |
| `{day}` | `20` | Giorno corrente (01-31) |

---

## 📊 Monitoraggio e Metriche

### Dashboard Kafka

Accedi a [http://localhost:8000/kafka](http://localhost:8000/kafka) per visualizzare:

- **Status Connessione**: Indicatore verde/rosso
- **Metriche Producer**: Messaggi inviati, falliti, latenza
- **Job Schedulati**: Lista job Kafka attivi
- **Test Tools**: Form per test manuali

### API Metriche

#### Riepilogo Giornaliero
```bash
curl http://localhost:8000/api/kafka/metrics/summary?period=today
```

#### Statistiche Orarie
```bash
curl http://localhost:8000/api/kafka/metrics/hourly?hours=24
```

#### Metriche per Topic
```bash
curl http://localhost:8000/api/kafka/metrics/topic/pstt-traces?limit=100
```

### File Metriche

Le metriche sono persistite in:
```
exports/kafka_metrics.json
```

Retention di default: **90 giorni**

Cleanup manuale:
```bash
curl -X POST http://localhost:8000/api/kafka/metrics/cleanup?days=30
```

---

## 🔍 Troubleshooting

### Problema: Connection Timeout

**Sintomo:**
```
[KAFKA] ERROR: TimeoutError connecting to bootstrap servers
```

**Diagnosi:**
```bash
# 1. Verifica connettività rete
telnet kafka-broker.example.com 9092

# 2. Verifica DNS
nslookup kafka-broker.example.com

# 3. Test da PSTT Tool
curl -X POST http://localhost:8000/api/kafka/test \
  -H "Content-Type: application/json" \
  -d '{"bootstrap_servers": "kafka-broker.example.com:9092"}'
```

**Soluzioni:**
1. Verifica firewall: porta 9092 o 9093 aperta
2. Controlla security groups (se cloud)
3. Verifica bootstrap_servers corretto (formato: `host:port`)
4. Aumenta timeout in `.env`: `KAFKA_REQUEST_TIMEOUT_MS=60000`

---

### Problema: Authentication Failed

**Sintomo:**
```
[KAFKA] ERROR: Authentication failed: Invalid credentials
```

**Diagnosi:**
```bash
# Verifica credenziali in .env
grep KAFKA_SASL .env

# Test connessione con credenziali
curl -X POST http://localhost:8000/api/kafka/test \
  -H "Content-Type: application/json" \
  -d '{
    "bootstrap_servers": "kafka-broker:9092",
    "security_protocol": "SASL_SSL",
    "sasl_mechanism": "PLAIN",
    "sasl_username": "pstt-producer",
    "sasl_password": "your-password"
  }'
```

**Soluzioni:**
1. Verifica username/password corretti
2. Controlla `SASL_MECHANISM` (PLAIN, SCRAM-SHA-256, SCRAM-SHA-512)
3. Verifica ACL Kafka (permessi topic)
4. Controlla scadenza credenziali

---

### Problema: Message Too Large

**Sintomo:**
```
[KAFKA] ERROR: MessageSizeTooLargeError: Message size exceeds max.message.bytes
```

**Diagnosi:**
```bash
# Controlla dimensione messaggi
curl http://localhost:8000/api/kafka/metrics/summary

# Verifica configurazione Kafka broker
# max.message.bytes (default: 1MB)
```

**Soluzioni:**
1. Riduci `batch_size` nella configurazione job
2. Aumenta `KAFKA_MAX_REQUEST_SIZE` in `.env`:
   ```bash
   KAFKA_MAX_REQUEST_SIZE=5242880  # 5MB
   ```
3. Configura broker Kafka: `max.message.bytes=5242880`
4. Abilita compressione: `KAFKA_COMPRESSION_TYPE=snappy`

---

### Problema: High Latency (p99 > 5s)

**Sintomo:**
Dashboard mostra latenze elevate.

**Diagnosi:**
```bash
# Verifica metriche dettagliate
curl http://localhost:8000/api/kafka/metrics/hourly?hours=6

# Controlla log
grep "KAFKA.*latency" logs/pstt_*.log
```

**Soluzioni:**
1. **Ottimizza batching:**
   ```bash
   KAFKA_LINGER_MS=50
   KAFKA_BATCH_SIZE=32768
   ```

2. **Abilita compressione:**
   ```bash
   KAFKA_COMPRESSION_TYPE=snappy
   ```

3. **Riduci payload:**
   - Rimuovi campi non necessari dalla query
   - Disabilita metadata: `"include_metadata": false`

4. **Verifica load Kafka cluster:**
   - Controlla metriche broker Kafka
   - Scala cluster se necessario

---

### Problema: Messaggi Duplicati

**Sintomo:**
Consumer riceve messaggi duplicati.

**Diagnosi:**
```bash
# Verifica idempotenza abilitata
grep KAFKA_ENABLE_IDEMPOTENCE .env
```

**Soluzioni:**
1. **Abilita idempotenza:**
   ```bash
   KAFKA_ENABLE_IDEMPOTENCE=true
   KAFKA_ACKS=all
   KAFKA_MAX_IN_FLIGHT_REQUESTS=5
   ```

2. **Usa message key unica:**
   - Assicurati che `message_key_field` contenga valori univoci
   - Esempio: BARCODE, UUID, ID_TRANSAZIONE

3. **Implementa deduplicazione consumer-side:**
   - Usa consumer group con offset commit
   - Memorizza message key processate

---

### Problema: Job Kafka Fallisce

**Sintomo:**
Scheduler mostra job con status "error".

**Diagnosi:**
```bash
# Verifica history
curl http://localhost:8000/api/scheduler/history?scheduling_id=<ID>

# Controlla log dettagliato
grep "KAFKA_JOB.*ERROR" logs/pstt_*.log
```

**Soluzioni:**
1. **Verifica query SQL:**
   - Testa query manualmente in PSTT Tool
   - Verifica parametri corretti

2. **Verifica connessione Kafka:**
   ```bash
   curl http://localhost:8000/api/kafka/health
   ```

3. **Controlla message_key_field:**
   - Assicurati che campo esista nei risultati query
   - Campo non deve essere NULL

4. **Aumenta timeout job:**
   ```json
   {
     "timeout": 7200,
     "max_retries": 5,
     "retry_delay": 600
   }
   ```

---

## ⚡ Performance Tuning

### Obiettivo: 20.000 messaggi/giorno

**Configurazione Base (OK per 20K msg/giorno):**

```bash
KAFKA_MESSAGE_BATCH_SIZE=100
KAFKA_BATCH_SIZE=16384
KAFKA_LINGER_MS=10
KAFKA_COMPRESSION_TYPE=snappy
```

**Throughput stimato:** ~100 msg/sec = 360K msg/ora

---

### Obiettivo: 200.000 messaggi/giorno

**Configurazione Ottimizzata:**

```bash
# Batch più grandi
KAFKA_MESSAGE_BATCH_SIZE=500
KAFKA_BATCH_SIZE=65536

# Maggiore attesa per accumulare batch
KAFKA_LINGER_MS=50

# Compressione efficiente
KAFKA_COMPRESSION_TYPE=lz4

# Più request parallele
KAFKA_MAX_IN_FLIGHT_REQUESTS=10

# Buffer più grande
KAFKA_BUFFER_MEMORY=67108864  # 64MB
```

**Throughput stimato:** ~500 msg/sec = 1.8M msg/ora

---

### Benchmark Test

Script per testare throughput:

```python
# File: tools/kafka_benchmark.py
import asyncio
import time
from app.services.kafka_service import get_kafka_service

async def benchmark(num_messages: int = 10000):
    service = get_kafka_service()
    
    messages = [
        (f"key-{i}", {"id": i, "data": f"test message {i}"})
        for i in range(num_messages)
    ]
    
    start = time.time()
    result = await service.send_batch(
        topic="pstt-benchmark",
        messages=messages
    )
    elapsed = time.time() - start
    
    throughput = num_messages / elapsed
    print(f"Sent {result.succeeded}/{num_messages} messages in {elapsed:.2f}s")
    print(f"Throughput: {throughput:.0f} msg/sec")
    
    return throughput

if __name__ == "__main__":
    asyncio.run(benchmark(10000))
```

**Esecuzione:**
```bash
python tools/kafka_benchmark.py
```

---

### Tuning Query SQL

**❌ Query Lenta (Full Scan):**
```sql
SELECT * FROM EXPORT_TABLE
WHERE TRUNC(TRKDATE) = TRUNC(SYSDATE - 1)
ORDER BY ARRIVETIMESTAMP DESC;
```

**✅ Query Ottimizzata:**
```sql
SELECT 
    BARCODE,
    TRKDATE,
    ARRIVETIMESTAMP,
    STATUS
FROM EXPORT_TABLE
WHERE TRKDATE >= TRUNC(SYSDATE - 1)
  AND TRKDATE < TRUNC(SYSDATE)
  AND TEST_FLAG = 'N'
ORDER BY ARRIVETIMESTAMP;  -- Solo se necessario
```

**Best Practices:**
1. Usa indici su campi filtro (TRKDATE)
2. Evita `SELECT *`, specifica solo colonne necessarie
3. Evita `TRUNC()` su colonne indicizzate
4. Usa range query invece di equality su funzioni
5. Limita ORDER BY se possibile

---

## 🔐 Sicurezza SSL/SASL

### Configurazione SSL (Encryption Only)

```bash
# .env
KAFKA_SECURITY_PROTOCOL=SSL
KAFKA_SSL_CAFILE=/app/certs/ca-cert.pem
KAFKA_SSL_CERTFILE=/app/certs/client-cert.pem
KAFKA_SSL_KEYFILE=/app/certs/client-key.pem
KAFKA_SSL_CHECK_HOSTNAME=true
```

### Configurazione SASL/PLAIN

```bash
# .env
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=pstt-producer
KAFKA_SASL_PASSWORD=${KAFKA_PASSWORD}
KAFKA_SSL_CAFILE=/app/certs/ca-cert.pem
```

### Configurazione SASL/SCRAM

```bash
# .env
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-256  # o SCRAM-SHA-512
KAFKA_SASL_USERNAME=pstt-producer
KAFKA_SASL_PASSWORD=${KAFKA_PASSWORD}
KAFKA_SSL_CAFILE=/app/certs/ca-cert.pem
```

### Gestione Certificati

**Posizionamento certificati:**
```
C:\App\PSTT_TOOL\certs\
├── ca-cert.pem          # Certificate Authority
├── client-cert.pem      # Client certificate
└── client-key.pem       # Client private key
```

**Permessi Windows:**
```powershell
# Imposta permessi lettura solo per servizio
icacls "C:\App\PSTT_TOOL\certs" /inheritance:r
icacls "C:\App\PSTT_TOOL\certs" /grant:r "NT SERVICE\PSTT_Service:(OI)(CI)R"
```

### Rotazione Credenziali

Procedura per aggiornare credenziali senza downtime:

1. **Prepara nuove credenziali:**
   ```bash
   # .env.new
   KAFKA_SASL_USERNAME=pstt-producer-new
   KAFKA_SASL_PASSWORD=new-secure-password
   ```

2. **Test nuove credenziali:**
   ```bash
   curl -X POST http://localhost:8000/api/kafka/test \
     -H "Content-Type: application/json" \
     -d '{
       "sasl_username": "pstt-producer-new",
       "sasl_password": "new-secure-password"
     }'
   ```

3. **Aggiorna .env e restart:**
   ```powershell
   # Backup .env
   Copy-Item .env .env.backup
   
   # Applica nuove credenziali
   Copy-Item .env.new .env
   
   # Restart servizio
   .\tools\manage_service.ps1 -action restart
   ```

4. **Verifica:**
   ```bash
   curl http://localhost:8000/api/kafka/health
   ```

---

## ❓ FAQ

### Q: Quale formato devo usare per message key?

**A:** Usa un campo univoco o semi-univoco:
- ✅ **Ottimo**: UUID, Transaction ID, Order ID
- ✅ **Buono**: BARCODE (se univoco), Customer ID
- ⚠️ **Accettabile**: DATE + SEQUENCE
- ❌ **Evitare**: Timestamp (bassa cardinalità), Status

---

### Q: Posso inviare dati binari (file, immagini)?

**A:** Sì, ma con limitazioni:
1. Converti in Base64 nella query SQL
2. Limita dimensione < 1MB per messaggio
3. Considera storage alternativo (S3, blob) e invia solo riferimento

---

### Q: Come gestisco schema evolution?

**A:** Due approcci:

**1. Include metadata (raccomandato):**
```json
{
  "data": {...},
  "metadata": {
    "schema_version": "v1.2.0",
    "system": "PSTT_Tool"
  }
}
```

**2. Usa Schema Registry (avanzato):**
- Richiede Confluent Schema Registry
- Supporto Avro/Protobuf
- Non ancora implementato in PSTT Tool

---

### Q: Quanti topic devo creare?

**A:** Dipende dall'architettura:

**Approccio 1: Topic per tipo dato (raccomandato)**
```
pstt-traces      → Tracce spedizioni
pstt-events      → Eventi operativi
pstt-analytics   → Dati aggregati
```

**Approccio 2: Topic unico multi-tenancy**
```
pstt-data        → Tutti i messaggi
```
Usa message header o campo `type` per distinguere.

---

### Q: Cosa succede se Kafka è down durante schedulazione?

**A:** Il job fallisce ma:
1. ✅ Retry automatici (configurabili)
2. ✅ Email notifica su errore
3. ✅ Log dettagliato in `logs/pstt_*.log`
4. ✅ History con errore salvata

**Recupero manuale:**
1. Verifica connessione Kafka
2. Re-esegui job da UI: **"Esegui Ora"**

---

### Q: Come monitoro consumer lag?

**A:** PSTT Tool è solo producer. Per consumer:
1. Usa Kafka tools: `kafka-consumer-groups`
2. Monitoring: Burrow, Kafka Manager, Confluent Control Center
3. Metriche: Prometheus + Grafana

---

### Q: Supportate transazioni Kafka?

**A:** No, non in questa versione. Alternative:
1. Usa idempotenza (`KAFKA_ENABLE_IDEMPOTENCE=true`)
2. Implementa deduplicazione consumer-side
3. Message key univoca per idempotency

---

### Q: Come faccio rollback se ci sono problemi?

**A:** Vedi [Runbook: Piano Rollback](#runbook-piano-rollback)

```powershell
# 1. Disabilita job Kafka via UI
# 2. Se necessario, rollback codice
git checkout <tag-pre-kafka>
.\tools\manage_service.ps1 -action restart
```

---

## 📞 Supporto

### Contatti

- **Documentazione**: `docs/KAFKA_SETUP.md` (questo file)
- **Runbook Operativo**: `docs/KAFKA_RUNBOOK.md`
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Issues**: GitHub Issues o sistema ticketing interno

### Log Files

```
logs/pstt_YYYYMMDD.log           # Log applicativo
logs/pstt_errors_YYYYMMDD.log    # Solo errori
exports/kafka_metrics.json       # Metriche Kafka
exports/scheduler_history.json   # History job
```

### Comandi Utili

```powershell
# Verifica status servizio
Get-Service PSTT_Service

# Restart servizio
.\tools\manage_service.ps1 -action restart

# Tail log in real-time
Get-Content logs\pstt_*.log -Wait -Tail 50

# Test connessione Kafka
curl http://localhost:8000/api/kafka/health

# Verifica metriche
curl http://localhost:8000/api/kafka/metrics/summary
```

---

**Documento aggiornato:** 20 Gennaio 2026  
**Versione PSTT Tool:** 1.0.4+kafka  
**Autore:** GitHub Copilot
