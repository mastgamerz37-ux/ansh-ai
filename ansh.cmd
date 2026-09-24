@echo off
setlocal
if not exist "D:\ansh\.license" (
    echo [ERROR] ANSH CLI is not activated. Run install.ps1 first!
    exit /b 1
)

"D:\ansh\venv\Scripts\python.exe" "D:\ansh\main.py" %*
endlocal
