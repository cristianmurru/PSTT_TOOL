<#
.SYNOPSIS
    Installa PSTT Tool come Windows Service usando NSSM
.DESCRIPTION
    Questo script configura e installa l'applicazione come servizio Windows
    con avvio automatico e riavvio in caso di failure.
.NOTES
    Richiede privilegi amministrativi.
    NSSM deve essere disponibile nel PATH o nella cartella corrente.
#>

#Requires -RunAsAdministrator

param(
    [string]$ServiceName = "PSTT_Tool",
    [string]$DisplayName = "PSTT Tool - Query Scheduler",
    [string]$Description = "Servizio per schedulazione e esecuzione automatica query Oracle/SQL Server",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# Verifica presenza NSSM (prima nel PATH, poi nelle cartelle locali)
$nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssmPath) {
    # Cerca nssm.exe nelle sottocartelle del progetto
    $localNssm = Get-ChildItem -Path $PSScriptRoot -Filter "nssm.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($localNssm) {
        Write-Host "NSSM trovato in: $($localNssm.FullName)" -ForegroundColor Cyan
        $nssmExe = $localNssm.FullName
        # Crea alias temporaneo per questa sessione
        Set-Alias -Name nssm -Value $nssmExe -Scope Script
    } else {
        Write-Error "NSSM non trovato nel PATH né nelle sottocartelle del progetto. Scaricalo da https://nssm.cc/download e copia nssm.exe nella root del progetto o in una cartella nel PATH."
        exit 1
    }
} else {
    $nssmExe = $nssmPath.Source
}

# Path del progetto e venv
$projectRoot = $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$mainPy = Join-Path $projectRoot "main.py"
$logDir = Join-Path $projectRoot "logs"
$exportsDir = Join-Path $projectRoot "exports"
$exportsTmpDir = Join-Path $exportsDir "_tmp"

# Verifica presenza file necessari
if (-not (Test-Path $pythonExe)) {
    Write-Error "Python non trovato in .venv\Scripts\python.exe. Crea virtualenv e installa dipendenze prima."
    exit 1
}
if (-not (Test-Path $mainPy)) {
    Write-Error "main.py non trovato in $projectRoot"
    exit 1
}

# Crea cartelle necessarie se non esistono
Write-Host "Verifica/creazione directories necessarie..."
foreach ($dir in @($logDir, $exportsDir, $exportsTmpDir)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "  Creata: $dir" -ForegroundColor Green
    }
}

# Rimuovi servizio esistente se presente
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Servizio esistente trovato. Rimozione in corso..."
    nssm stop $ServiceName
    nssm remove $ServiceName confirm
    Start-Sleep -Seconds 2
}

# Installa servizio
Write-Host "Installazione servizio $ServiceName sulla porta $Port..."
nssm install $ServiceName $pythonExe "$mainPy --port $Port"

# Configura parametri servizio
Write-Host "Configurazione parametri..."
nssm set $ServiceName DisplayName "$DisplayName"
nssm set $ServiceName Description "$Description"
nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName AppDirectory $projectRoot

# Configura restart automatico
# Riavvia sempre il servizio quando il processo termina (exit code 0 incluso)
# Necessario per hot restart funzionalità dell'app
nssm set $ServiceName AppStopMethodSkip 0
nssm set $ServiceName AppStopMethodConsole 1500
nssm set $ServiceName AppExit Default Restart
nssm set $ServiceName AppRestartDelay 5000

# Configura logging
$stdoutLog = Join-Path $logDir "service_stdout.log"
$stderrLog = Join-Path $logDir "service_stderr.log"
nssm set $ServiceName AppStdout $stdoutLog
nssm set $ServiceName AppStderr $stderrLog

# Configura rotazione log (10MB max, 1 file di backup)
nssm set $ServiceName AppStdoutCreationDisposition 4
nssm set $ServiceName AppStderrCreationDisposition 4
nssm set $ServiceName AppRotateFiles 1
nssm set $ServiceName AppRotateOnline 1
nssm set $ServiceName AppRotateSeconds 0
nssm set $ServiceName AppRotateBytes 10485760

# Avvia servizio
Write-Host "Avvio servizio..."
nssm start $ServiceName

Start-Sleep -Seconds 3

# Verifica stato
$status = nssm status $ServiceName
Write-Host "`nStato servizio: $status" -ForegroundColor Green

Write-Host "`n✅ Installazione completata!" -ForegroundColor Green
Write-Host "Gestione servizio:" -ForegroundColor Cyan
Write-Host "  - Avvia:   nssm start $ServiceName"
Write-Host "  - Ferma:   nssm stop $ServiceName"
Write-Host "  - Restart: nssm restart $ServiceName"
Write-Host "  - Stato:   nssm status $ServiceName"
Write-Host "  - Rimuovi: nssm remove $ServiceName confirm"
Write-Host "`nLog disponibili in: $logDir" -ForegroundColor Cyan
Write-Host "  - stdout: $stdoutLog"
Write-Host "  - stderr: $stderrLog"