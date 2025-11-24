<#
.SYNOPSIS
    Gestione rapida servizio PSTT Tool
.PARAMETER Action
    start, stop, restart, status, logs, uninstall
#>

param(
    [ValidateSet("start","stop","restart","status","logs","uninstall")]
    [string]$Action = "status",
    [string]$ServiceName = "PSTT_Tool"
)

#Requires -RunAsAdministrator

# Trova nssm.exe (nel PATH o localmente)
$nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssmPath) {
    $localNssm = Get-ChildItem -Path $PSScriptRoot -Filter "nssm.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($localNssm) {
        $nssmExe = $localNssm.FullName
        Set-Alias -Name nssm -Value $nssmExe -Scope Script
    } else {
        Write-Error "NSSM non trovato. Assicurati che nssm.exe sia nella cartella del progetto o nel PATH."
        exit 1
    }
}

$logDir = Join-Path $PSScriptRoot "logs"
$stdoutLog = Join-Path $logDir "service_stdout.log"
$stderrLog = Join-Path $logDir "service_stderr.log"

switch ($Action) {
    "start" {
        Write-Host "Avvio servizio $ServiceName..."
        nssm start $ServiceName
        Start-Sleep -Seconds 2
        nssm status $ServiceName
    }
    "stop" {
        Write-Host "Arresto servizio $ServiceName..."
        nssm stop $ServiceName
        Start-Sleep -Seconds 2
        nssm status $ServiceName
    }
    "restart" {
        Write-Host "Restart servizio $ServiceName..."
        nssm restart $ServiceName
        Start-Sleep -Seconds 3
        nssm status $ServiceName
    }
    "status" {
        $status = nssm status $ServiceName
        Write-Host "Stato: $status" -ForegroundColor $(if($status -eq "SERVICE_RUNNING"){"Green"}else{"Yellow"})
        
        # Mostra anche info da services
        $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($svc) {
            Write-Host "`nDettagli servizio:"
            $svc | Format-List Name, DisplayName, Status, StartType
        }
    }
    "logs" {
        Write-Host "Log stdout (ultimi 50 righe):" -ForegroundColor Cyan
        if (Test-Path $stdoutLog) {
            Get-Content $stdoutLog -Tail 50
        } else {
            Write-Host "  (vuoto)" -ForegroundColor Gray
        }
        
        Write-Host "`nLog stderr (ultimi 50 righe):" -ForegroundColor Cyan
        if (Test-Path $stderrLog) {
            Get-Content $stderrLog -Tail 50
        } else {
            Write-Host "  (vuoto)" -ForegroundColor Gray
        }
    }
    "uninstall" {
        Write-Host "Disinstallazione servizio $ServiceName..." -ForegroundColor Yellow
        nssm stop $ServiceName
        Start-Sleep -Seconds 2
        nssm remove $ServiceName confirm
        Write-Host "✅ Servizio rimosso" -ForegroundColor Green
    }
}