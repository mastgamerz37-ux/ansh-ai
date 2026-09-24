# ==============================================================================
#  update.ps1 — 1-Click Automated GitHub Updater for ANSH
#  ANSH — Your Own AI Friend | Autonomous Multimodal AI Assistant
#  Developer: Anshu Dubey | https://getyoursoft.vercel.app
#
#  Safely updates all clean code, assets, and documentation from GitHub
#  WITHOUT overwriting private keys, API keys, license state, or memory.
# ==============================================================================

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
$ErrorActionPreference = "Stop"

$RepoOwner = "mastgamerz37-ux"
$RepoName  = "ansh-ai"

$BaseDir = if ($PSScriptRoot) { $PSScriptRoot } else { $PWD.Path }
Set-Location $BaseDir

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "   ANSH AI - GitHub Auto-Update Utility                                       " -ForegroundColor White
Write-Host "   Repository: https://github.com/$RepoOwner/$RepoName                        " -ForegroundColor DarkGray
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check for Python in venv
$VenvPython = Join-Path $BaseDir "venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = "python"
}

# Run the core updater module
Write-Host "[1/2] Checking and syncing latest GitHub commits..." -ForegroundColor Yellow
& $VenvPython -m core.updater

# Also verify requirements in case new packages were added
if (Test-Path "$BaseDir\requirements.txt") {
    Write-Host "`n[2/2] Checking and updating dependencies..." -ForegroundColor Yellow
    & $VenvPython -m pip install -r "$BaseDir\requirements.txt" --quiet --no-warn-script-location
    Write-Host "   [OK] Dependencies verified." -ForegroundColor Green
}

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "   [DONE] ANSH AI update check and synchronization finished!                  " -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host ""
