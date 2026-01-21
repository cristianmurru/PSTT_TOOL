# STEP 4: SchedulerService Integration - Implementation Summary

**Status**: ✅ COMPLETATO  
**Data**: 2026-01-18  
**Test Coverage**: 15/15 passed (100%)  
**Total Kafka Tests**: 80/80 passed (STEP 1-4)

## 📋 Obiettivi Raggiunti

### 1. Estensione Modelli (`app/models/scheduling.py`)
- ✅ Aggiunto `SharingMode.KAFKA` enum value
- ✅ Esteso `SchedulingItem` con 5 nuovi campi Kafka:
  - `kafka_topic`: Topic Kafka di destinazione
  - `kafka_key_field`: Campo da usare come message key (default: 'id')
  - `kafka_batch_size`: Dimensione batch (range: 1-10000, default: 100)
  - `kafka_include_metadata`: Flag per metadata automatici (default: True)
  - `kafka_connection`: Nome connessione da connections.json (default: 'default')
- ✅ Esteso `SchedulingHistoryItem` con tracking Kafka:
  - `kafka_topic`: Topic utilizzato
  - `kafka_messages_sent`: Messaggi inviati con successo
  - `kafka_messages_failed`: Messaggi falliti
  - `kafka_duration_sec`: Durata invio batch
  - `export_mode`: 'filesystem', 'email', o 'kafka'

### 2. Integrazione SchedulerService (`app/services/scheduler_service.py`)
- ✅ Metodo `_execute_kafka_export()` completo (~140 righe)
- ✅ Caricamento configurazione da `connections.json`
- ✅ Trasformazione risultati query → messaggi Kafka
- ✅ Metadata automatici nei messaggi
- ✅ Invio batch con retry automatico (3 tentativi)
- ✅ Tracking completo in `scheduler_history.json`
- ✅ Error handling robusto
- ✅ Logging dettagliato con metriche

### 3. Pipeline Export Kafka
- ✅ Supporto `sharing_mode='kafka'` in `run_scheduled_query()`
- ✅ Flow completo: Query → Transform → Kafka Export
- ✅ Tracking `export_mode` in tutte le esecuzioni
- ✅ Zero breaking changes su filesystem/email export

## 🔧 API Reference

### Configurazione SchedulingItem

```python
{
    "query": "CDG-KAFKA-001--TracceGiornaliere.sql",
    "connection": "cdg_prod",
    "enabled": true,
    "scheduling_mode": "cron",
    "cron_expression": "0 8 * * *",  # Ogni giorno alle 8:00
    
    # Kafka Export Configuration
    "sharing_mode": "kafka",
    "kafka_topic": "cdg-tracce-giornaliere",
    "kafka_key_field": "codice_spedizione",
    "kafka_batch_size": 500,
    "kafka_include_metadata": true,
    "kafka_connection": "kafka_prod"
}
```

### Configurazione connections.json

```json
{
  "kafka_connections": {
    "kafka_prod": {
      "bootstrap_servers": "kafka1.example.com:9092,kafka2.example.com:9092",
      "security_protocol": "SASL_SSL",
      "sasl_mechanism": "SCRAM-SHA-512",
      "sasl_username": "pstt_producer",
      "sasl_password": "${KAFKA_PASSWORD}",
      "ssl_cafile": "/path/to/ca-cert.pem"
    },
    "kafka_dev": {
      "bootstrap_servers": "localhost:9092",
      "security_protocol": "PLAINTEXT"
    }
  }
}
```

### Formato Messaggio Kafka

```json
{
  "codice_spedizione": "ABC123456",
  "data_evento": "2026-01-18",
  "stato": "CONSEGNATO",
  "note": "Consegna effettuata",
  "_metadata": {
    "source_query": "CDG-KAFKA-001--TracceGiornaliere.sql",
    "source_connection": "cdg_prod",
    "export_timestamp": "2026-01-18T08:00:15.123456",
    "export_id": "CDG-KAFKA-001--TracceGiornaliere.sql-20260118080015"
  }
}
```

**Message Key**: Valore del campo `kafka_key_field` (es: "ABC123456")

### Formato scheduler_history.json

```json
{
  "query": "CDG-KAFKA-001--TracceGiornaliere.sql",
  "connection": "cdg_prod",
  "timestamp": "2026-01-18T08:00:15.123456",
  "status": "success",
  "duration_sec": 12.5,
  "row_count": 5000,
  "export_mode": "kafka",
  "kafka_topic": "cdg-tracce-giornaliere",
  "kafka_messages_sent": 5000,
  "kafka_messages_failed": 0,
  "kafka_duration_sec": 10.2,
  "start_date": "2026-01-18"
}
```

## 📊 Export Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SCHEDULER EXECUTION                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Execute Query (QueryService)                             │
│     - Timeout: 300s (configurable)                           │
│     - Result: List[Dict] (es: 5000 righe)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Check sharing_mode                                       │
│     - filesystem → Save as XLSX                              │
│     - email → Save + Send email                              │
│     - kafka → Transform + Send to Kafka ✅                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ (kafka mode)
┌─────────────────────────────────────────────────────────────┐
│  3. _execute_kafka_export()                                  │
│     a. Load Kafka config from connections.json               │
│     b. Transform rows → messages (key/value pairs)           │
│     c. Add metadata (if kafka_include_metadata=True)         │
│     d. Create KafkaService instance                          │
│     e. send_batch_with_retry(messages, max_retries=3)        │
│     f. Log results (throughput, success_rate, duration)      │
│     g. Update scheduler_history.json with Kafka fields       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. History Tracking                                         │
│     - export_mode: 'kafka'                                   │
│     - kafka_topic, kafka_messages_sent, kafka_duration_sec   │
│     - Success rate threshold: 95%                            │
└─────────────────────────────────────────────────────────────┘
```

## 🧪 Test Coverage

### Test Implementati (15 totali)

**TestSchedulingItemKafkaFields** (4 test):
1. ✅ `test_kafka_fields_present` - Campi Kafka presenti in SchedulingItem
2. ✅ `test_kafka_fields_optional` - Campi Kafka opzionali
3. ✅ `test_kafka_batch_size_validation` - Validazione range batch_size (1-10000)
4. ✅ `test_sharing_mode_kafka_enum` - Enum KAFKA correttamente definito

**TestKafkaExportMethod** (6 test):
5. ✅ `test_execute_kafka_export_success` - Export completo con successo
6. ✅ `test_execute_kafka_export_no_topic` - Errore se topic mancante
7. ✅ `test_execute_kafka_export_connection_not_found` - Connessione non trovata
8. ✅ `test_execute_kafka_export_partial_failure` - Gestione fallimento parziale
9. ✅ `test_execute_kafka_export_metadata_inclusion` - Metadata incluso
10. ✅ `test_execute_kafka_export_without_metadata` - Metadata escluso

**TestSchedulingHistoryKafkaFields** (2 test):
11. ✅ `test_history_kafka_fields` - Campi Kafka in history item
12. ✅ `test_history_without_kafka_fields` - History senza campi Kafka

**TestExportModeTracking** (3 test):
13. ✅ `test_export_mode_kafka` - export_mode='kafka' tracciato
14. ✅ `test_export_mode_filesystem` - export_mode='filesystem' tracciato
15. ✅ `test_export_mode_email` - export_mode='email' tracciato

### Test Command
```bash
pytest tests/test_scheduler_kafka_integration.py -v
```

### Total Test Results
```
STEP 1 (config):          25 tests ✅
STEP 2 (service base):    24 tests ✅
STEP 3 (batch):           16 tests ✅
STEP 4 (integration):     15 tests ✅
─────────────────────────────────────
TOTAL:                    80 tests ✅ (100% passed)
```

## 📝 Implementation Details

### File Modificati

1. **app/models/scheduling.py**
   - Linee aggiunte: ~20
   - Modifiche:
     - Aggiunto `SharingMode.KAFKA`
     - Campi Kafka in `SchedulingItem`
     - Campi tracking in `SchedulingHistoryItem`

2. **app/services/scheduler_service.py**
   - Linee aggiunte: ~150
   - Modifiche:
     - Import `KafkaService`, `KafkaConnectionConfig`, `KafkaProducerConfig`
     - Metodo `_execute_kafka_export()` completo
     - Branch `sharing_mode='kafka'` in `run_scheduled_query()`
     - Tracking `export_mode` in history append

3. **tests/test_scheduler_kafka_integration.py**
   - File nuovo: 15 test completi
   - Linee totali: ~550
   - Coverage: Models + SchedulerService integration

### Metadata Automatici

Quando `kafka_include_metadata=True`, ogni messaggio include:

```python
{
    ...  # dati originali riga query
    "_metadata": {
        "source_query": "nome_file_query.sql",
        "source_connection": "nome_connessione_db",
        "export_timestamp": "ISO8601 timestamp",
        "export_id": "unique_export_id"
    }
}
```

**Benefici**:
- Traceability completa origine dati
- Debugging facilitato
- Audit trail automatico
- Possibilità di ricostruire fonte dati

### Error Handling

```python
# Success Rate Threshold
if result.get_success_rate() < 95.0:
    raise Exception(
        f"Kafka export failed: solo {result.succeeded}/{result.total} messaggi inviati "
        f"({success_rate:.1f}% success rate)"
    )

# History Update su Errore
if self.execution_history and self.execution_history[-1].get('query') == query_filename:
    self.execution_history[-1]['error'] = f"Kafka export failed: {str(kafka_err)}"
    self.execution_history[-1]['status'] = 'fail'
    self.save_history()
```

### Retry Logic

- **Max Retries**: 3 tentativi (configurato in `send_batch_with_retry`)
- **Backoff**: 100ms → 200ms → 400ms (esponenziale)
- **Success Threshold**: 95% messaggi inviati
- **Fallback**: Se tutti i retry falliscono, solleva eccezione e history viene aggiornato con errore

## 🎯 Use Cases

### 1. Export Giornaliero Tracce Spedizioni
```python
{
    "query": "CDG-KAFKA-001--TracceGiornaliere.sql",
    "connection": "cdg_prod",
    "cron_expression": "0 8 * * *",  # Ogni giorno alle 8:00
    "sharing_mode": "kafka",
    "kafka_topic": "cdg-tracce-giornaliere",
    "kafka_key_field": "codice_spedizione",
    "kafka_batch_size": 1000
}
```

### 2. Export Real-time Eventi
```python
{
    "query": "CDG-KAFKA-002--EventiRealtime.sql",
    "connection": "cdg_prod",
    "cron_expression": "*/5 * * * *",  # Ogni 5 minuti
    "sharing_mode": "kafka",
    "kafka_topic": "cdg-eventi-realtime",
    "kafka_key_field": "evento_id",
    "kafka_batch_size": 500,
    "kafka_include_metadata": true
}
```

### 3. Export Aggregati Giornalieri
```python
{
    "query": "BOSC-KAFKA-001--AggregatiGiornalieri.sql",
    "connection": "bosc_prod",
    "cron_expression": "0 9 * * *",  # Ogni giorno alle 9:00
    "sharing_mode": "kafka",
    "kafka_topic": "bosc-aggregati",
    "kafka_key_field": "data_aggregato",
    "kafka_batch_size": 100,
    "kafka_connection": "kafka_prod"
}
```

## 📚 References

- **Prompt originale**: [Prompts/05-TopicKafka.md](../Prompts/05-TopicKafka.md)
- **Models Scheduling**: [app/models/scheduling.py](../app/models/scheduling.py)
- **SchedulerService**: [app/services/scheduler_service.py](../app/services/scheduler_service.py)
- **KafkaService**: [app/services/kafka_service.py](../app/services/kafka_service.py) (STEP 2-3)
- **Tests**: [tests/test_scheduler_kafka_integration.py](../tests/test_scheduler_kafka_integration.py)
- **Changelog**: [CHANGELOG.md](../CHANGELOG.md) - v1.1.0-alpha.1

## ✅ Acceptance Criteria

- [x] SchedulingItem esteso con campi Kafka
- [x] SharingMode.KAFKA enum definito
- [x] Validazione batch_size (1-10000)
- [x] Metodo `_execute_kafka_export()` implementato
- [x] Caricamento config da connections.json
- [x] Trasformazione query results → Kafka messages
- [x] Metadata automatici opzionali
- [x] Invio batch con retry (max 3)
- [x] Success rate threshold 95%
- [x] Tracking completo in scheduler_history.json
- [x] Export_mode tracking (kafka/filesystem/email)
- [x] Error handling robusto
- [x] Logging dettagliato con metriche
- [x] Test coverage 100% (15/15)
- [x] Zero breaking changes
- [x] Documentazione completa

## 🔄 Backward Compatibility

- ✅ Export filesystem: funziona come prima
- ✅ Export email: funziona come prima
- ✅ Campi Kafka opzionali in SchedulingItem
- ✅ History format esteso, campi nuovi opzionali
- ✅ Nessun cambio API esistenti
- ✅ Zero breaking changes

## 🎯 Next Steps (STEP 5)

### API Endpoints da Implementare
1. **POST `/api/kafka/test-connection`**
   - Test connettività Kafka cluster
   - Input: connection_name o connection_config
   - Output: KafkaHealthStatus

2. **POST `/api/kafka/publish`**
   - Publish singolo messaggio (debug/test)
   - Input: topic, key, value, connection
   - Output: Success/Error

3. **POST `/api/kafka/publish-batch`**
   - Publish batch manuale
   - Input: topic, messages[], batch_size, connection
   - Output: BatchResult

4. **GET `/api/kafka/metrics`**
   - Metriche producer Kafka
   - Output: KafkaMetrics

5. **GET `/api/kafka/connections`**
   - Lista connessioni Kafka disponibili
   - Output: List[KafkaConnectionInfo]

### UI Dashboard da Creare
1. Pannello configurazione schedulazioni Kafka
2. Form test connessione Kafka
3. Visualizzazione history con filtri export_mode
4. Metriche Kafka in tempo reale
5. Monitor throughput/success rate per topic

---

**STEP 4 Status**: ✅ **COMPLETATO CON SUCCESSO**  
**Total Tests**: 80/80 passed (25 STEP1 + 40 STEP2-3 + 15 STEP4)  
**Ready for**: STEP 5 - API Endpoints e UI Dashboard
