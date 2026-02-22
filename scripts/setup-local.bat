@echo off
setlocal

set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "VENV_PY=%BACKEND%\.venv\Scripts\python.exe"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="/?" goto :help

if not exist "%BACKEND%" (
  echo [setup] Missing backend directory: "%BACKEND%"
  exit /b 1
)
if not exist "%FRONTEND%" (
  echo [setup] Missing frontend directory: "%FRONTEND%"
  exit /b 1
)

echo [setup] Repo root: "%ROOT%"
echo [setup] Creating backend virtual environment...
pushd "%BACKEND%" || exit /b 1
python -m venv .venv || exit /b 1
popd

if not exist "%VENV_PY%" (
  echo [setup] Failed to create backend venv python: "%VENV_PY%"
  exit /b 1
)

echo [setup] Installing backend dependencies...
"%VENV_PY%" -m pip install --upgrade pip || exit /b 1
"%VENV_PY%" -m pip install -r "%BACKEND%\requirements.txt" || exit /b 1

echo [setup] Installing Playwright Chromium...
"%VENV_PY%" -m playwright install chromium || exit /b 1

echo [setup] Installing frontend dependencies...
pushd "%FRONTEND%" || exit /b 1
npm install || exit /b 1
popd

if exist "%FRONTEND%\.env.example" (
  if not exist "%FRONTEND%\.env" (
    echo [setup] Creating frontend\.env from frontend\.env.example...
    copy /Y "%FRONTEND%\.env.example" "%FRONTEND%\.env" >nul || exit /b 1
  ) else (
    echo [setup] frontend\.env already exists, skipping.
  )
) else (
  echo [setup] frontend\.env.example not found, skipping env bootstrap.
)

echo.
if "%OPENAI_API_KEY%"=="" (
  echo [setup] OPENAI_API_KEY is not set in this shell.
  echo [setup] AI features are core to this app and will be blocked until the key is set.
  echo [setup] Set it before first run, then restart terminals:
  echo [setup]   setx OPENAI_API_KEY "your_key_here"
  echo [setup] or for current shell only:
  echo [setup]   set OPENAI_API_KEY=your_key_here
) else (
  echo [setup] OPENAI_API_KEY detected in current shell.
)
echo.
echo Setup complete.
echo Start app with:
echo   scripts\start-local.bat
echo.
echo Or manually:
echo   backend\.venv\Scripts\python.exe run-backend.py
echo   cd frontend ^&^& npm run dev
echo.
echo frontend\.env is optional unless you need a non-default VITE_API_BASE.
exit /b 0

:help
echo Usage: scripts\setup-local.bat
echo Creates backend venv, installs backend deps, installs Playwright Chromium,
echo installs frontend npm deps, and bootstraps frontend\.env if missing.
exit /b 0
