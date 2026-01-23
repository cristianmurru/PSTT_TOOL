# Script per risolvere problemi avvio servizio PSTT_Tool
# Encoding: UTF-8

$ErrorActionPreference = "Stop"
$projectRoot = "C:\app\pstt_tool"

Write-Host "=== Fix PSTT_Tool - Macchina Collaudo ===" -ForegroundColor Cyan

# 1. Crea directories mancanti
Write-Host ""
Write-Host "[1/5] Creazione directories necessarie..." -ForegroundColor Yellow
$dirs = @(
    "$projectRoot\exports",
    "$projectRoot\exports\_tmp",
    "$projectRoot\logs"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  [OK] Creata: $dir" -ForegroundColor Green
    } else {
        Write-Host "  [OK] Esiste: $dir" -ForegroundColor Gray
    }
}

# 2. Verifica venv Python
Write-Host ""
Write-Host "[2/5] Verifica Python virtual environment..." -ForegroundColor Yellow
$pythonExe = "$projectRoot\.venv\Scripts\python.exe"
if (Test-Path $pythonExe) {
    Write-Host "  [OK] Python trovato: $pythonExe" -ForegroundColor Green
    & $pythonExe --version
} else {
    Write-Host "  [ERRORE] Python non trovato in $pythonExe" -ForegroundColor Red
    exit 1
}

# 3. Verifica file main.py
Write-Host ""
Write-Host "[3/5] Verifica main.py..." -ForegroundColor Yellow
$mainPy = "$projectRoot\main.py"
if (Test-Path $mainPy) {
    Write-Host "  [OK] main.py trovato" -ForegroundColor Green
} else {
    Write-Host "  [ERRORE] main.py non trovato" -ForegroundColor Red
    exit 1
}

# 4. Verifica NSSM
Write-Host ""
Write-Host "[4/5] Verifica configurazione servizio..." -ForegroundColor Yellow
try {
    $nssmStatus = nssm status PSTT_Tool 2>&1
    Write-Host "  Stato attuale: $nssmStatus" -ForegroundColor Cyan
    
    Write-Host "  Parametri servizio:" -ForegroundColor Cyan
    $appPath = nssm get PSTT_Tool Application
    $appParams = nssm get PSTT_Tool AppParameters
    $appDir = nssm get PSTT_Tool AppDirectory
    
    Write-Host "    Application: $appPath" -ForegroundColor Gray
    Write-Host "    Parameters: $appParams" -ForegroundColor Gray
    Write-Host "    Directory: $appDir" -ForegroundColor Gray
} catch {
    Write-Host "  [WARNING] Impossibile interrogare NSSM" -ForegroundColor Yellow
}

# 5. Test avvio manuale
Write-Host ""
Write-Host "[5/5] Test avvio manuale applicazione..." -ForegroundColor Yellow
Write-Host "  Avvio su porta 8001 per 5 secondi..." -ForegroundColor Gray

Set-Location $projectRoot

$job = Start-Job -ScriptBlock {
    param($root, $python)
    Set-Location $root
    & $python main.py --port 8001 2>&1
} -ArgumentList $projectRoot, $pythonExe

Start-Sleep -Seconds 5

$jobState = $job.State
if ($jobState -eq "Running") {
    Write-Host "  [OK] Applicazione avviata correttamente!" -ForegroundColor Green
    Stop-Job -Job $job
} else {
    Write-Host "  [ERRORE] Applicazione crashata!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Output completo:" -ForegroundColor Yellow
    Receive-Job -Job $job
}

Remove-Job -Job $job -Force

Write-Host ""
Write-Host "=== Riepilogo ===" -ForegroundColor Cyan
Write-Host "Comandi per avviare il servizio:" -ForegroundColor White
Write-Host "  nssm start PSTT_Tool" -ForegroundColor Yellow
Write-Host ""
Write-Host "Comandi diagnostici:" -ForegroundColor White
Write-Host "  nssm status PSTT_Tool" -ForegroundColor Gray
Write-Host "  Get-Content C:\app\pstt_tool\logs\service_stderr.log -Tail 50" -ForegroundColor Gray
Write-Host "  Get-Content C:\app\pstt_tool\logs\service_stdout.log -Tail 50" -ForegroundColor Gray
