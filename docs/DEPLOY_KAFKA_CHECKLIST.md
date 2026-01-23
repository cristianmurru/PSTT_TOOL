# Deploy Kafka - Pre-Deploy Checklist

**Data:** 21 Gennaio 2026  
**Ambiente Target:** Collaudo → Produzione  
**Responsabile Deploy:** [Nome]

---

## ✅ Pre-Deploy Checklist (Sviluppo)

### Codice e Test
- [x] Tutti i test passano (111/111)
- [x] Coverage >= 75% (attuale: 76%)
- [x] Nessun errore critico nei log
- [x] Codice committed e pushato su repository

### Documentazione
- [x] KAFKA_SETUP.md completo (~400 righe)
- [x] KAFKA_RUNBOOK.md completo (~600 righe)
- [x] CHANGELOG.md aggiornato (v1.1.0)
- [x] Benchmark tool disponibile (kafka_benchmark.py)

### Configurazione
- [ ] Credenziali Kafka collaudo disponibili
- [ ] Credenziali Kafka produzione disponibili
- [ ] Topic Kafka creati su broker (es. `pstt-traces-collaudo`, `pstt-traces-prod`)
- [ ] Network/Firewall configurato per accesso broker Kafka

### Backup
- [ ] Backup `connections.json` corrente
- [ ] Backup `.env` corrente
- [ ] Backup `scheduler_history.json`
- [ ] Tag Git creato (es. `v1.0.4-pre-kafka`)

---

## 📦 Fase 1: Deploy Infrastruttura Collaudo

### 1.1 Preparazione Pacchetto Deploy

**Su macchina di sviluppo:**

```powershell
# Crea pacchetto deploy
$deployDate = Get-Date -Format "yyyyMMdd_HHmmss"
$deployDir = "c:\App\PSTT_TOOL\release\kafka_deploy_$deployDate"
New-Item -ItemType Directory -Path $deployDir -Force

# Copia file essenziali
Copy-Item "requirements.txt" $deployDir
Copy-Item ".env.example" "$deployDir\.env.template"
Copy-Item "connections.json" "$deployDir\connections.json.template"
Copy-Item -Recurse "app" $deployDir
Copy-Item -Recurse "docs" $deployDir
Copy-Item -Recurse "tools" $deployDir

# Crea archivio
Compress-Archive -Path "$deployDir\*" -DestinationPath "$deployDir.zip"
Write-Host "✅ Pacchetto deploy creato: $deployDir.zip"
```

### 1.2 Deploy su Collaudo

**Su Terminal Server → Collaudo:**

```powershell
# 1. Stop servizio
.\manage_service.ps1 -action stop

# 2. Backup configurazioni
$backupDate = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "connections.json" "connections.json.backup_$backupDate"
Copy-Item ".env" ".env.backup_$backupDate"

# 3. Estrai pacchetto
# (copiare manualmente kafka_deploy_YYYYMMDD_HHMMSS.zip su collaudo)
Expand-Archive -Path "kafka_deploy_*.zip" -DestinationPath "." -Force

# 4. Installa dipendenze Kafka (offline bundle)
.\.venv\Scripts\python.exe -m pip install --no-index --find-links=C:\temp\kafka_package kafka-python-ng==2.2.2 aiokafka==0.10.0

# (Opzionale) Librerie di compressione per performance
# Installa se usi `KAFKA_COMPRESSION_TYPE=snappy|lz4|zstd`
.\.venv\Scripts\python.exe -m pip install --no-index --find-links=C:\temp\kafka_package python-snappy lz4 zstandard

# 5. Configura .env per Kafka
# Aggiungi alla fine del file .env:
@"

# ========================================
# KAFKA CONFIGURATION - COLLAUDO
# ========================================

# Feature Flag
KAFKA_ENABLED=true

# Connection
KAFKA_BOOTSTRAP_SERVERS=<KAFKA_BROKER_COLLAUDO>:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=<USERNAME_COLLAUDO>
KAFKA_SASL_PASSWORD=<PASSWORD_COLLAUDO>

# Producer Settings
KAFKA_COMPRESSION_TYPE=snappy
KAFKA_BATCH_SIZE=16384
KAFKA_LINGER_MS=10
KAFKA_ACKS=all
KAFKA_ENABLE_IDEMPOTENCE=true
KAFKA_MAX_IN_FLIGHT_REQUESTS=5
KAFKA_REQUEST_TIMEOUT_MS=30000

# Default Export Settings
KAFKA_DEFAULT_TOPIC=pstt-traces-collaudo
KAFKA_DEFAULT_BATCH_SIZE=100
KAFKA_DEFAULT_INCLUDE_METADATA=true

"@ | Out-File -FilePath ".env" -Append -Encoding UTF8

# 6. Configura connections.json (aggiungi kafka_connections)
# Editare manualmente connections.json e aggiungere sezione kafka_connections

# 7. Test connessione Kafka (senza avviare servizio)
.\.venv\Scripts\python.exe -c @"
import asyncio
from app.core.config import get_kafka_config
from app.services.kafka_service import KafkaService

async def test_connection():
    config = get_kafka_config()
    async with KafkaService(config) as kafka:
        health = await kafka.health_check()
        print(f'✅ Connessione Kafka OK: {health.connected}')
        print(f'   Brokers: {health.broker_count}')
        print(f'   Latency: {health.latency_ms}ms')

asyncio.run(test_connection())
"@

# 8. Start servizio
.\manage_service.ps1 -action start

# 9. Verifica health
Start-Sleep -Seconds 10
Invoke-WebRequest -Uri "http://localhost:8000/api/monitoring/health" | Select-Object -ExpandProperty Content
```

### 1.3 Verifiche Post-Deploy Collaudo

```powershell
# Dashboard Kafka
Start-Process "http://localhost:8000/kafka"

# API Health Check
$health = Invoke-RestMethod -Uri "http://localhost:8000/api/kafka/health"
Write-Host "Kafka Connected: $($health.connected)"

# Metriche
$metrics = Invoke-RestMethod -Uri "http://localhost:8000/api/kafka/metrics/summary"
Write-Host "Total Messages Sent: $($metrics.total_sent)"
```

---

## 🧪 Fase 2: Test in Collaudo (1 settimana)

### 2.1 Creazione Job Test

**Via UI (http://collaudo-server:8000/scheduler):**

1. Click "Aggiungi nuova schedulazione"
2. Compila form:
   - **Query**: Seleziona query semplice (es. query che restituisce max 100 righe)
   - **Connessione**: CDG o altra disponibile
   - **Modalità**: Classic
   - **Ora**: 09:00 (ogni giorno alle 9)
   - **Giorni settimana**: Lun-Ven
   - **Condivisione**: **Kafka**
   - **Kafka Topic**: `pstt-traces-collaudo`
   - **Key Field**: Campo chiave dalla query (es. `BARCODE`)
   - **Batch Size**: 100
   - **Include Metadata**: ✓ checked
3. Salva schedulazione

### 2.2 Monitoring Giornaliero (7 giorni)

**Daily Check (ogni mattina alle 10:00):**

```powershell
# Script: tools/kafka_daily_check.ps1
$date = Get-Date -Format "yyyy-MM-dd"

Write-Host "=== Kafka Daily Check - $date ===" -ForegroundColor Cyan

# 1. Health Status
$health = Invoke-RestMethod -Uri "http://localhost:8000/api/kafka/health"
if ($health.connected) {
    Write-Host "✅ Kafka Connected (Latency: $($health.latency_ms)ms)" -ForegroundColor Green
} else {
    Write-Host "❌ Kafka Disconnected!" -ForegroundColor Red
}

# 2. Metriche ultime 24h
$metrics = Invoke-RestMethod -Uri "http://localhost:8000/api/kafka/metrics/hourly?hours=24"
$total = $metrics | Measure-Object -Property messages_sent -Sum
Write-Host "📊 Messages sent (24h): $($total.Sum)"

# 3. Success Rate
$summary = Invoke-RestMethod -Uri "http://localhost:8000/api/kafka/metrics/summary"
$successRate = [math]::Round(($summary.total_sent / ($summary.total_sent + $summary.total_failed)) * 100, 2)
Write-Host "✅ Success Rate: $successRate%"

# 4. Latency Stats
Write-Host "⏱️  Avg Latency: $($summary.avg_latency_ms)ms"
Write-Host "⏱️  P90 Latency: $($summary.p90_latency_ms)ms"
Write-Host "⏱️  P99 Latency: $($summary.p99_latency_ms)ms"

# 5. Errori recenti (ultimi 10 log errors)
$errors = Get-Content "logs\pstt_errors.log" -Tail 10 | Where-Object { $_ -match "kafka" }
if ($errors) {
    Write-Host "⚠️  Errori recenti:" -ForegroundColor Yellow
    $errors | ForEach-Object { Write-Host "   $_" }
} else {
    Write-Host "✅ Nessun errore Kafka" -ForegroundColor Green
}
```

### 2.3 Criteri di Successo (1 settimana)

- ✅ Success rate >= 99%
- ✅ Latency P99 < 500ms
- ✅ Zero crash dell'applicazione
- ✅ Nessun alert critico
- ✅ Risorse sistema stabili (CPU < 70%, RAM < 80%)

---

## 🚀 Fase 3: Rollout Graduale Produzione

### 3.1 Deploy Produzione (Settimana 2)

**Ripetere procedure Fase 1 su ambiente PRODUZIONE:**
- Stessi step 1.1-1.3
- Usare credenziali Kafka produzione
- Topic: `pstt-traces-prod`
- **NON creare ancora job schedulati**

### 3.2 Rollout Progressivo (Settimana 3-4)

**Settimana 3: 1 Job Semplice**
- Scegliere query più semplice e affidabile
- Schedulazione: 1 volta/giorno off-peak (es. 03:00)
- Monitorare quotidianamente

**Settimana 4: Aggiungere Job Progressivamente**
- Giorno 1-2: +1 job (totale 2)
- Giorno 3-4: +1 job (totale 3)
- Giorno 5-7: +2 job (totale 5)
- Obiettivo: Raggiungere 20K+ messaggi/giorno

### 3.3 Monitoring Post-Deploy (2 settimane)

**Daily Dashboard Review:**
- http://prod-server:8000/kafka
- Verificare grafici throughput e latency
- Controllare breakdown per topic

**Weekly Report:**
```powershell
# Script: tools/kafka_weekly_report.ps1
# Genera report con metriche aggregate settimanali
# Esporta in Excel o invia via email
```

---

## 🔄 Piano Rollback

### Quando Fare Rollback?

🚨 **Criteri di Rollback Automatico:**
- Success rate < 95% per 24h consecutive
- Crash applicazione > 2 volte in 24h
- Latency P99 > 2000ms costantemente
- Impatto su funzionalità esistenti (filesystem/email)

### Procedura Rollback

**STEP 1: Disabilitare Job Kafka**

Via UI o API:
```powershell
# Ottieni lista job Kafka
$jobs = Invoke-RestMethod -Uri "http://localhost:8000/api/scheduler/scheduling"
$kafkaJobs = $jobs | Where-Object { $_.sharing_mode -eq "kafka" }

# Disabilita ogni job Kafka
foreach ($job in $kafkaJobs) {
    Write-Host "Disabling job: $($job.query)"
    # Eliminare o modificare via UI cambiando sharing_mode a filesystem
}
```

**STEP 2: Verificare Sistema Stabile**

```powershell
# Health check
$health = Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/health"
if ($health.status -eq "healthy") {
    Write-Host "✅ Sistema stabile dopo disabilitazione Kafka"
}

# Verificare job filesystem/email funzionanti
$history = Invoke-RestMethod -Uri "http://localhost:8000/api/scheduler/history"
$recentSuccess = $history | Where-Object { $_.status -eq "success" -and $_.export_mode -ne "kafka" }
Write-Host "Job non-Kafka recenti: $($recentSuccess.Count)"
```

**STEP 3: Rollback Codice (opzionale)**

Se problema grave nel codice:
```powershell
# Stop servizio
.\manage_service.ps1 -action stop

# Restore backup configurazioni
Copy-Item "connections.json.backup_*" "connections.json"
Copy-Item ".env.backup_*" ".env"

# Git checkout previous version
git checkout v1.0.4-pre-kafka

# Reinstall dependencies (senza Kafka)
.\.venv\Scripts\python.exe -m pip uninstall -y kafka-python-ng aiokafka

# Restart servizio
.\manage_service.ps1 -action start
```

**STEP 4: Root Cause Analysis**

1. Raccogliere log:
   ```powershell
   # Copia log in folder diagnostics
   $diagDir = "diagnostics\kafka_issue_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
   New-Item -ItemType Directory -Path $diagDir
   Copy-Item "logs\*.log" $diagDir
   Copy-Item "exports\scheduler_history.json" $diagDir
   Copy-Item "exports\scheduler_metrics.json" $diagDir
   ```

2. Analizzare errori con KAFKA_RUNBOOK.md (sezione Emergency Scenarios)

3. Fix e re-test su collaudo prima di ri-deploy produzione

---

## 📋 Deliverable STEP 8

- [x] DEPLOY_KAFKA_CHECKLIST.md (questo documento)
- [ ] Pacchetto deploy creato (kafka_deploy_YYYYMMDD.zip)
- [ ] Deploy su collaudo completato
- [ ] 1 settimana monitoring collaudo (daily checks)
- [ ] Deploy su produzione completato
- [ ] Rollout graduale produzione (settimana 3-4)
- [ ] Documentazione post-deploy (lessons learned)

---

## 📞 Contatti e Escalation

**In caso di problemi critici:**

1. **Livello 1 - Dev Team**: Analisi log, fix codice
2. **Livello 2 - Infrastructure**: Kafka broker, network, credenziali
3. **Livello 3 - Vendor**: Supporto Kafka enterprise (se disponibile)

**Riferimenti:**
- KAFKA_SETUP.md: Troubleshooting section
- KAFKA_RUNBOOK.md: Emergency scenarios
- KAFKA_INTEGRATION_PLAN.md: Architettura completa
