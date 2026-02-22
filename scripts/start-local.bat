@echo off
setlocal

set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "VENV_PY=%BACKEND%\.venv\Scripts\python.exe"
set "BACKEND_ENTRY=%ROOT%\run-backend.py"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="--check" goto :check

if not exist "%VENV_PY%" (
  echo [start] Missing backend venv python: "%VENV_PY%"
  echo [start] Run scripts\setup-local.bat first.
  exit /b 1
)
if not exist "%BACKEND_ENTRY%" (
  echo [start] Missing backend entrypoint: "%BACKEND_ENTRY%"
  exit /b 1
)
if not exist "%FRONTEND%\package.json" (
  echo [start] Missing frontend package.json in "%FRONTEND%"
  exit /b 1
)

echo [start] Launching backend terminal...
start "Job Finder Backend" cmd /k ""%VENV_PY%" "%BACKEND_ENTRY%""

echo [start] Launching frontend terminal...
start "Job Finder Frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev"

echo [start] Opening http://localhost:5173 ...
start "" "http://localhost:5173"

echo [start] Done.
exit /b 0

:check
if not exist "%VENV_PY%" (
  echo check_ok=false
  echo reason=missing_backend_venv
  exit /b 1
)
if not exist "%BACKEND_ENTRY%" (
  echo check_ok=false
  echo reason=missing_backend_entry
  exit /b 1
)
if not exist "%FRONTEND%\package.json" (
  echo check_ok=false
  echo reason=missing_frontend_package
  exit /b 1
)
echo check_ok=true
exit /b 0

:help
echo Usage: scripts\start-local.bat [--check]
echo Starts backend and frontend in separate terminals and opens the app URL.
echo Use --check to validate prerequisites without launching terminals.
exit /b 0

