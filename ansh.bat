@echo off
setlocal EnableDelayedExpansion

:: Check arguments
if "%1"=="" goto help
if /i "%1"=="install" goto install
if /i "%1"=="dev" goto dev
if /i "%1"=="start" goto start
if /i "%1"=="update" goto update
if /i "%1"=="status" goto status
if /i "%1"=="keys" goto keys
if /i "%1"=="help" goto help
if /i "%1"=="-h" goto help
if /i "%1"=="--help" goto help
goto help

:install
powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"
exit /b %ERRORLEVEL%

:update
echo [ANSH] Checking for latest updates from GitHub...
powershell -ExecutionPolicy Bypass -File "%~dp0update.ps1"
exit /b %ERRORLEVEL%

:status
if not exist venv (
    echo [ANSH] Environment not found! Run "ansh install" first.
    exit /b 1
)
call venv\Scripts\activate.bat
python setup_keys.py --status
exit /b 0

:keys
if not exist venv (
    echo [ANSH] Environment not found! Run "ansh install" first.
    exit /b 1
)
call venv\Scripts\activate.bat
python setup_keys.py %2 %3 %4 %5
exit /b %ERRORLEVEL%

:dev
echo [ANSH] Starting Developer Mode...
if not exist venv (
    echo [ANSH] Environment not found! Run "ansh install" first.
    exit /b 1
)
call venv\Scripts\activate.bat
python main.py
exit /b %ERRORLEVEL%

:start
echo [ANSH] Starting Ansh AI in background...
if not exist venv (
    echo [ANSH] Environment not found! Run "ansh install" first.
    exit /b 1
)
call venv\Scripts\activate.bat
start "" pythonw main.py
exit /b 0

:help
echo.
echo ==============================================================
echo         ANSH - Your Own AI Friend — Command Line Tool
echo ==============================================================
echo   ansh install   - Automatically sets up Python, venv, shortcuts, and global command
echo   ansh dev       - Starts Ansh in developer mode with live terminal logs
echo   ansh start     - Starts Ansh silently in the background
echo   ansh update    - Safely syncs latest code from GitHub (keeps your keys and memory safe)
echo   ansh status    - Shows current license status and API key diagnostics
echo   ansh keys      - Configures API keys or activates product keys
echo ==============================================================
echo.
exit /b 0
