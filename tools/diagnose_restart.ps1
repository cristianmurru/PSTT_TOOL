<#
.SYNOPSIS
    Script diagnostico per troubleshooting restart servizio PSTT_Tool
.DESCRIPTION
    Verifica configurazione NSSM, PATH, porte e stato servizio per identificare
    problemi con il restart automatico da UI.
#>

param(
    [string]$ServiceName = "PSTT_Tool"
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  DIAGNOSI RESTART SERVIZIO PSTT_Tool" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$issues = @()
$warnings = @()

# 1. Verifica esistenza servizio
Write-Host "[1/8] Verifica esistenza servizio..." -ForegroundColor Yellow
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "  ✅ Servizio trovato: $($service.DisplayName)" -ForegroundColor Green
    Write-Host "     Status: $($service.Status)" -ForegroundColor Cyan
} else {
    Write-Host "  ❌ Servizio NON trovato" -ForegroundColor Red
    $issues += "Servizio $ServiceName non installato"
}

# 2. Verifica NSSM nel PATH
Write-Host "`n[2/8] Verifica NSSM nel PATH..." -ForegroundColor Yellow
$nssmCmd = Get-Command nssm -ErrorAction SilentlyContinue
if ($nssmCmd) {
    Write-Host "  ✅ NSSM trovato: $($nssmCmd.Source)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  NSSM non trovato nel PATH" -ForegroundColor Yellow
    $warnings += "NSSM non nel PATH - restart potrebbe fallire"
    
    # Cerca NSSM nel progetto
    $localNssm = Get-ChildItem -Path $PSScriptRoot\.. -Filter "nssm.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($localNssm) {
        Write-Host "     NSSM locale trovato: $($localNssm.FullName)" -ForegroundColor Cyan
    }
}

# 3. Verifica manage_service.ps1
Write-Host "`n[3/8] Verifica manage_service.ps1..." -ForegroundColor Yellow
$manageScript = Join-Path $PSScriptRoot "..\manage_service.ps1"
if (Test-Path $manageScript) {
    Write-Host "  ✅ manage_service.ps1 trovato" -ForegroundColor Green
} else {
    Write-Host "  ❌ manage_service.ps1 NON trovato" -ForegroundColor Red
    $issues += "manage_service.ps1 mancante"
}

# 4. Verifica configurazione NSSM
Write-Host "`n[4/8] Verifica configurazione NSSM..." -ForegroundColor Yellow
if ($nssmCmd -and $service) {
    try {
        $appPath = & nssm get $ServiceName Application 2>&1
        $appDir = & nssm get $ServiceName AppDirectory 2>&1
        $appExit = & nssm get $ServiceName AppExit 2>&1
        
        Write-Host "  Application: $appPath" -ForegroundColor Cyan
        Write-Host "  AppDirectory: $appDir" -ForegroundColor Cyan
        Write-Host "  AppExit: $appExit" -ForegroundColor Cyan
        
        # Verifica AppExit configuration
        if ($appExit -match "Default Restart") {
            Write-Host "  ⚠️  AppExit usa 'Default Restart' - può causare loop!" -ForegroundColor Yellow
            $warnings += "AppExit Default Restart configurato - rischio loop infinito"
        } elseif ($appExit -match "Default Exit") {
            Write-Host "  ✅ AppExit configurato correttamente (Default Exit)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ⚠️  Errore lettura configurazione NSSM: $_" -ForegroundColor Yellow
    }
}

# 5. Verifica .env e PORT
Write-Host "`n[5/8] Verifica .env e configurazione PORT..." -ForegroundColor Yellow
$envPath = Join-Path $PSScriptRoot "..\.env"
if (Test-Path $envPath) {
    $portLine = Select-String -Path $envPath -Pattern "^PORT=" | Select-Object -First 1
    if ($portLine) {
        Write-Host "  ✅ $($portLine.Line)" -ForegroundColor Green
        
        $port = $portLine.Line -replace "PORT=", ""
        
        # Verifica se porta è in ascolto
        $listening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($listening) {
            Write-Host "  ✅ Porta $port in ascolto (PID: $($listening.OwningProcess))" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Porta $port NON in ascolto" -ForegroundColor Yellow
            if ($service.Status -eq "Running") {
                $warnings += "Servizio running ma porta $port non in ascolto - possibile bind su porta diversa"
            }
        }
    } else {
        Write-Host "  ⚠️  PORT non definito in .env" -ForegroundColor Yellow
        $warnings += "PORT non configurato in .env - usa default 8000"
    }
} else {
    Write-Host "  ❌ .env NON trovato" -ForegroundColor Red
    $issues += ".env file mancante"
}

# 6. Verifica log errori recenti
Write-Host "`n[6/8] Verifica log errori recenti..." -ForegroundColor Yellow
$errorLog = Join-Path $PSScriptRoot "..\logs\error.log"
if (Test-Path $errorLog) {
    $recentErrors = Get-Content $errorLog -Tail 10 -ErrorAction SilentlyContinue
    if ($recentErrors) {
        Write-Host "  ⚠️  Ultimi errori trovati:" -ForegroundColor Yellow
        $recentErrors | ForEach-Object { Write-Host "     $_" -ForegroundColor DarkYellow }
    } else {
        Write-Host "  ✅ Nessun errore recente" -ForegroundColor Green
    }
} else {
    Write-Host "  ℹ️  Log errori non presente" -ForegroundColor Gray
}

# 7. Test restart simulato
Write-Host "`n[7/8] Test restart simulato (senza esecuzione)..." -ForegroundColor Yellow
if ($nssmCmd -and $service) {
    Write-Host "  Comando che verrebbe eseguito:" -ForegroundColor Cyan
    Write-Host "  > nssm restart $ServiceName" -ForegroundColor White
    Write-Host "  ℹ️  Per testare realmente, esegui manualmente il comando sopra" -ForegroundColor Gray
} else {
    Write-Host "  ⚠️  Impossibile testare - NSSM o servizio non disponibile" -ForegroundColor Yellow
}

# 8. Verifica permessi PowerShell
Write-Host "`n[8/8] Verifica permessi ed ExecutionPolicy..." -ForegroundColor Yellow
$execPolicy = Get-ExecutionPolicy
Write-Host "  ExecutionPolicy: $execPolicy" -ForegroundColor Cyan
if ($execPolicy -eq "Restricted") {
    Write-Host "  ⚠️  ExecutionPolicy Restricted - script potrebbero fallire" -ForegroundColor Yellow
    $warnings += "ExecutionPolicy Restricted impedisce esecuzione script"
}

# Verifica se running come admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "  ✅ Running con privilegi amministrativi" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  NON running come amministratore" -ForegroundColor Yellow
    $warnings += "Script non eseguito come amministratore - alcune operazioni potrebbero fallire"
}

# RIEPILOGO
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  RIEPILOGO" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($issues.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "✅ Nessun problema rilevato!" -ForegroundColor Green
} else {
    if ($issues.Count -gt 0) {
        Write-Host "❌ PROBLEMI CRITICI ($($issues.Count)):" -ForegroundColor Red
        $issues | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host "`n⚠️  AVVISI ($($warnings.Count)):" -ForegroundColor Yellow
        $warnings | ForEach-Object { Write-Host "   - $_" -ForegroundColor Yellow }
    }
}

# RACCOMANDAZIONI
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  RACCOMANDAZIONI" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($warnings -match "NSSM non nel PATH") {
    Write-Host "➡️  Aggiungi NSSM al PATH di sistema:" -ForegroundColor Cyan
    Write-Host '   $nssmDir = (Get-ChildItem -Path . -Filter nssm.exe -Recurse | Select-Object -First 1).DirectoryName' -ForegroundColor White
    Write-Host '   [Environment]::SetEnvironmentVariable("Path", "$env:Path;$nssmDir", "Machine")' -ForegroundColor White
    Write-Host "   Poi riavvia PowerShell`n" -ForegroundColor Gray
}

if ($warnings -match "AppExit Default Restart") {
    Write-Host "➡️  Correggi configurazione NSSM per prevenire loop:" -ForegroundColor Cyan
    Write-Host "   nssm set $ServiceName AppExit Default Exit" -ForegroundColor White
    Write-Host "   nssm restart $ServiceName`n" -ForegroundColor White
}

if ($service.Status -eq "Stopped") {
    Write-Host "➡️  Servizio attualmente fermo. Per avviarlo:" -ForegroundColor Cyan
    Write-Host "   nssm start $ServiceName" -ForegroundColor White
    Write-Host "   Oppure:" -ForegroundColor Gray
    Write-Host "   .\manage_service.ps1 start`n" -ForegroundColor White
}

Write-Host "========================================`n" -ForegroundColor Cyan
