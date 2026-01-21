# Kafka Integration - Configuration Examples

## connections.json Example

```json
{
  "connections": {
    "cdg_prod": {
      "connection_string": "oracle+cx_oracle://user:pass@host:1521/?service_name=CDG",
      "description": "Database CDG Produzione"
    }
  },
  "kafka_connections": {
    "kafka_prod": {
      "bootstrap_servers": "kafka1.example.com:9092,kafka2.example.com:9092,kafka3.example.com:9092",
      "security_protocol": "SASL_SSL",
      "sasl_mechanism": "SCRAM-SHA-512",
      "sasl_username": "pstt_producer",
      "sasl_password": "${KAFKA_PROD_PASSWORD}",
      "ssl_cafile": "/etc/ssl/certs/kafka-ca-cert.pem",
      "ssl_certfile": "/etc/ssl/certs/kafka-client-cert.pem",
      "ssl_keyfile": "/etc/ssl/private/kafka-client-key.pem"
    },
    "kafka_collaudo": {
      "bootstrap_servers": "kafka-test1.example.com:9092,kafka-test2.example.com:9092",
      "security_protocol": "SASL_PLAINTEXT",
      "sasl_mechanism": "PLAIN",
      "sasl_username": "pstt_test",
      "sasl_password": "${KAFKA_TEST_PASSWORD}"
    },
    "kafka_dev": {
      "bootstrap_servers": "localhost:9092",
      "security_protocol": "PLAINTEXT"
    }
  }
}
```

## .env Example

```bash
# Kafka Production
KAFKA_PROD_PASSWORD=your_secure_password_here

# Kafka Test/Collaudo
KAFKA_TEST_PASSWORD=test_password_here

# Kafka Producer Settings (global defaults)
KAFKA_COMPRESSION_TYPE=snappy
KAFKA_BATCH_SIZE=16384
KAFKA_LINGER_MS=10
KAFKA_REQUEST_TIMEOUT_MS=30000
KAFKA_ACKS=all
KAFKA_RETRIES=3
KAFKA_ENABLE_IDEMPOTENCE=true
```

## Scheduling Configuration Examples

### Example 1: Export Tracce Giornaliere
```json
{
  "query": "CDG-KAFKA-001--TracceGiornaliere.sql",
  "connection": "cdg_prod",
  "enabled": true,
  "description": "Export tracce spedizioni giornaliere su Kafka",
  
  "scheduling_mode": "cron",
  "cron_expression": "0 8 * * *",
  
  "sharing_mode": "kafka",
  "kafka_topic": "cdg.tracce.giornaliere",
  "kafka_key_field": "codice_spedizione",
  "kafka_batch_size": 1000,
  "kafka_include_metadata": true,
  "kafka_connection": "kafka_prod"
}
```

### Example 2: Export Eventi Real-time (ogni 5 minuti)
```json
{
  "query": "CDG-KAFKA-002--EventiRealtime.sql",
  "connection": "cdg_prod",
  "enabled": true,
  "description": "Export eventi tracciatura real-time",
  
  "scheduling_mode": "cron",
  "cron_expression": "*/5 * * * *",
  
  "sharing_mode": "kafka",
  "kafka_topic": "cdg.eventi.realtime",
  "kafka_key_field": "evento_id",
  "kafka_batch_size": 500,
  "kafka_include_metadata": true,
  "kafka_connection": "kafka_prod"
}
```

### Example 3: Export Aggregati con Partitioning
```json
{
  "query": "BOSC-KAFKA-001--AggregatiGiornalieri.sql",
  "connection": "bosc_prod",
  "enabled": true,
  "description": "Export aggregati giornalieri per data",
  
  "scheduling_mode": "cron",
  "cron_expression": "0 9 * * *",
  
  "sharing_mode": "kafka",
  "kafka_topic": "bosc.aggregati.daily",
  "kafka_key_field": "data_aggregato",
  "kafka_batch_size": 100,
  "kafka_include_metadata": true,
  "kafka_connection": "kafka_prod",
  
  "output_date_format": "%Y-%m-%d",
  "output_offset_days": -1
}
```

### Example 4: Multi-Mode Export (Filesystem + Kafka)
**Note**: Attualmente non supportato direttamente. Per dual export serve creare 2 schedulazioni separate.

```json
[
  {
    "query": "CDG-DUAL-001--TracceGiornaliere.sql",
    "connection": "cdg_prod",
    "enabled": true,
    "description": "Export filesystem (backup)",
    "scheduling_mode": "cron",
    "cron_expression": "0 8 * * *",
    "sharing_mode": "filesystem",
    "output_dir": "exports/cdg_tracce",
    "output_filename_template": "tracce_{date}.xlsx"
  },
  {
    "query": "CDG-DUAL-001--TracceGiornaliere.sql",
    "connection": "cdg_prod",
    "enabled": true,
    "description": "Export Kafka (primary)",
    "scheduling_mode": "cron",
    "cron_expression": "0 8 * * *",
    "sharing_mode": "kafka",
    "kafka_topic": "cdg.tracce.giornaliere",
    "kafka_key_field": "codice_spedizione",
    "kafka_batch_size": 1000,
    "kafka_connection": "kafka_prod"
  }
]
```

## Query Examples

### CDG-KAFKA-001--TracceGiornaliere.sql
```sql
-- Export tracce spedizioni giornaliere
-- Message key: codice_spedizione

SELECT 
    t.codice_spedizione,
    t.data_evento,
    t.tipo_evento,
    t.stato,
    t.note,
    t.operatore,
    t.timestamp_inserimento
FROM 
    cdg_tracce t
WHERE 
    TRUNC(t.data_evento) = TRUNC(SYSDATE - 1)  -- Ieri
ORDER BY 
    t.codice_spedizione, t.data_evento
```

### CDG-KAFKA-002--EventiRealtime.sql
```sql
-- Export eventi real-time ultimi 5 minuti
-- Message key: evento_id

SELECT 
    e.evento_id,
    e.codice_spedizione,
    e.tipo_evento,
    e.timestamp_evento,
    e.payload_json,
    e.fonte_sistema
FROM 
    cdg_eventi e
WHERE 
    e.timestamp_evento >= SYSDATE - INTERVAL '5' MINUTE
ORDER BY 
    e.timestamp_evento
```

### BOSC-KAFKA-001--AggregatiGiornalieri.sql
```sql
-- Export aggregati giornalieri
-- Message key: data_aggregato

SELECT 
    TRUNC(data_operazione) as data_aggregato,
    tipo_prodotto,
    COUNT(*) as totale_operazioni,
    SUM(importo) as importo_totale,
    AVG(importo) as importo_medio,
    MAX(importo) as importo_max,
    MIN(importo) as importo_min
FROM 
    bosc_operazioni
WHERE 
    TRUNC(data_operazione) = TRUNC(SYSDATE - 1)
GROUP BY 
    TRUNC(data_operazione),
    tipo_prodotto
ORDER BY 
    data_aggregato, tipo_prodotto
```

## Message Format Examples

### Standard Message (with metadata)
```json
{
  "codice_spedizione": "CDG123456789",
  "data_evento": "2026-01-18",
  "tipo_evento": "CONSEGNA",
  "stato": "CONSEGNATO",
  "note": "Consegna effettuata al destinatario",
  "operatore": "OPR001",
  "timestamp_inserimento": "2026-01-18T14:30:15",
  "_metadata": {
    "source_query": "CDG-KAFKA-001--TracceGiornaliere.sql",
    "source_connection": "cdg_prod",
    "export_timestamp": "2026-01-18T08:00:15.123456",
    "export_id": "CDG-KAFKA-001--TracceGiornaliere.sql-20260118080015"
  }
}
```

### Message Without Metadata (kafka_include_metadata: false)
```json
{
  "codice_spedizione": "CDG123456789",
  "data_evento": "2026-01-18",
  "tipo_evento": "CONSEGNA",
  "stato": "CONSEGNATO",
  "note": "Consegna effettuata al destinatario",
  "operatore": "OPR001",
  "timestamp_inserimento": "2026-01-18T14:30:15"
}
```

## Topic Naming Conventions

### Recommended Pattern
```
<application>.<entity>.<type>

Examples:
- cdg.tracce.giornaliere
- cdg.eventi.realtime
- bosc.aggregati.daily
- tt2.stampe.pcl
```

### Anti-patterns (avoid)
```
❌ tracce                    # Troppo generico
❌ CDG_TRACCE_GIORNALIERE   # Uppercase, underscore
❌ cdg-tracce-01-18         # Date nel nome
❌ tracce.cdg               # Ordine invertito
```

## Performance Tuning

### Small Datasets (< 1000 records)
```json
{
  "kafka_batch_size": 100
}
```

### Medium Datasets (1K-10K records)
```json
{
  "kafka_batch_size": 500
}
```

### Large Datasets (10K-100K records)
```json
{
  "kafka_batch_size": 1000
}
```

### Very Large Datasets (> 100K records)
```json
{
  "kafka_batch_size": 2000
}
```

**Note**: Batch size ottimale dipende da:
- Dimensione media messaggi
- Latenza rete Kafka
- Throughput richiesto
- Memoria disponibile

## Monitoring & Troubleshooting

### Check scheduler_history.json
```bash
# Ultimi 10 export Kafka
jq '.[] | select(.export_mode == "kafka") | {query, status, kafka_messages_sent, kafka_messages_failed, kafka_duration_sec}' exports/scheduler_history.json | tail -20

# Export falliti
jq '.[] | select(.export_mode == "kafka" and .status == "fail")' exports/scheduler_history.json
```

### Log Analysis
```bash
# Cerca errori Kafka nei log
grep "KAFKA" logs/*.log | grep "ERROR"

# Monitora throughput
grep "KAFKA_EXPORT_END" logs/*.log | tail -20
```

### Performance Metrics
```bash
# Calcola throughput medio
jq '[.[] | select(.export_mode == "kafka" and .kafka_duration_sec > 0) | (.kafka_messages_sent / .kafka_duration_sec)] | add / length' exports/scheduler_history.json
```

## Common Issues & Solutions

### Issue: "Connessione Kafka 'default' non trovata"
**Soluzione**: Verifica che `kafka_connection` esista in `connections.json` sotto `kafka_connections`.

### Issue: "kafka_topic non specificato"
**Soluzione**: Aggiungi campo `kafka_topic` alla configurazione scheduling.

### Issue: Success rate < 95%
**Soluzione**: 
1. Verifica connettività Kafka cluster
2. Controlla dimensione messaggi (max 1MB default Kafka)
3. Aumenta `kafka_batch_size` se batch troppo piccoli
4. Verifica logs Kafka broker per errori

### Issue: Timeout durante export
**Soluzione**:
1. Riduci `kafka_batch_size`
2. Aumenta `KAFKA_REQUEST_TIMEOUT_MS` in .env
3. Verifica performance query SQL (ottimizza se necessario)
4. Controlla latenza rete verso Kafka cluster

### Issue: Campo key mancante
**Soluzione**: Assicurati che il campo specificato in `kafka_key_field` sia presente nel risultato query. Se non disponibile, verrà usato un UUID random (con warning nel log).

---

**Versione**: 1.1.0-alpha.1  
**Last Updated**: 2026-01-18  
**Status**: STEP 4 Completato
