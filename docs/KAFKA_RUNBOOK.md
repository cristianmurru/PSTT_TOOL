# Runbook Operativo - Kafka Integration

**Guida per Operations e Troubleshooting**  
**Data:** 20 Gennaio 2026  
**Versione:** 1.0  
**Target:** Operations Team, SRE, Support

---

## 📋 Indice

1. [Overview Sistema](#overview-sistema)
2. [Procedure Standard](#procedure-standard)
3. [Scenari di Emergenza](#scenari-di-emergenza)
4. [Escalation Matrix](#escalation-matrix)
5. [Health Check Giornaliero](#health-check-giornaliero)
6. [Alerting e Monitoring](#alerting-e-monitoring)

---

## 🔍 Overview Sistema

### Architettura Kafka Integration

```
┌─────────────────────────────────────────────────────┐
│  PSTT Tool (Windows Service)                        │
│                                                      │
│  ┌──────────────┐         ┌──────────────┐         │
│  │  Scheduler   │────────▶│ KafkaService │         │
│  │  (APScheduler)│         │ (Producer)   │         │
│  └──────────────┘         └──────┬───────┘         │
│                                   │                  │
└───────────────────────────────────┼──────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │  Kafka Cluster   │
                          │  (3+ brokers)    │
                          └──────────────────┘
```

### Componenti Critici

| Componente | Tipo | Criticità | Monitoraggio |
|------------|------|-----------|--------------|
| PSTT Service | Windows Service | 🔴 Critico | Service Status |
| Kafka Producer | Python Library | 🔴 Critico | Health Check API |
| Kafka Cluster | Infrastruttura | 🔴 Critico | Kafka Monitoring |
| Scheduler Jobs | Application | 🟡 Medio | Job History |
| Metriche Storage | JSON File | 🟢 Basso | File Size |

### SLA e Obiettivi

| Metrica | Target | Warning | Critical |
|---------|--------|---------|----------|
| Uptime Servizio | 99.5% | < 99% | < 95% |
| Success Rate Messaggi | > 99% | < 98% | < 95% |
| Latenza p99 | < 500ms | > 1000ms | > 5000ms |
| Job Failure Rate | < 1% | > 2% | > 5% |

---

## 📝 Procedure Standard

### Procedura 1: Avvio Servizio

**Quando:** Dopo manutenzione, reboot, deploy

```powershell
# 1. Verifica prerequisiti
Get-Service PSTT_Service
Test-NetConnection kafka-broker.example.com -Port 9092

# 2. Avvia servizio
Start-Service PSTT_Service

# 3. Attendi 30 secondi per inizializzazione
Start-Sleep -Seconds 30

# 4. Verifica health check
Invoke-RestMethod http://localhost:8000/api/kafka/health

# 5. Verifica log
Get-Content C:\App\PSTT_TOOL\logs\pstt_*.log -Tail 20
```

**Output atteso:**
```json
{
  "status": "healthy",
  "connected": true,
  "producer_ready": true
}
```

---

### Procedura 2: Stop Servizio (Graceful)

**Quando:** Manutenzione programmata, deploy, upgrade

```powershell
# 1. Disabilita job schedulati (via UI)
# Apri: http://localhost:8000/scheduler
# Disabilita tutti i job Kafka

# 2. Attendi completamento job in corso (max 10 min)
Start-Sleep -Seconds 600

# 3. Stop servizio
Stop-Service PSTT_Service

# 4. Verifica stop completo
Get-Service PSTT_Service
# Status = Stopped

# 5. Backup configurazioni (opzionale)
Copy-Item C:\App\PSTT_TOOL\.env C:\Backup\.env_$(Get-Date -Format "yyyyMMdd_HHmmss")
```

---

### Procedura 3: Restart Servizio

**Quando:** Dopo cambio configurazione, problemi prestazioni

```powershell
# Script automatizzato
C:\App\PSTT_TOOL\tools\manage_service.ps1 -action restart

# Oppure manualmente:
Restart-Service PSTT_Service

# Verifica health
Start-Sleep -Seconds 30
Invoke-RestMethod http://localhost:8000/api/kafka/health
```

---

### Procedura 4: Verifica Giornaliera

**Quando:** Ogni mattina (automazione via task scheduler)

```powershell
# File: tools/daily_check.ps1

# 1. Status servizio
$service = Get-Service PSTT_Service
if ($service.Status -ne "Running") {
    Write-Error "❌ Servizio non running!"
    exit 1
}

# 2. Health check Kafka
$health = Invoke-RestMethod http://localhost:8000/api/kafka/health
if (-not $health.connected) {
    Write-Error "❌ Kafka non connesso!"
    exit 1
}

# 3. Metriche ultime 24h
$metrics = Invoke-RestMethod "http://localhost:8000/api/kafka/metrics/summary?period=today"
Write-Host "✅ Messaggi inviati oggi: $($metrics.total_messages)"
Write-Host "✅ Success rate: $($metrics.success_rate)%"

if ($metrics.success_rate -lt 98) {
    Write-Warning "⚠️ Success rate < 98%!"
}

# 4. Job falliti
$history = Invoke-RestMethod "http://localhost:8000/api/scheduler/history?limit=100"
$failed = $history | Where-Object { $_.status -eq "error" -and $_.export_format -eq "kafka" }

if ($failed.Count -gt 0) {
    Write-Warning "⚠️ $($failed.Count) job Kafka falliti nelle ultime 24h"
}

Write-Host "✅ Daily check completato"
```

**Esecuzione:**
```powershell
.\tools\daily_check.ps1
```

---

### Procedura 5: Cambio Credenziali Kafka

**Quando:** Rotazione credenziali, security update

```powershell
# 1. Prepara nuove credenziali
# File: .env.new
# KAFKA_SASL_USERNAME=pstt-producer-new
# KAFKA_SASL_PASSWORD=new-password

# 2. Test nuove credenziali (NON in produzione)
$testRequest = @{
    bootstrap_servers = "kafka-broker:9092"
    security_protocol = "SASL_SSL"
    sasl_mechanism = "PLAIN"
    sasl_username = "pstt-producer-new"
    sasl_password = "new-password"
} | ConvertTo-Json

Invoke-RestMethod http://localhost:8000/api/kafka/test `
    -Method POST `
    -ContentType "application/json" `
    -Body $testRequest

# 3. Backup configurazione corrente
Copy-Item .env .env.backup_$(Get-Date -Format "yyyyMMdd_HHmmss")

# 4. Applica nuove credenziali
Copy-Item .env.new .env

# 5. Restart servizio (finestra manutenzione)
Stop-Service PSTT_Service
Start-Sleep -Seconds 5
Start-Service PSTT_Service

# 6. Verifica connessione
Start-Sleep -Seconds 30
Invoke-RestMethod http://localhost:8000/api/kafka/health

# 7. Test invio messaggio
$testMsg = @{
    topic = "pstt-test"
    key = "test-$(Get-Date -Format "yyyyMMddHHmmss")"
    value = @{ test = "Credential rotation test" }
} | ConvertTo-Json

Invoke-RestMethod http://localhost:8000/api/kafka/send `
    -Method POST `
    -ContentType "application/json" `
    -Body $testMsg

Write-Host "✅ Rotazione credenziali completata"
```

---

## 🚨 Scenari di Emergenza

### Scenario 1: Producer Disconnesso

**Sintomo:**
```
Dashboard: 🔴 Disconnected
API: {"connected": false}
Log: [KAFKA] ERROR: Connection timeout
```

**Severità:** 🔴 **CRITICO** - Nessun messaggio viene inviato

**Diagnosi (5 min):**

```powershell
# Step 1: Verifica servizio PSTT
Get-Service PSTT_Service
# Se Stopped → Restart

# Step 2: Verifica connettività rete
Test-NetConnection kafka-broker.example.com -Port 9092
# Se fallisce → Problema rete/firewall

# Step 3: Verifica log dettagliato
Get-Content C:\App\PSTT_TOOL\logs\pstt_errors_*.log -Tail 50 | Select-String "KAFKA"

# Step 4: Test connessione da API
Invoke-RestMethod http://localhost:8000/api/kafka/health
```

**Soluzione Rapida (10 min):**

1. **Se servizio stopped:**
   ```powershell
   Start-Service PSTT_Service
   Start-Sleep 30
   ```

2. **Se timeout rete:**
   ```powershell
   # Verifica firewall
   Test-NetConnection kafka-broker.example.com -Port 9092
   
   # Se fallisce, contatta team network
   # Escalation: Network Team
   ```

3. **Se errore autenticazione:**
   ```powershell
   # Verifica credenziali in .env
   Get-Content .env | Select-String "KAFKA_SASL"
   
   # Test credenziali
   # Escalation: Kafka Team per verifica ACL
   ```

4. **Restart forzato:**
   ```powershell
   Restart-Service PSTT_Service -Force
   Start-Sleep 30
   Invoke-RestMethod http://localhost:8000/api/kafka/health
   ```

**Fallback (se problema persiste):**
```powershell
# Disabilita job Kafka temporaneamente
# Via UI: http://localhost:8000/scheduler
# Imposta enabled=false per tutti i job kafka

# Sistema continua a funzionare per export Excel/CSV
```

**Escalation:** Se non risolto in 30 min → Kafka Team + Application Team

---

### Scenario 2: Alta Latenza (p99 > 5s)

**Sintomo:**
```
Dashboard: Avg Latency > 1000ms, p99 > 5000ms
Job: Durata 10x normale
```

**Severità:** 🟡 **MEDIO** - Sistema funziona ma lento

**Diagnosi (10 min):**

```powershell
# Step 1: Verifica metriche
$metrics = Invoke-RestMethod "http://localhost:8000/api/kafka/metrics/hourly?hours=6"
$metrics | ForEach-Object { 
    Write-Host "$($_.hour): avg=$($_.avg_latency_ms)ms, p99=$($_.p99_latency_ms)ms" 
}

# Step 2: Verifica dimensione messaggi
$summary = Invoke-RestMethod "http://localhost:8000/api/kafka/metrics/summary?period=today"
$avg_size = $summary.total_bytes / $summary.total_messages
Write-Host "Dimensione media messaggio: $avg_size bytes"

# Step 3: Verifica job in esecuzione
$running = Invoke-RestMethod "http://localhost:8000/api/scheduler/running"
Write-Host "Job in esecuzione: $($running.Count)"

# Step 4: Verifica risorse sistema
Get-Process -Name python | Select-Object CPU, WorkingSet64
```

**Soluzione Rapida (15 min):**

1. **Se messaggi grandi:**
   ```powershell
   # Abilita compressione in .env
   # KAFKA_COMPRESSION_TYPE=snappy
   Restart-Service PSTT_Service
   ```

2. **Se molti job paralleli:**
   ```powershell
   # Ridurre concorrenza scheduler
   # Nel scheduling config: max_workers ridotto
   ```

3. **Se problema Kafka cluster:**
   ```powershell
   # Contatta Kafka Team per verifica:
   # - Broker load
   # - Network latency
   # - Disk I/O
   ```

**Escalation:** Se p99 > 10s per > 1 ora → Application Team + Kafka Team

---

### Scenario 3: Job Kafka Falliscono Ripetutamente

**Sintomo:**
```
Scheduler History: Multipli job con status="error"
Email: Job failure notification
Log: [KAFKA_JOB] ERROR: ...
```

**Severità:** 🟡 **MEDIO** - Dati non inviati

**Diagnosi (10 min):**

```powershell
# Step 1: Identifica job problematici
$failed = Invoke-RestMethod "http://localhost:8000/api/scheduler/history?limit=100" |
    Where-Object { $_.status -eq "error" -and $_.export_format -eq "kafka" }

$failed | ForEach-Object {
    Write-Host "Job: $($_.scheduling_name)"
    Write-Host "Error: $($_.error_message)"
    Write-Host "---"
}

# Step 2: Verifica query SQL
# Testa manualmente la query del job fallito via UI

# Step 3: Verifica message_key_field
# Assicurati che campo esista nei risultati

# Step 4: Verifica connessione Kafka
Invoke-RestMethod http://localhost:8000/api/kafka/health
```

**Soluzione Rapida (15 min):**

1. **Se errore query SQL:**
   ```powershell
   # Correggi query e salva
   # Re-esegui job: "Esegui Ora" in UI
   ```

2. **Se message_key_field mancante:**
   ```powershell
   # Modifica configurazione job
   # Imposta message_key_field corretto
   ```

3. **Se timeout query:**
   ```powershell
   # Aumenta timeout in config job
   # "timeout": 7200  (2 ore)
   ```

4. **Retry manuale:**
   ```powershell
   # Via UI: http://localhost:8000/scheduler
   # Trova job fallito → "Esegui Ora"
   ```

**Escalation:** Se > 5 job falliti consecutivi → Application Team

---

### Scenario 4: Disco Pieno (Metriche JSON)

**Sintomo:**
```
Log: [ERROR] Cannot write to kafka_metrics.json: Disk full
Dashboard: Metriche non aggiornate
```

**Severità:** 🟢 **BASSO** - Non impatta invio messaggi

**Diagnosi (5 min):**

```powershell
# Step 1: Verifica spazio disco
Get-PSDrive C | Select-Object Used, Free

# Step 2: Verifica dimensione file metriche
Get-ChildItem C:\App\PSTT_TOOL\exports\kafka_metrics.json | 
    Select-Object Name, Length

# Step 3: Conta entries metriche
$metrics = Get-Content C:\App\PSTT_TOOL\exports\kafka_metrics.json | ConvertFrom-Json
Write-Host "Entries totali: $($metrics.Count)"
```

**Soluzione Rapida (5 min):**

```powershell
# Cleanup metriche vecchie (> 30 giorni)
Invoke-RestMethod -Method POST "http://localhost:8000/api/kafka/metrics/cleanup?days=30"

# Verifica riduzione dimensione
Get-ChildItem C:\App\PSTT_TOOL\exports\kafka_metrics.json | 
    Select-Object Name, Length
```

**Prevenzione:**
```powershell
# Aggiungi task scheduler settimanale
# Task: Cleanup metriche > 90 giorni
# Schedule: Ogni domenica 02:00
```

---

### Scenario 5: Memory Leak / High Memory Usage

**Sintomo:**
```
Task Manager: python.exe usa > 2GB RAM
Log: OutOfMemoryError
Sistema: Lento, swap elevato
```

**Severità:** 🔴 **CRITICO** - Rischio crash servizio

**Diagnosi (10 min):**

```powershell
# Step 1: Verifica memoria processo
Get-Process -Name python | Select-Object CPU, WorkingSet64, VirtualMemorySize64

# Step 2: Verifica batch size job
$schedulings = Invoke-RestMethod "http://localhost:8000/api/scheduler/scheduling"
$schedulings | Where-Object { $_.export_format -eq "kafka" } | 
    Select-Object name, @{N="BatchSize";E={$_.kafka_config.batch_size}}

# Step 3: Verifica job in esecuzione
$running = Invoke-RestMethod "http://localhost:8000/api/scheduler/running"
Write-Host "Job attivi: $($running.Count)"
```

**Soluzione Rapida (15 min):**

1. **Restart immediato:**
   ```powershell
   Restart-Service PSTT_Service -Force
   ```

2. **Riduci batch size:**
   ```powershell
   # Modifica job con batch > 500
   # Imposta batch_size = 100
   ```

3. **Limita concorrenza:**
   ```powershell
   # In scheduler config
   # max_workers = 2 (default: 5)
   ```

**Prevenzione:**
```powershell
# Monitor memoria continuo (task ogni 15 min)
$mem = (Get-Process -Name python).WorkingSet64 / 1GB
if ($mem -gt 2) {
    Write-Warning "Memory usage: $mem GB"
    Send-MailMessage -Subject "PSTT High Memory" ...
}
```

**Escalation:** Se leak persiste dopo restart → Application Team (possibile bug)

---

## 📊 Health Check Giornaliero

### Checklist Manuale (5 min)

```
□ Servizio PSTT_Service = Running
□ Dashboard Kafka = 🟢 Connected  
□ Success Rate oggi ≥ 99%
□ Latenza p99 < 500ms
□ Nessun job fallito nelle ultime 24h
□ Dimensione kafka_metrics.json < 50MB
□ Memoria processo python < 1GB
□ Spazio disco C:\ > 20%
```

### Script Automatizzato

File: `tools/health_check.ps1`

```powershell
# Health Check Automatizzato PSTT Tool - Kafka Integration
# Esegui via Task Scheduler: Ogni giorno 08:00

$ErrorActionPreference = "Continue"
$report = @()

# 1. Service Status
$service = Get-Service PSTT_Service -ErrorAction SilentlyContinue
if ($service.Status -eq "Running") {
    $report += "✅ Servizio: Running"
} else {
    $report += "❌ Servizio: $($service.Status)"
}

# 2. Kafka Health
try {
    $health = Invoke-RestMethod http://localhost:8000/api/kafka/health -TimeoutSec 10
    if ($health.connected) {
        $report += "✅ Kafka: Connected"
    } else {
        $report += "❌ Kafka: Disconnected"
    }
} catch {
    $report += "❌ Kafka: Unreachable"
}

# 3. Metriche
try {
    $metrics = Invoke-RestMethod "http://localhost:8000/api/kafka/metrics/summary?period=today"
    $report += "📊 Messaggi oggi: $($metrics.total_messages)"
    $report += "📊 Success rate: $($metrics.success_rate)%"
    
    if ($metrics.success_rate -lt 99) {
        $report += "⚠️ WARNING: Success rate < 99%"
    }
    
    if ($metrics.avg_latency_ms -gt 500) {
        $report += "⚠️ WARNING: Alta latenza media"
    }
} catch {
    $report += "❌ Metriche non disponibili"
}

# 4. Job Falliti
try {
    $history = Invoke-RestMethod "http://localhost:8000/api/scheduler/history?limit=100"
    $failed = $history | Where-Object { 
        $_.status -eq "error" -and 
        $_.export_format -eq "kafka" -and
        $_.end_time -gt (Get-Date).AddHours(-24)
    }
    
    if ($failed.Count -eq 0) {
        $report += "✅ Job falliti: 0"
    } else {
        $report += "⚠️ Job falliti: $($failed.Count)"
    }
} catch {
    $report += "❌ History non disponibile"
}

# 5. Risorse
$process = Get-Process -Name python -ErrorAction SilentlyContinue | 
    Where-Object { $_.Path -like "*PSTT_TOOL*" }
if ($process) {
    $memGB = [math]::Round($process.WorkingSet64 / 1GB, 2)
    $report += "💾 Memoria: $memGB GB"
    
    if ($memGB -gt 2) {
        $report += "⚠️ WARNING: High memory usage"
    }
}

# 6. Disco
$drive = Get-PSDrive C
$freePercent = [math]::Round(($drive.Free / ($drive.Used + $drive.Free)) * 100, 1)
$report += "💿 Disco libero: $freePercent%"

if ($freePercent -lt 20) {
    $report += "⚠️ WARNING: Spazio disco < 20%"
}

# Output report
$report | ForEach-Object { Write-Host $_ }

# Salva report
$reportText = $report -join "`n"
$reportFile = "logs\health_check_$(Get-Date -Format 'yyyyMMdd').log"
$reportText | Out-File $reportFile -Append

# Email se ci sono warning/errori
$warnings = $report | Where-Object { $_ -match "⚠️|❌" }
if ($warnings.Count -gt 0) {
    $subject = "PSTT Tool - Kafka Health Check: Issues Found"
    $body = $report -join "`n"
    
    # Send-MailMessage -To "admin@example.com" -Subject $subject -Body $body -SmtpServer "smtp.example.com"
    Write-Warning "⚠️ $($warnings.Count) issue(s) trovati!"
}
```

**Setup Task Scheduler:**
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-File C:\App\PSTT_TOOL\tools\health_check.ps1"

$trigger = New-ScheduledTaskTrigger -Daily -At 08:00

Register-ScheduledTask -TaskName "PSTT_Kafka_HealthCheck" `
    -Action $action -Trigger $trigger `
    -Description "Daily health check PSTT Kafka integration"
```

---

## 🔔 Alerting e Monitoring

### Metriche da Monitorare

| Metrica | Fonte | Threshold Warning | Threshold Critical |
|---------|-------|-------------------|-------------------|
| Service Status | Windows Service | Stopped > 1min | Stopped > 5min |
| Kafka Connection | API /health | Disconnected > 5min | Disconnected > 15min |
| Success Rate | API /metrics/summary | < 98% | < 95% |
| Latenza p99 | API /metrics/summary | > 1000ms | > 5000ms |
| Job Failure Rate | API /history | > 2% | > 5% |
| Memory Usage | Process Monitor | > 1.5GB | > 2GB |
| Disk Free Space | System | < 30% | < 20% |

### Configurazione Alert Email

File: `.env` (aggiungi)

```bash
# Email Alerting
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=pstt-alerts@example.com
SMTP_PASSWORD=${SMTP_PASSWORD}
SMTP_FROM=pstt-tool@example.com
SMTP_TO=ops-team@example.com,kafka-team@example.com

# Alert Thresholds
ALERT_SUCCESS_RATE_WARNING=98
ALERT_SUCCESS_RATE_CRITICAL=95
ALERT_LATENCY_P99_WARNING=1000
ALERT_LATENCY_P99_CRITICAL=5000
```

### Integration con Monitoring Tools

#### Prometheus Metrics (Future)

```yaml
# prometheus.yml (esempio)
scrape_configs:
  - job_name: 'pstt-tool-kafka'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/kafka/metrics/prometheus'
    scrape_interval: 60s
```

#### Grafana Dashboard (Future)

```json
{
  "dashboard": {
    "title": "PSTT Tool - Kafka Integration",
    "panels": [
      {
        "title": "Messages Sent (24h)",
        "targets": [
          {
            "expr": "sum(kafka_messages_sent_total)"
          }
        ]
      },
      {
        "title": "Latency p99",
        "targets": [
          {
            "expr": "kafka_latency_p99_milliseconds"
          }
        ]
      }
    ]
  }
}
```

---

## 📞 Escalation Matrix

### Livelli di Escalation

**Livello 1: Operations Team (First Response)**
- Tempo risposta: 15 minuti
- Competenze: Restart servizi, verifica log base, checklist standard
- Contatto: ops-team@example.com, +39 XXX XXXXXXX

**Livello 2: Application Team (PSTT Tool Developers)**
- Tempo risposta: 1 ora
- Competenze: Debug application, analisi log, hotfix
- Contatto: pstt-dev@example.com, +39 XXX XXXXXXX
- Escalation: Se problema applicativo non risolvibile da Ops

**Livello 3: Kafka Team (Infrastructure)**
- Tempo risposta: 2 ore
- Competenze: Kafka cluster, network, security
- Contatto: kafka-team@example.com, +39 XXX XXXXXXX
- Escalation: Se problema infrastrutturale Kafka

**Livello 4: Management**
- Tempo risposta: Best effort
- Escalation: Se impatto business critico > 4 ore

### Matrice Decisionale

| Problema | Severità | First Response | Escalation |
|----------|----------|----------------|------------|
| Servizio stopped | 🔴 Critico | Ops: Restart | Se persiste 15min → App Team |
| Kafka disconnected | 🔴 Critico | Ops: Check network | Se persiste 15min → Kafka Team |
| Job fallito singolo | 🟢 Basso | Ops: Retry manuale | Se ripete 3x → App Team |
| Success rate < 95% | 🔴 Critico | Ops: Health check | Immediate → App Team + Kafka Team |
| Alta latenza | 🟡 Medio | Ops: Monitor | Se persiste 1h → Kafka Team |
| Memory leak | 🔴 Critico | Ops: Restart | Immediate → App Team |

### Contact List Template

```yaml
contacts:
  operations:
    - name: "Mario Rossi"
      role: "Ops Engineer"
      email: "mario.rossi@example.com"
      phone: "+39 XXX XXXXXXX"
      availability: "24/7"
  
  application:
    - name: "Luca Bianchi"
      role: "Senior Developer"
      email: "luca.bianchi@example.com"
      phone: "+39 XXX XXXXXXX"
      availability: "08:00-18:00 (On-call)"
  
  kafka:
    - name: "Giuseppe Verdi"
      role: "Kafka Admin"
      email: "giuseppe.verdi@example.com"
      phone: "+39 XXX XXXXXXX"
      availability: "08:00-18:00"

on_call_schedule:
  primary: "ops-oncall@example.com"
  backup: "ops-backup@example.com"
  escalation_email: "ops-manager@example.com"
```

---

## 📝 Change Log

| Data | Versione | Modifiche |
|------|----------|-----------|
| 2026-01-20 | 1.0 | Documento iniziale |

---

**Revisione successiva:** Trimestrale o dopo major incident  
**Owner:** Operations Team  
**Approvato da:** Tech Lead + Ops Manager
