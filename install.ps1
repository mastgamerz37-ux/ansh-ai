<#
====================================================================
 Project    : ANSH - Your Own AI Friend
 File       : install.ps1
 Description: Universal One-Command Web & Local Installer for Windows
 Author     : Anshu Dubey | https://getyoursoft.vercel.app
 GitHub     : https://github.com/mastgamerz37-ux/ansh-ai
====================================================================
Usage (From any PC in PowerShell):
    irm https://raw.githubusercontent.com/mastgamerz37-ux/ansh-ai/main/install.ps1 | iex
====================================================================
#>

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$REPO_OWNER = "mastgamerz37-ux"
$REPO_NAME  = "ansh-ai"
$BRANCH     = "main"

Clear-Host
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "           ANSH - YOUR OWN AI FRIEND INSTALLER              " -ForegroundColor Cyan
Write-Host "         Developer: Anshu Dubey | https://getyoursoft.vercel.app " -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------
# STEP 0: DETERMINE INSTALLATION DIRECTORY & SOURCE
# ------------------------------------------------------------------
$isLocal = $false
$currentDir = if ($PSScriptRoot) { $PSScriptRoot.TrimEnd('\') } else { (Get-Location).Path.TrimEnd('\') }

if (Test-Path (Join-Path $currentDir "main.py")) {
    $InstallDir = $currentDir
    $isLocal = $true
    Write-Host "[Mode] Local installation detected in: $InstallDir" -ForegroundColor Green
} else {
    $InstallDir = Join-Path $env:LOCALAPPDATA "ANSH"
    Write-Host "[Mode] Remote Web Installer (Target: $InstallDir)" -ForegroundColor Yellow
}

# ------------------------------------------------------------------
# STEP 1: DOWNLOAD SOURCE FILES (IF REMOTE WEB INSTALL)
# ------------------------------------------------------------------
if (-not $isLocal) {
    Write-Host ""
    Write-Host "[1/5] Downloading latest ANSH AI package from GitHub..." -ForegroundColor Yellow
    
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }

    $zipUrl = "https://github.com/$REPO_OWNER/$REPO_NAME/archive/refs/heads/$BRANCH.zip"
    $tempZip = Join-Path $env:TEMP "ansh_latest.zip"
    $tempExtract = Join-Path $env:TEMP "ansh_extract_$([Guid]::NewGuid().ToString('N'))"

    try {
        Write-Host "Connecting to GitHub ($REPO_OWNER/$REPO_NAME)..." -ForegroundColor Gray
        Invoke-WebRequest -Uri $zipUrl -OutFile $tempZip -UseBasicParsing
        
        Write-Host "Extracting application packages..." -ForegroundColor Gray
        Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force
        
        $innerFolder = Get-ChildItem -Path $tempExtract -Directory | Select-Object -First 1
        if ($innerFolder) {
            Get-ChildItem -Path $innerFolder.FullName | Copy-Item -Destination $InstallDir -Recurse -Force
        } else {
            Get-ChildItem -Path $tempExtract | Copy-Item -Destination $InstallDir -Recurse -Force
        }
        
        Write-Host "[SUCCESS] ANSH files downloaded to $InstallDir" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Could not download ANSH repository from GitHub: $_" -ForegroundColor Red
        Write-Host "Please check internet connection or repository status." -ForegroundColor Yellow
        exit 1
    } finally {
        Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "[1/5] Using local repository files..." -ForegroundColor Green
}

# ------------------------------------------------------------------
# STEP 2: PYTHON ENVIRONMENT CHECK & AUTO-INSTALL
# ------------------------------------------------------------------
Write-Host ""
Write-Host "[2/5] Checking Python Runtime..." -ForegroundColor Yellow

$sysPythonCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $sysPythonCmd = "python"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $sysPythonCmd = "py"
}

if (-not $sysPythonCmd) {
    Write-Host "[!] Python is not installed on this system." -ForegroundColor Yellow
    if (Get-Command "winget" -ErrorAction SilentlyContinue) {
        Write-Host "Installing Python 3.12 automatically via Windows Package Manager (winget)..." -ForegroundColor Cyan
        try {
            winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            if (Get-Command "python" -ErrorAction SilentlyContinue) {
                $sysPythonCmd = "python"
            }
        } catch {
            Write-Host "winget installation encountered an issue." -ForegroundColor Gray
        }
    }
}

if (-not $sysPythonCmd) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host " [ERROR] Python 3.10+ is required to run ANSH AI!           " -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "Please download & install Python: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "IMPORTANT: Check the box 'Add Python to PATH' during setup." -ForegroundColor Yellow
    exit 1
}

$pyVersion = (& $sysPythonCmd --version 2>&1)
Write-Host "[SUCCESS] Found: $pyVersion" -ForegroundColor Green

# ------------------------------------------------------------------
# STEP 3: VIRTUAL ENVIRONMENT & DEPENDENCIES
# ------------------------------------------------------------------
Write-Host ""
Write-Host "[3/5] Setting up Virtual Environment & Dependencies..." -ForegroundColor Yellow

$venvDir = Join-Path $InstallDir "venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating Python virtual environment in $venvDir..." -ForegroundColor Gray
    & $sysPythonCmd -m venv $venvDir
}

if (Test-Path (Join-Path $InstallDir "requirements.txt")) {
    Write-Host "Installing and verifying libraries from requirements.txt..." -ForegroundColor Gray
    Write-Host "(This might take 1-2 minutes on first install)..." -ForegroundColor DarkGray
    & $venvPip install -r (Join-Path $InstallDir "requirements.txt") --quiet
}

Write-Host "[SUCCESS] All AI libraries and dependencies installed!" -ForegroundColor Green

# ------------------------------------------------------------------
# STEP 4: LICENSE & 3-DAY FREE TRIAL INITIALIZATION
# ------------------------------------------------------------------
Write-Host ""
Write-Host "[4/5] Activating 3-Day Free Evaluation Trial..." -ForegroundColor Yellow

$licenseFile = Join-Path $InstallDir ".license"
if (-not (Test-Path $licenseFile)) {
    $licenseLock = @{
        "installed_at" = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        "status"       = "TRIAL_ACTIVE"
        "trial_days"   = 3
    } | ConvertTo-Json
    Set-Content -Path $licenseFile -Value $licenseLock -Encoding utf8
}

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

Write-Host "[SUCCESS] 3-Day Free Trial Activated (No credit card or key required)!" -ForegroundColor Green

# ------------------------------------------------------------------
# STEP 5: CLI LAUNCHER, PATH SETUP & DESKTOP SHORTCUT
# ------------------------------------------------------------------
Write-Host ""
Write-Host "[5/5] Creating Global CLI Launcher & Desktop Shortcut..." -ForegroundColor Yellow

# Portable ansh.cmd using %~dp0
$cmdPath = Join-Path $InstallDir "ansh.cmd"
$cmdContent = @"
@echo off
setlocal
set "ANSH_DIR=%~dp0"
set "ANSH_DIR=%ANSH_DIR:~0,-1%"

if not exist "%ANSH_DIR%\.license" (
    echo [ERROR] ANSH is not installed properly. Run install.ps1 first!
    exit /b 1
)

if exist "%ANSH_DIR%\venv\Scripts\python.exe" (
    "%ANSH_DIR%\venv\Scripts\python.exe" "%ANSH_DIR%\main.py" %*
) else (
    python "%ANSH_DIR%\main.py" %*
)
endlocal
"@

Set-Content -Path $cmdPath -Value $cmdContent -Encoding ASCII

# Add to User PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathList = if ($userPath) {
    $userPath -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.TrimEnd('\') }
} else { @() }

if ($pathList -notcontains $InstallDir) {
    $updatedPath = ($pathList + $InstallDir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $updatedPath, "User")
    $env:Path += ";$InstallDir"
    Write-Host "[SUCCESS] Added '$InstallDir' to Windows User PATH!" -ForegroundColor Green
}

# Desktop Shortcut
try {
    $desktopDir = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktopDir "ANSH AI.lnk"
    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $cmdPath
    $shortcut.WorkingDirectory = $InstallDir
    $ico = Join-Path $InstallDir "config\jarvis.ico"
    if (Test-Path $ico) {
        $shortcut.IconLocation = "$ico, 0"
    }
    $shortcut.Description = "ANSH - Your Own AI Friend"
    $shortcut.Save()
    Write-Host "[SUCCESS] Created Desktop Shortcut: 'ANSH AI'!" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Desktop shortcut creation skipped." -ForegroundColor Gray
}

# ------------------------------------------------------------------
# FINISHED
# ------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "           CONGRATULATIONS! INSTALLATION COMPLETE           " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "ANSH - Your Own AI Friend is now ready on this PC!" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can start ANSH in two ways:" -ForegroundColor White
Write-Host "  1. Double click the 'ANSH AI' icon on your Desktop" -ForegroundColor Yellow
Write-Host "  2. Open any CMD or PowerShell terminal and run:" -ForegroundColor White
Write-Host "         ansh" -ForegroundColor Yellow
Write-Host ""
Write-Host "Commercial keys & licenses available at: https://getyoursoft.vercel.app" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Green