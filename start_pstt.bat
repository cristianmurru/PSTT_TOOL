@echo off
rem Batch file to start PSTT Tool on Windows
rem Usage: double-click or run from an elevated prompt

:: Change directory to repository root (this script is in repo root)
cd /d "%~dp0"

:: Activate virtual environment if present
:: Windows PowerShell activation (for interactive session) is different; here we use the venv Scripts activate for cmd
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo Virtual environment not found at .venv\Scripts\activate.bat
    echo Please create and install dependencies before running this script.
    pause
    exit /b 1
)

:: Optional: set environment variables from .env if desired (requires a helper or set manually)
:: You can uncomment the following line to load a .env file using the 'set' builtin, but note it won't parse quotes and special chars safely.
:: for /f "usebackq tokens=*" %%a in (".env") do set "%%a"

:: Start the application and redirect stdout/stderr to logs\app.log, create logs dir if missing
if not exist "logs" mkdir "logs"
set LOGFILE=logs\app.log

:: Start the app (non-blocking) and redirect output. Use start to run in new window if desired.
start "PSTT Tool" cmd /c "python main.py >> %LOGFILE% 2>&1"

echo PSTT Tool started. See %LOGFILE% for output.
exit /b 0
