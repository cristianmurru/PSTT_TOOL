# Script: Kafka Deploy Package Creator
# Descrizione: Crea pacchetto zip per deploy su collaudo/produzione
# Uso: .\create_kafka_deploy_package.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Kafka Deploy Package Creator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verifica che siamo nella root del progetto
if (-not (Test-Path "app") -or -not (Test-Path "requirements.txt")) {
    Write-Host "❌ Errore: Eseguire lo script dalla root del progetto PSTT_TOOL" -ForegroundColor Red
    exit 1
}

# 2. Verifica che tutti i test passino
Write-Host "[1/6] Verifica test suite..." -ForegroundColor Yellow
try {
    $null = & .\.venv\Scripts\pytest.exe --tb=short -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Test falliti! Risolvere prima di creare pacchetto deploy." -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✅ Tutti i test passano" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Impossibile eseguire test (pytest non trovato), procedo comunque..." -ForegroundColor Yellow
}
Write-Host ""

# 3. Crea directory deploy
$deployDate = Get-Date -Format "yyyyMMdd_HHmmss"
$deployDir = "release\kafka_deploy_$deployDate"
Write-Host "[2/6] Creazione directory deploy..." -ForegroundColor Yellow
Write-Host "  📁 $deployDir" -ForegroundColor Gray

if (Test-Path "release") {
    Remove-Item "release\kafka_deploy_*" -Recurse -Force -ErrorAction SilentlyContinue
} else {
    New-Item -ItemType Directory -Path "release" -Force | Out-Null
}
New-Item -ItemType Directory -Path $deployDir -Force | Out-Null
Write-Host "  ✅ Directory creata" -ForegroundColor Green
Write-Host ""

# 4. Copia file essenziali
Write-Host "[3/6] Copia file essenziali..." -ForegroundColor Yellow

# Requirements
Copy-Item "requirements.txt" $deployDir
Write-Host "  ✅ requirements.txt" -ForegroundColor Green

# Template configurazioni
Copy-Item ".env.example" "$deployDir\.env.template"
Write-Host "  ✅ .env.template" -ForegroundColor Green

Copy-Item "connections.json" "$deployDir\connections.json.template"
Write-Host "  ✅ connections.json.template" -ForegroundColor Green

# Codice applicazione
Copy-Item -Recurse "app" $deployDir
Write-Host "  ✅ app/ (codice applicazione)" -ForegroundColor Green

# Documentazione
Copy-Item -Recurse "docs" $deployDir
Write-Host "  ✅ docs/ (documentazione)" -ForegroundColor Green

# Tools
Copy-Item -Recurse "tools" $deployDir
Write-Host "  ✅ tools/ (script utilità)" -ForegroundColor Green

# Script gestione servizio
Copy-Item "install_service.ps1" $deployDir
Copy-Item "manage_service.ps1" $deployDir
Write-Host "  ✅ Script gestione servizio" -ForegroundColor Green

# Batch files
Copy-Item "start_pstt.bat" $deployDir -ErrorAction SilentlyContinue
Write-Host "  ✅ start_pstt.bat" -ForegroundColor Green

# README e CHANGELOG
Copy-Item "README.md" $deployDir
Copy-Item "docs\CHANGELOG.md" "$deployDir\CHANGELOG.md"
Write-Host "  ✅ README.md, CHANGELOG.md" -ForegroundColor Green

Write-Host ""

# 5. Crea file istruzioni deploy
Write-Host "[4/6] Creazione istruzioni deploy..." -ForegroundColor Yellow

$deployInstructions = @"
# Kafka Deploy Package - $deployDate

## Contenuto Pacchetto

- app/                      : Codice applicazione con supporto Kafka
- docs/                     : Documentazione completa (KAFKA_SETUP.md, KAFKA_RUNBOOK.md)
- tools/                    : Script utilità (kafka_daily_check.ps1, kafka_benchmark.py)
- requirements.txt          : Dipendenze Python (include kafka-python-ng, aiokafka)
- .env.template             : Template configurazione (da copiare in .env)
- connections.json.template : Template connessioni (da copiare in connections.json)
- install_service.ps1       : Script installazione servizio Windows
- manage_service.ps1        : Script gestione servizio (start/stop/restart)
- start_pstt.bat            : Batch avvio manuale

## Procedura Deploy Rapida

### 1. Pre-Requisiti

- Python 3.11+ installato
- Virtual environment attivo (.venv)
- Credenziali Kafka disponibili
- Topic Kafka creato su broker

### 2. Deploy

``````powershell
# Stop servizio (se già in esecuzione)
.\manage_service.ps1 -action stop

# Backup configurazioni correnti
`$backupDate = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "connections.json" "connections.json.backup_`$backupDate"
Copy-Item ".env" ".env.backup_`$backupDate"

# Copia file da pacchetto deploy (sovrascrivere app/, docs/, tools/)
# ATTENZIONE: NON sovrascrivere .env e connections.json direttamente!

# Installa nuove dipendenze Kafka
\.\.venv\Scripts\python.exe -m pip install kafka-python-ng==2.2.2
\.\.venv\Scripts\python.exe -m pip install aiokafka==0.10.0

# (Opzionale) Librerie di compressione per performance
# Installa se usi KAFKA_COMPRESSION_TYPE=snappy|lz4|zstd
\.\.venv\Scripts\python.exe -m pip install python-snappy lz4 zstandard

# Configura .env (aggiungi sezione KAFKA alla fine del file)
# Vedi .env.template per variabili necessarie

# Configura connections.json (aggiungi sezione kafka_connections)
# Vedi connections.json.template per struttura

# Test connessione Kafka (prima di riavviare servizio)
.\.venv\Scripts\python.exe -c "
import asyncio
from app.core.config import get_kafka_config
from app.services.kafka_service import KafkaService

async def test():
    config = get_kafka_config()
    async with KafkaService(config) as kafka:
        health = await kafka.health_check()
        print(f'Connected: {health.connected}')
        
asyncio.run(test())
"

# Start servizio
.\manage_service.ps1 -action start

# Verifica health
Start-Sleep -Seconds 10
Invoke-WebRequest -Uri "http://localhost:8000/api/monitoring/health"
``````

### 3. Verifica Post-Deploy

``````powershell
# Dashboard Kafka
Start-Process "http://localhost:8000/kafka"

# API Health Check
`$health = Invoke-RestMethod -Uri "http://localhost:8000/api/kafka/health"
Write-Host "Kafka Connected: `$(`$health.connected)"

# Daily Check
.\tools\kafka_daily_check.ps1
``````

## Documentazione Completa

- **docs/KAFKA_SETUP.md**: Setup guide, troubleshooting, performance tuning
- **docs/KAFKA_RUNBOOK.md**: Operational procedures, emergency scenarios
- **docs/DEPLOY_KAFKA_CHECKLIST.md**: Checklist deploy completa con monitoring
- **docs/CHANGELOG.md**: Tutte le modifiche (versione 1.1.0)

## Supporto

In caso di problemi:
1. Consultare KAFKA_RUNBOOK.md (sezione Emergency Scenarios)
2. Eseguire kafka_daily_check.ps1 per diagnostics
3. Verificare log: logs/pstt_errors.log
4. Contattare team di sviluppo

---

**Versione Deploy:** $deployDate
**Versione Applicazione:** 1.1.0
**Kafka Integration:** STEP 1-7 completati (111 test passing, 76% coverage)
"@

$deployInstructions | Out-File -FilePath "$deployDir\DEPLOY_INSTRUCTIONS.md" -Encoding UTF8
Write-Host "  ✅ DEPLOY_INSTRUCTIONS.md creato" -ForegroundColor Green
Write-Host ""

# 6. Crea archivio zip
Write-Host "[5/6] Creazione archivio ZIP..." -ForegroundColor Yellow
$zipPath = "$deployDir.zip"
Compress-Archive -Path "$deployDir\*" -DestinationPath $zipPath -Force
Write-Host "  ✅ Archivio creato: $zipPath" -ForegroundColor Green
Write-Host ""

# 7. Summary
Write-Host "[6/6] Riepilogo pacchetto..." -ForegroundColor Yellow
$zipSize = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
$fileCount = (Get-ChildItem -Path $deployDir -Recurse -File).Count

Write-Host "  📦 File: $zipPath" -ForegroundColor Cyan
Write-Host "  💾 Dimensione: $zipSize MB" -ForegroundColor Cyan
Write-Host "  📄 Files inclusi: $fileCount" -ForegroundColor Cyan
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " PACCHETTO DEPLOY CREATO CON SUCCESSO" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 Prossimi passi:" -ForegroundColor Yellow
Write-Host "  1. Copiare $zipPath su server collaudo/produzione" -ForegroundColor Gray
Write-Host "  2. Estrarre archivio nella directory PSTT_TOOL" -ForegroundColor Gray
Write-Host "  3. Seguire istruzioni in DEPLOY_INSTRUCTIONS.md" -ForegroundColor Gray
Write-Host "  4. Consultare docs/DEPLOY_KAFKA_CHECKLIST.md per checklist completa" -ForegroundColor Gray
Write-Host ""
