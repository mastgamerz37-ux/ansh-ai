@echo off
setlocal EnableDelayedExpansion

:: Check arguments
if "%1"=="" goto help
if "%1"=="install" goto install
if "%1"=="dev" goto dev
if "%1"=="start" goto start
goto help

:install
echo [ANSH] Checking Python...
py --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    python --version >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo [ANSH] Python is missing! Installing automatically...
        winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    )
)

echo [ANSH] Creating Environment...
if not exist venv (
    py -m venv venv >nul 2>&1 || python -m venv venv
)

echo [ANSH] Installing Dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
echo [ANSH] Install Complete! Starting Ansh...
goto start

:dev
echo [ANSH] Starting Developer Mode...
if not exist venv (
    echo [ANSH] Environment not found! Run "ansh install" first.
    exit /b
)
call venv\Scripts\activate.bat
python main.py
exit /b

:start
echo [ANSH] Starting Ansh AI in background...
if not exist venv (
    echo [ANSH] Environment not found! Run "ansh install" first.
    exit /b
)
call venv\Scripts\activate.bat
start pythonw main.py
exit /b

:help
echo.
echo =========================================
echo         ANSH AI COMMAND LINE TOOL
echo =========================================
echo Usage: 
echo   ansh install   - Automatically sets up Python and installs all files/libraries
echo   ansh dev       - Starts Ansh with console output (like npm run dev)
echo   ansh start     - Starts Ansh silently in the background (no black window)
echo =========================================
echo.
exit /b
