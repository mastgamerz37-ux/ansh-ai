<#
====================================================================
 Project    : ANSH CLI Tool
 File       : install.ps1
 Description: Full Installer with 3-Day Free Trial & Global PATH Setup
====================================================================
#>

$ErrorActionPreference = "Stop"

# Current Directory automatically detect karna (Trailing slash hatana)
$InstallDir = if ($PSScriptRoot) { $PSScriptRoot.TrimEnd('\') } else { (Get-Location).Path.TrimEnd('\') }

Clear-Host
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "                 ANSH CLI INSTALLATION WIZARD               " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Installation Directory: $InstallDir" -ForegroundColor Gray
Write-Host ""

# ------------------------------------------------------------------
# STEP 1: 3-DAY FREE TRIAL INITIALIZATION
# ------------------------------------------------------------------
Write-Host "[1/4] Initializing 3-Day Free Trial..." -ForegroundColor Yellow

# .license file create karna (CLI launcher ke status ke liye)
$licenseLock = @{
    "installed_at" = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "status"       = "TRIAL_ACTIVE"
    "trial_days"   = 3
} | ConvertTo-Json

Set-Content -Path (Join-Path $InstallDir ".license") -Value $licenseLock -Encoding utf8

# config/license.json check/initialize karna (Python LicenseManager ke liye)
$configDir = Join-Path $InstallDir "config"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

$pyLicenseFile = Join-Path $configDir "license.json"
if (-not (Test-Path $pyLicenseFile)) {
    $nowEpoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $pyLicData = @{
        "first_launch_time"  = $nowEpoch
        "activated"          = $false
        "activated_key_hash" = ""
        "activation_date"    = ""
    } | ConvertTo-Json -Depth 5
    Set-Content -Path $pyLicenseFile -Value $pyLicData -Encoding utf8
}

Write-Host "[SUCCESS] 3-Day Free Trial initialized!" -ForegroundColor Green
Write-Host "Aapko 3 din ka full access mila hai (Bina kisi key ke)." -ForegroundColor Gray
Write-Host "3 din baad aap https://getyoursoft.vercel.app se key lekar continue kar sakte hain." -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------
# STEP 2: PYTHON & DEPENDENCIES CHECK
# ------------------------------------------------------------------
Write-Host "[2/4] Setting up Environment & Dependencies..." -ForegroundColor Yellow

# Python command check
$sysPythonCmd = "python"
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        $sysPythonCmd = "py"
    } else {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Red
        Write-Host " [ERROR] Python system me install nahi mila!                " -ForegroundColor Red
        Write-Host "============================================================" -ForegroundColor Red
        Write-Host "Kripya Python 3.10+ install karein: https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "Note: Install karte waqt 'Add Python to PATH' zaroor tick karein." -ForegroundColor Yellow
        Write-Host "Press Enter to exit..."
        Read-Host
        exit 1
    }
}

$pythonExe = $sysPythonCmd
$entryScript = "main.py"

if (Test-Path (Join-Path $InstallDir "ansh.py")) { $entryScript = "ansh.py" }
elseif (Test-Path (Join-Path $InstallDir "app.py")) { $entryScript = "app.py" }
elseif (Test-Path (Join-Path $InstallDir "cli.py")) { $entryScript = "cli.py" }

# Virtual Environment & Requirements
if (Test-Path (Join-Path $InstallDir "requirements.txt")) {
    $venvDir = Join-Path $InstallDir "venv"
    if (-not (Test-Path $venvDir)) {
        Write-Host "Creating Python virtual environment..." -ForegroundColor Gray
        & $sysPythonCmd -m venv $venvDir
    }
    
    $venvPython = Join-Path $venvDir "Scripts\python.exe"
    $venvPip = Join-Path $venvDir "Scripts\pip.exe"
    
    if (Test-Path $venvPython) {
        $pythonExe = $venvPython
        Write-Host "Installing/verifying required libraries from requirements.txt..." -ForegroundColor Gray
        & $venvPip install -r (Join-Path $InstallDir "requirements.txt") --quiet
    }
}

Write-Host "[SUCCESS] Environment ready." -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------------
# STEP 3: CLI LAUNCHER SCRIPT (ansh.cmd) BANANA
# ------------------------------------------------------------------
Write-Host "[3/4] Creating Global CLI Command ('ansh')..." -ForegroundColor Yellow

$cmdPath = Join-Path $InstallDir "ansh.cmd"

$cmdContent = @"
@echo off
setlocal
if not exist "$InstallDir\.license" (
    echo [ERROR] ANSH CLI is not installed properly. Run install.ps1 first!
    exit /b 1
)

"$pythonExe" "$InstallDir\$entryScript" %*
endlocal
"@

Set-Content -Path $cmdPath -Value $cmdContent -Encoding ASCII
Write-Host "[SUCCESS] Launcher created at: $cmdPath" -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------------
# STEP 4: WINDOWS USER PATH ME DIRECTORY ADD KARNA (PERMANENT)
# ------------------------------------------------------------------
Write-Host "[4/4] Configuring System PATH..." -ForegroundColor Yellow

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathList = if ($userPath) {
    $userPath -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.TrimEnd('\') }
} else { @() }

if ($pathList -notcontains $InstallDir) {
    $updatedPath = ($pathList + $InstallDir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $updatedPath, "User")
    
    # Current PowerShell session ka path bhi update
    $env:Path += ";$InstallDir"
    Write-Host "[SUCCESS] '$InstallDir' permanently added to Windows User PATH!" -ForegroundColor Green
} else {
    Write-Host "[INFO] '$InstallDir' already PATH me shamil hai." -ForegroundColor Cyan
}

# ------------------------------------------------------------------
# FINISHED
# ------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "           CONGRATULATIONS! INSTALLATION COMPLETE           " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Aapka 3-Day Free Trial start ho chuka hai!" -ForegroundColor Cyan
Write-Host "Ab aap kisi bhi CMD ya PowerShell window me type karein:" -ForegroundColor White
Write-Host ""
Write-Host "    ansh" -ForegroundColor Yellow
Write-Host ""
Write-Host "Note: 3 din ke baad application aapse Product Key mangegi." -ForegroundColor Gray
Write-Host "      Aap key yahan se le sakte hain: https://getyoursoft.vercel.app" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Green