@echo off
:: start_pstt.bat - minimal launcher for PSTT_TOOL
:: Usage: start_pstt.bat [--host 0.0.0.0] [--port 8000]

SETLOCAL
REM Get the folder containing this script
SET SCRIPT_DIR=%~dp0

REM Normalize path (remove trailing backslash)
IF "%SCRIPT_DIR:~-1%"=="\" SET SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Prefer venv python if available
IF EXIST "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%\.venv\Scripts\python.exe" "%SCRIPT_DIR%\main.py" %*
) ELSE (
    REM Fallback to system python in PATH
    python "%SCRIPT_DIR%\main.py" %*
)

ENDLOCAL