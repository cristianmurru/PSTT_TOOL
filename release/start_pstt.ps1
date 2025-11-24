<#
PowerShell starter for PSTT Tool
- Activates .venv (PowerShell activation)
- Securely loads .env into process environment (simple parser)
- Ensures logs dir exists and starts the app redirecting stdout/stderr to logs\app.log
- Use: powershell -NoProfile -ExecutionPolicy Bypass -File .\start_pstt.ps1
#>

param(
-    [switch]$Detached
-)

# Move to script directory (repo root)
Set-Location -Path $PSScriptRoot

function Load-DotEnv {
    param([string]$Path = ".env")
    if (-Not (Test-Path $Path)) {
        return
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        $pair = $line -split "=", 2
        if ($pair.Length -ne 2) { return }
        $key = $pair[0].Trim()
        $val = $pair[1].Trim().Trim('"')
        # Do not expose secrets to host; set in process only
        $env:$key = $val
    }
}

# Activate venv for PowerShell
$activate = Join-Path -Path $PSScriptRoot -ChildPath ".venv\Scripts\Activate.ps1"
if (Test-Path $activate) {
    Write-Host "Activating virtualenv..."
    try {
        . $activate
    } catch {
        Write-Warning "Failed to source Activate.ps1: $_"
    }
} else {
    Write-Warning ".venv Activate.ps1 not found. Ensure virtualenv exists and dependencies are installed."
}

# Load .env into process env
Load-DotEnv -Path (Join-Path $PSScriptRoot ".env")

# Ensure logs dir
$logDir = Join-Path $PSScriptRoot "logs"
if (-Not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir "app.log"

# Start application
if ($Detached) {
    Write-Host "Starting PSTT Tool in detached window..."
    Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command \"python main.py >> '$logFile' 2>&1\"" -WindowStyle Hidden
    Write-Host "Started (detached). See $logFile for output."
} else {
    Write-Host "Starting PSTT Tool (foreground). Logs -> $logFile"
    python main.py 2>&1 | Tee-Object -FilePath $logFile
}
