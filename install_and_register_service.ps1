<#
install_and_register_service.ps1
- Creates virtualenv (.venv) if missing
- Installs dependencies from requirements.txt
- Ensures logs and Export directories exist
- Attempts to register the app as a Windows service using NSSM if installed, otherwise provides sc.exe instructions
- Usage: Run as Administrator
#>

param(
    [string]$RepoRoot = $PSScriptRoot,
    [string]$PythonExe = "python",
    [string]$ServiceName = "PSTT_Tool",
    [switch]$InstallService
)

Set-Location -Path $RepoRoot

function Ensure-Venv {
    if (-Not (Test-Path (Join-Path $RepoRoot ".venv"))) {
        Write-Host "Creating virtual environment .venv..."
        & $PythonExe -m venv .venv
    } else {
        Write-Host ".venv already exists"
    }
}

function Install-Requirements {
    Write-Host "Installing Python dependencies..."
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (-Not (Test-Path $venvPython)) { Write-Error "Virtualenv python not found: $venvPython"; return }
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $RepoRoot "requirements.txt")
}

function Ensure-Dirs {
    foreach ($d in @("logs", "Export")) {
        if (-Not (Test-Path (Join-Path $RepoRoot $d))) { New-Item -ItemType Directory -Path (Join-Path $RepoRoot $d) | Out-Null }
    }
}

function Register-Service-NSSM {
    param([string]$NssmPath = "nssm")
    # Look for nssm.exe in path or script folder
    $nssm = Get-Command $NssmPath -ErrorAction SilentlyContinue
    if (-Not $nssm) { return $false }
    $nssmExe = $nssm.Source
    $serviceExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    $serviceArgs = "`"$RepoRoot\main.py`""
    & $nssmExe install $ServiceName $serviceExe $serviceArgs
    & $nssmExe set $ServiceName AppDirectory $RepoRoot
    & $nssmExe set $ServiceName AppStdout $RepoRoot\logs\app.log
    & $nssmExe set $ServiceName AppStderr $RepoRoot\logs\errors.log
    & $nssmExe set $ServiceName Start SERVICE_AUTO_START
    Write-Host "Service $ServiceName installed with NSSM"
    return $true
}

function Register-Service-SC {
    # sc.exe create <ServiceName> binPath= "C:\path\to\cmd.exe /k \"...\""
    $cmd = "sc.exe create $ServiceName binPath= `"`"""$RepoRoot\\start_pstt.bat`"`""`" start= auto"
    Write-Host "To register service using sc.exe run (as Admin):"
    Write-Host $cmd
}

# Run steps
Ensure-Venv
Install-Requirements
Ensure-Dirs

if ($InstallService) {
    $installed = Register-Service-NSSM
    if (-Not $installed) { Register-Service-SC }
}

Write-Host "Setup complete. Run './start_pstt.ps1 -Detached' to start in background, or run 'start_pstt.bat' to use fallback."
